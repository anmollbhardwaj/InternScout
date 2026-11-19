import asyncio
import json
import logging
import random
from pathlib import Path
from typing import Optional, Dict, Any, List

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from app.core.config import settings

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
]


async def human_delay(min_s: Optional[float] = None, max_s: Optional[float] = None) -> None:
    """Randomized non-uniform delay to mimic human behavior."""
    min_val = min_s if min_s is not None else settings.SCRAPE_MIN_DELAY_SEC
    max_val = max_s if max_s is not None else settings.SCRAPE_MAX_DELAY_SEC
    delay = random.uniform(min_val, max_val)
    await asyncio.sleep(delay)


async def human_scroll(page: Page, scrolls: int = 3) -> None:
    """Smooth incremental scrolling with jitter to simulate human reading."""
    for _ in range(scrolls):
        scroll_step = random.randint(300, 700)
        await page.evaluate(f"window.scrollBy({{ top: {scroll_step}, behavior: 'smooth' }});")
        await human_delay(0.8, 1.8)


class BrowserManager:
    """Manages resilient Playwright instances with stealth evasion and persistent session state."""

    def __init__(self, session_name: str = "internshala_state.json"):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.session_path: Path = settings.SESSION_DIR / session_name

    async def initialize(self, headless: Optional[bool] = None) -> BrowserContext:
        is_headless = headless if headless is not None else settings.HEADLESS_BROWSER
        self.playwright = await async_playwright().start()

        viewport = random.choice(VIEWPORTS)
        user_agent = random.choice(USER_AGENTS)

        # Launch Chromium with stealth flags
        self.browser = await self.playwright.chromium.launch(
            headless=is_headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-position=0,0",
                f"--window-size={viewport['width']},{viewport['height']}",
            ],
        )

        context_kwargs: Dict[str, Any] = {
            "viewport": viewport,
            "user_agent": user_agent,
            "locale": "en-US",
            "timezone_id": "Asia/Kolkata",
            "permissions": ["geolocation"],
            "geolocation": {"latitude": 28.6139, "longitude": 77.2090},  # Delhi / India default
        }

        # Load session state if exists
        if self.session_path.exists():
            logger.info("Found existing session cookies at %s", self.session_path)
            context_kwargs["storage_state"] = str(self.session_path)

        self.context = await self.browser.new_context(**context_kwargs)

        # Apply stealth evasions
        await self._apply_stealth(self.context)

        return self.context

    async def _apply_stealth(self, context: BrowserContext) -> None:
        """Inject scripts before any script execution to evade bot detection."""
        stealth_script = """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        window.navigator.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        """
        await context.add_init_script(stealth_script)

    async def save_session_state(self) -> None:
        """Persist cookies and localStorage to disk."""
        if self.context:
            await self.context.storage_state(path=str(self.session_path))
            logger.info("Saved browser session state to %s", self.session_path)

    async def ensure_authenticated(self, page: Page) -> bool:
        """Verify login status on Internshala. Perform login if session is expired or missing."""
        try:
            await page.goto(f"{settings.INTERNSHALA_BASE_URL}/internships", wait_until="domcontentloaded", timeout=settings.ACTION_TIMEOUT_MS)
            await human_delay(1.5, 3.0)

            # Check if user profile dropdown exists or login button is shown
            is_logged_in = await page.locator("div.profile_container, a.profile_icon, #profile_dropdown").count() > 0

            if is_logged_in:
                logger.info("Playwright session is authenticated with Internshala.")
                return True

            logger.warning("Session not authenticated. Initiating stealth login...")
            if not settings.INTERNSHALA_EMAIL or not settings.INTERNSHALA_PASSWORD:
                logger.warning("No INTERNSHALA_EMAIL or INTERNSHALA_PASSWORD configured. Operating in public guest mode.")
                return False

            # Click login modal button
            login_btn = page.locator("button.login-cta, a.login_modal, button:has-text('Login')").first
            if await login_btn.count() > 0:
                await login_btn.click()
                await human_delay(1.0, 2.0)

                # Fill credentials with human typing speed
                email_input = page.locator("input#modal_email, input[name='email']")
                password_input = page.locator("input#modal_password, input[name='password']")

                if await email_input.count() > 0:
                    await email_input.click()
                    for char in settings.INTERNSHALA_EMAIL:
                        await email_input.type(char, delay=random.randint(40, 110))
                    
                    await human_delay(0.5, 1.2)
                    await password_input.click()
                    for char in settings.INTERNSHALA_PASSWORD:
                        await password_input.type(char, delay=random.randint(40, 110))
                    
                    await human_delay(0.8, 1.5)
                    submit_btn = page.locator("button#modal_login_submit, button:has-text('Login')").first
                    await submit_btn.click()

                    await page.wait_for_load_state("networkidle", timeout=15000)
                    await human_delay(2.0, 3.5)

                    await self.save_session_state()
                    logger.info("Stealth login successful. Session state saved.")
                    return True
        except Exception as e:
            logger.error("Authentication check failed: %s", str(e))
            return False
        return False

    async def close(self) -> None:
        try:
            if self.context:
                await self.save_session_state()
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error("Error closing browser manager: %s", str(e))
