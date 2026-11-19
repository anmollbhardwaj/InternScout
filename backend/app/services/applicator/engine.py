import asyncio
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Application, Internship, ResumeVersion, User
from app.services.scraper.browser import BrowserManager, human_delay
from app.services.websocket.manager import ws_manager

logger = logging.getLogger(__name__)


class ApplicationEngine:
    def __init__(self, browser_mgr: Optional[BrowserManager] = None):
        self.browser_mgr = browser_mgr or BrowserManager()

    async def apply_to_internship(
        self,
        db: AsyncSession,
        application_id: str,
    ) -> bool:
        """Executes automated application submission via Playwright stealth browser."""
        stmt = (
            select(Application)
            .where(Application.id == application_id)
        )
        res = await db.execute(stmt)
        application = res.scalar_one_or_none()

        if not application:
            logger.error("Application ID %s not found", application_id)
            return False

        # Load related data
        user_stmt = select(User).where(User.id == application.user_id)
        user = (await db.execute(user_stmt)).scalar_one()

        internship_stmt = select(Internship).where(Internship.id == application.internship_id)
        internship = (await db.execute(internship_stmt)).scalar_one()

        resume_ver_stmt = select(ResumeVersion).where(ResumeVersion.id == application.resume_version_id)
        resume_ver = (await db.execute(resume_ver_stmt)).scalar_one_or_none()

        application.status = "IN_PROGRESS"
        await db.commit()

        await ws_manager.broadcast_json("APPLICATION_PROGRESS", {
            "application_id": str(application.id),
            "status": "IN_PROGRESS",
            "message": f"Launching browser to apply for {internship.title} at {internship.company_name}..."
        })

        context = await self.browser_mgr.initialize(headless=settings.HEADLESS_BROWSER)
        page = await context.new_page()

        try:
            # Ensure session is logged in
            is_auth = await self.browser_mgr.ensure_authenticated(page)
            if not is_auth:
                raise Exception("Cannot apply: Session is not authenticated on Internshala.")

            logger.info("Navigating to internship application page: %s", internship.url)
            await page.goto(internship.url, wait_until="domcontentloaded", timeout=settings.ACTION_TIMEOUT_MS)
            await human_delay(2.0, 4.0)

            # Check if already applied
            already_applied = await page.locator("button.already_applied, span:has-text('Already Applied')").count() > 0
            if already_applied:
                application.status = "SUBMITTED"
                application.applied_at = datetime.utcnow()
                application.error_message = "Listing was already marked as applied on Internshala."
                await db.commit()
                return True

            # Click Apply Now
            apply_btn = page.locator("#apply_now_button, .apply_now_button, button:has-text('Apply now')").first
            if await apply_btn.count() == 0:
                raise Exception("Could not find 'Apply now' button on page.")

            await apply_btn.click()
            await human_delay(1.5, 3.0)

            # Check for "Proceed to application" or assessment modal
            proceed_btn = page.locator("#proceed_to_application, button:has-text('Proceed to application')").first
            if await proceed_btn.count() > 0:
                await proceed_btn.click()
                await human_delay(1.5, 3.0)

            # Fill Assessment Questions
            # 1. Why should you be hired?
            cover_letter = resume_ver.cover_letter_text if resume_ver else "I am an eager developer with relevant skills."
            cover_letter_box = page.locator("textarea#cover_letter, textarea[name='cover_letter'], textarea[placeholder*='Why should you be hired']").first
            if await cover_letter_box.count() > 0:
                await cover_letter_box.click()
                await cover_letter_box.fill("")
                # Type in chunks to look natural
                for paragraph in cover_letter.split("\n"):
                    await cover_letter_box.type(paragraph + "\n", delay=random.randint(15, 35))
                await human_delay(0.8, 1.5)

            # 2. Availability question (e.g. Yes, I am available for 3 months)
            avail_radio = page.locator("input[type='radio'][value='yes'], input#availability_yes").first
            if await avail_radio.count() > 0:
                await avail_radio.click()
                await human_delay(0.5, 1.0)

            # 3. Custom Screening Questions
            if resume_ver and resume_ver.custom_qa_answers:
                textareas = await page.locator("textarea.assessment_question, div.assessment_question textarea").all()
                for idx, textarea in enumerate(textareas):
                    # Answer with grounded response
                    ans = list(resume_ver.custom_qa_answers.values())[idx % len(resume_ver.custom_qa_answers)]
                    await textarea.fill(ans)
                    await human_delay(0.5, 1.2)

            # 4. Upload tailored PDF if present
            if resume_ver and resume_ver.pdf_storage_path and Path(resume_ver.pdf_storage_path).exists():
                upload_input = page.locator("input[type='file']#custom_resume, input[type='file'][name='custom_resume']").first
                if await upload_input.count() > 0:
                    await upload_input.set_input_files(resume_ver.pdf_storage_path)
                    await human_delay(1.0, 2.0)

            # Submit Application
            submit_btn = page.locator("input#submit, button#submit, button:has-text('Submit')").first
            if await submit_btn.count() > 0:
                await submit_btn.click()
                await human_delay(3.0, 5.0)

            # Capture verification screenshot
            screenshot_filename = f"app_{application.id}_{int(datetime.utcnow().timestamp())}.png"
            screenshot_path = settings.SCREENSHOT_DIR / screenshot_filename
            await page.screenshot(path=str(screenshot_path), full_page=True)

            application.status = "SUBMITTED"
            application.applied_at = datetime.utcnow()
            application.submission_screenshot_path = str(screenshot_path)
            internship.status = "APPLIED"
            await db.commit()

            await ws_manager.broadcast_json("APPLICATION_PROGRESS", {
                "application_id": str(application.id),
                "status": "SUBMITTED",
                "message": f"Successfully applied for {internship.title} at {internship.company_name}!"
            })
            logger.info("Successfully applied for internship %s (App ID: %s)", internship.title, application.id)
            return True

        except Exception as e:
            logger.error("Failed to submit application: %s", str(e), exc_info=True)
            # Capture error state screenshot
            err_screenshot = settings.SCREENSHOT_DIR / f"err_{application.id}.png"
            try:
                await page.screenshot(path=str(err_screenshot))
                application.submission_screenshot_path = str(err_screenshot)
            except Exception:
                pass

            application.status = "FAILED"
            application.error_message = str(e)
            await db.commit()

            await ws_manager.broadcast_json("APPLICATION_PROGRESS", {
                "application_id": str(application.id),
                "status": "FAILED",
                "message": f"Application failed: {str(e)}"
            })
            return False

        finally:
            await page.close()
            await self.browser_mgr.close()


application_engine = ApplicationEngine()
