import asyncio
import logging
import time
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import User, Internship, ScraperRun
from app.schemas.schemas import InternshipResponse, WSMatchAlertPayload, BulletDiff
from app.services.scraper.internshala import InternshalaScraper
from app.services.llm.evaluator import LLMEvaluator
from app.services.llm.tailor import LLMResumeTailor
from app.services.websocket.manager import ws_manager

logger = logging.getLogger(__name__)

# Mutex to prevent overlapping Playwright sessions
scrape_lock = asyncio.Lock()


class AutomationScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scraper = InternshalaScraper()

    def start(self) -> None:
        """Register scheduled jobs and start APScheduler."""
        # 1. Hourly Delta Scraper
        self.scheduler.add_job(
            self.run_hourly_delta_sync,
            trigger=IntervalTrigger(minutes=settings.HOURLY_DELTA_INTERVAL_MINUTES),
            id="hourly_delta_scraper",
            name="Hourly Internshala Delta Scraper",
            replace_existing=True,
        )

        # 2. Daily Deep Sync
        self.scheduler.add_job(
            self.run_daily_deep_sync,
            trigger=CronTrigger(hour=settings.DAILY_DEEP_SYNC_HOUR, minute=0),
            id="daily_deep_sync",
            name="Daily Deep Catalog Sync",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Automation scheduler started: hourly delta (%d min) & daily deep sync (%d:00)",
                    settings.HOURLY_DELTA_INTERVAL_MINUTES, settings.DAILY_DEEP_SYNC_HOUR)

    def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
        logger.info("Automation scheduler stopped.")

    async def run_hourly_delta_sync(self) -> None:
        """Scheduled worker task executed every hour for fast turnaround alerts."""
        if scrape_lock.locked():
            logger.warning("Scraper lock currently acquired. Skipping overlapping hourly run.")
            return

        async with scrape_lock:
            start_time = time.time()
            logger.info("Starting hourly delta scraping job...")

            async with AsyncSessionLocal() as db:
                try:
                    # Get primary active user profile
                    stmt = select(User).where(User.is_active == True).limit(1)
                    res = await db.execute(stmt)
                    user = res.scalar_one_or_none()

                    if not user:
                        logger.warning("No active User profile found. Aborting scrape task.")
                        return

                    # Run delta scrape
                    new_listings = await self.scraper.scrape_listings(
                        db=db,
                        user=user,
                        max_pages=settings.MAX_PAGES_DELTA,
                    )

                    high_matches = 0
                    for internship in new_listings:
                        # Step 1: LLM Eligibility & Fit Evaluation
                        eval_res = await LLMEvaluator.evaluate_listing(user, internship)
                        internship.match_score = eval_res.match_score
                        internship.eligibility_verdict = eval_res.model_dump()
                        internship.missing_skills = eval_res.missing_skills

                        if eval_res.is_eligible and eval_res.match_score >= settings.MIN_MATCH_THRESHOLD:
                            internship.status = "MATCHED"
                            high_matches += 1
                            await db.commit()

                            # Step 2: Generate Tailored Resume Diffs & Q&A
                            resume_ver = await LLMResumeTailor.generate_tailored_version(db, user, internship)

                            # Step 3: Broadcast real-time interactive alert over WebSocket
                            bullet_diffs_typed = [BulletDiff(**b) for b in resume_ver.bullet_diffs]
                            alert_payload = WSMatchAlertPayload(
                                internship=InternshipResponse.model_validate(internship),
                                resume_version_id=resume_ver.id,
                                match_score=eval_res.match_score,
                                summary_verdict=eval_res.summary_verdict,
                                missing_skills=eval_res.missing_skills,
                                tailored_headline=resume_ver.tailored_headline or "",
                                tailored_summary=resume_ver.tailored_summary or "",
                                bullet_diffs=bullet_diffs_typed,
                                cover_letter=resume_ver.cover_letter_text or "",
                                assessment_answers=resume_ver.custom_qa_answers or {},
                            )

                            await ws_manager.broadcast_json("NEW_MATCH_ALERT", alert_payload.model_dump())
                            logger.info("Broadcasted NEW_MATCH_ALERT for internship %s (%d%%)", internship.title, eval_res.match_score)
                        else:
                            internship.status = "DISQUALIFIED" if not eval_res.is_eligible else "SKIPPED"
                            await db.commit()

                    # Record run audit
                    duration = time.time() - start_time
                    run_log = ScraperRun(
                        run_type="HOURLY_DELTA",
                        items_scraped=len(new_listings),
                        new_items_saved=len(new_listings),
                        high_matches_found=high_matches,
                        duration_seconds=round(duration, 2),
                        status="SUCCESS",
                    )
                    db.add(run_log)
                    await db.commit()
                    logger.info("Hourly delta scraping completed in %.2fs. %d new items, %d high matches.",
                                duration, len(new_listings), high_matches)

                except Exception as e:
                    logger.error("Hourly delta job failed: %s", str(e), exc_info=True)
                    run_log = ScraperRun(
                        run_type="HOURLY_DELTA",
                        duration_seconds=round(time.time() - start_time, 2),
                        status="FAILED",
                        error_log=str(e),
                    )
                    db.add(run_log)
                    await db.commit()

    async def run_daily_deep_sync(self) -> None:
        """Deep sync executed daily to catalog broader opportunities and purge expired listings."""
        if scrape_lock.locked():
            return

        async with scrape_lock:
            start_time = time.time()
            logger.info("Starting daily deep sync job...")
            async with AsyncSessionLocal() as db:
                try:
                    stmt = select(User).where(User.is_active == True).limit(1)
                    res = await db.execute(stmt)
                    user = res.scalar_one_or_none()
                    if not user:
                        return

                    new_listings = await self.scraper.scrape_listings(
                        db=db,
                        user=user,
                        max_pages=settings.MAX_PAGES_DEEP,
                    )

                    duration = time.time() - start_time
                    run_log = ScraperRun(
                        run_type="DAILY_DEEP_SYNC",
                        items_scraped=len(new_listings),
                        new_items_saved=len(new_listings),
                        duration_seconds=round(duration, 2),
                        status="SUCCESS",
                    )
                    db.add(run_log)
                    await db.commit()
                    logger.info("Daily deep sync completed in %.2fs. %d new items saved.", duration, len(new_listings))
                except Exception as e:
                    logger.error("Daily deep sync failed: %s", str(e), exc_info=True)


scheduler_service = AutomationScheduler()
