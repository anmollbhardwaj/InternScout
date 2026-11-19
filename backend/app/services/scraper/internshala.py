import asyncio
import logging
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Internship, User
from app.services.scraper.browser import BrowserManager, human_delay, human_scroll

logger = logging.getLogger(__name__)


def parse_stipend_inr(stipend_str: Optional[str]) -> tuple[int, int]:
    """Extract numeric min and max stipend in INR from text like '₹ 15,000 - 25,000 /month'."""
    if not stipend_str:
        return 0, 0
    cleaned = stipend_str.replace(",", "").replace("₹", "")
    numbers = [int(n) for n in re.findall(r"\b\d+\b", cleaned)]
    if not numbers:
        return 0, 0
    if len(numbers) == 1:
        return numbers[0], numbers[0]
    return min(numbers[0], numbers[1]), max(numbers[0], numbers[1])


def parse_duration_months(duration_str: Optional[str]) -> int:
    """Parse '3 Months' or '6 Months' into integer months."""
    if not duration_str:
        return 1
    match = re.search(r"(\d+)\s*month", duration_str.lower())
    if match:
        return int(match.group(1))
    return 1


class InternshalaScraper:
    def __init__(self, browser_mgr: Optional[BrowserManager] = None):
        self.browser_mgr = browser_mgr or BrowserManager()

    async def scrape_listings(
        self,
        db: AsyncSession,
        user: User,
        max_pages: int = 2,
    ) -> List[Internship]:
        """Scrapes matching listings from Internshala, filters duplicates against DB, and hydrates detail fields."""
        context = await self.browser_mgr.initialize()
        page = await context.new_page()

        new_internships: List[Internship] = []

        try:
            await self.browser_mgr.ensure_authenticated(page)

            # Build search URLs based on user target roles
            roles = user.target_roles or ["backend-development", "python", "software-development"]
            role_slugs = [r.lower().strip().replace(" ", "-") for r in roles]

            # Primary search query URL
            target_slug = role_slugs[0] if role_slugs else "computer-science"
            remote_prefix = "work-from-home-" if user.allow_remote else ""
            search_url = f"{settings.INTERNSHALA_BASE_URL}/internships/{remote_prefix}{target_slug}-internships"

            logger.info("Navigating to target Internshala search: %s", search_url)

            for page_num in range(1, max_pages + 1):
                paged_url = f"{search_url}/page-{page_num}" if page_num > 1 else search_url
                logger.info("Scraping page %d: %s", page_num, paged_url)

                await page.goto(paged_url, wait_until="domcontentloaded", timeout=settings.ACTION_TIMEOUT_MS)
                await human_delay(1.5, 3.5)
                await human_scroll(page, scrolls=3)

                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")

                cards = soup.select(".individual_internship, div[id^='individual_internship_']")
                logger.info("Found %d raw internship cards on page %d", len(cards), page_num)

                for card in cards:
                    try:
                        # Extract unique ID
                        internshala_id = card.get("internship_id") or card.get("id", "").replace("individual_internship_", "")
                        link_el = card.select_one(".view_detail_button, a.job-title-href, .internship_meta h3 a")
                        if not link_el:
                            continue

                        card_href = link_el.get("href", "")
                        if not internshala_id:
                            # Fallback to URL hash or slug
                            id_match = re.search(r"/(\d+)$", card_href)
                            internshala_id = id_match.group(1) if id_match else card_href.split("/")[-1]

                        if not internshala_id:
                            continue

                        # Check deduplication against PostgreSQL DB
                        stmt = select(Internship.id).where(Internship.internshala_id == internshala_id)
                        res = await db.execute(stmt)
                        if res.scalar_one_or_none():
                            # Already stored
                            continue

                        # Extract basic card metadata
                        title = link_el.get_text(strip=True)
                        company_el = card.select_one(".company_name, div.company-name, .link_display_like_text")
                        company_name = company_el.get_text(strip=True) if company_el else "Unknown Company"

                        location_el = card.select_one(".location_link, #location_names, .locations span")
                        location_text = location_el.get_text(strip=True) if location_el else "Work From Home"
                        locations = [loc.strip() for loc in location_text.split(",") if loc.strip()]
                        is_remote = any("home" in l.lower() or "remote" in l.lower() for l in locations) or user.allow_remote

                        stipend_el = card.select_one(".stipend, span.stipend")
                        stipend_raw = stipend_el.get_text(strip=True) if stipend_el else "Unpaid"
                        min_stipend, max_stipend = parse_stipend_inr(stipend_raw)

                        # Filter out by user minimum stipend threshold early if configured
                        if user.min_stipend_inr > 0 and max_stipend > 0 and max_stipend < user.min_stipend_inr:
                            logger.debug("Skipping %s due to low stipend: %d < %d", title, max_stipend, user.min_stipend_inr)
                            continue

                        duration_el = card.select_one(".duration, .other_detail_item:has(.ic-calendar) .item_body")
                        duration_raw = duration_el.get_text(strip=True) if duration_el else "1 Month"
                        duration_months = parse_duration_months(duration_raw)

                        full_url = f"{settings.INTERNSHALA_BASE_URL}{card_href}" if card_href.startswith("/") else card_href

                        # Detail extraction
                        detail_data = await self._scrape_detail_page(page, full_url)

                        internship_obj = Internship(
                            internshala_id=internshala_id,
                            title=title,
                            company_name=company_name,
                            locations=locations,
                            is_remote=is_remote,
                            stipend_raw=stipend_raw,
                            stipend_min_inr=min_stipend,
                            stipend_max_inr=max_stipend,
                            duration_months=duration_months,
                            url=full_url,
                            about_internship=detail_data.get("about_internship"),
                            skills_required=detail_data.get("skills_required", []),
                            who_can_apply=detail_data.get("who_can_apply"),
                            perks=detail_data.get("perks", []),
                            number_of_openings=detail_data.get("number_of_openings", 1),
                            status="DISCOVERED",
                        )

                        db.add(internship_obj)
                        await db.commit()
                        await db.refresh(internship_obj)
                        new_internships.append(internship_obj)
                        logger.info("Successfully discovered new internship: %s at %s (ID: %s)", title, company_name, internshala_id)

                    except Exception as e:
                        logger.error("Error parsing internship card: %s", str(e), exc_info=True)
                        continue

                await human_delay(2.0, 4.5)

        finally:
            await page.close()
            await self.browser_mgr.close()

        return new_internships

    async def _scrape_detail_page(self, page, detail_url: str) -> Dict[str, Any]:
        """Visits individual detail page to extract in-depth requirements and questions."""
        detail_data: Dict[str, Any] = {
            "about_internship": "",
            "skills_required": [],
            "who_can_apply": "",
            "perks": [],
            "number_of_openings": 1,
        }
        try:
            await page.goto(detail_url, wait_until="domcontentloaded", timeout=settings.ACTION_TIMEOUT_MS)
            await human_delay(1.0, 2.5)

            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")

            # Extract "About the internship"
            about_section = soup.select_one(".text-container, .internship_details .about_internship")
            if about_section:
                detail_data["about_internship"] = about_section.get_text(separator="\n", strip=True)

            # Extract "Skills required"
            skills_tags = soup.select(".round_tabs_container span, .skills_container .round_tabs, .skill_name")
            skills = [s.get_text(strip=True) for s in skills_tags if s.get_text(strip=True)]
            detail_data["skills_required"] = list(dict.fromkeys(skills))

            # Extract "Who can apply"
            who_can_apply_section = soup.select_one(".who_can_apply")
            if who_can_apply_section:
                detail_data["who_can_apply"] = who_can_apply_section.get_text(separator="\n", strip=True)

            # Extract "Perks"
            perks_tags = soup.select(".perks_container .round_tabs, .perks span")
            perks = [p.get_text(strip=True) for p in perks_tags if p.get_text(strip=True)]
            detail_data["perks"] = perks

            # Openings
            openings_match = re.search(r"(\d+)\s*opening", content, re.IGNORECASE)
            if openings_match:
                detail_data["number_of_openings"] = int(openings_match.group(1))

        except Exception as e:
            logger.warning("Could not hydrate full detail page for %s: %s", detail_url, str(e))

        return detail_data
