import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Internship, User, ResumeVersion
from app.schemas.schemas import ResumeTailoringResult, BulletDiff
from app.services.llm.client import llm_client

logger = logging.getLogger(__name__)

TAILOR_SYSTEM_PROMPT = """You are a Senior Principal Resume Architect and ATS Optimization Engineer.
Your task is to tailor a candidate's resume and generate tailored application answers for an Internshala internship listing.

STRICT GROUNDING RULES:
1. NEVER hallucinate fake degrees, fake companies, or ungrounded credentials.
2. Only rewrite and enhance existing accomplishments from the Base Resume using strong action verbs (e.g., "Architected", "Engineered", "Implemented", "Optimized") and incorporating exact keywords from the target Job Description.
3. Quantify impact where plausible based on context.
4. For "cover_letter" / "Why should you be hired for this role?":
   - Write a compelling, concise (150-250 words) response.
   - Specifically connect 2-3 concrete projects or skills from the candidate's base resume directly to the company's stated requirements.
   - Maintain a passionate, humble, and professional engineering tone.
5. Provide structured bullet diffs showing:
   - "section": (e.g., "Work Experience", "Projects", "Technical Skills")
   - "original_bullet": the exact text from candidate's base resume
   - "suggested_bullet": the tailored version
   - "reason": why this change aligns with the JD
"""


class LLMResumeTailor:
    @staticmethod
    async def generate_tailored_version(
        db: AsyncSession,
        user: User,
        internship: Internship,
    ) -> ResumeVersion:
        """Generates bullet diffs and application Q&A answers, then persists a new ResumeVersion."""
        user_prompt = f"""
### CANDIDATE BASE RESUME:
{user.base_resume_text}

### TARGET INTERNSHIP:
Role Title: {internship.title}
Company: {internship.company_name}
Required Skills: {', '.join(internship.skills_required)}
About Internship:
{internship.about_internship}
Who Can Apply:
{internship.who_can_apply}

Generate a tailored resume adjustment plan and custom screening answers.
"""

        try:
            tailored_data: ResumeTailoringResult = await llm_client.generate_structured(
                prompt=user_prompt,
                system_instruction=TAILOR_SYSTEM_PROMPT,
                response_model=ResumeTailoringResult,
            )

            # Persist to ResumeVersion
            bullet_diffs_dicts = [b.model_dump() for b in tailored_data.bullet_diffs]

            resume_version = ResumeVersion(
                user_id=user.id,
                internship_id=internship.id,
                version_number=1,
                tailored_headline=tailored_data.tailored_headline,
                tailored_summary=tailored_data.tailored_summary,
                bullet_diffs=bullet_diffs_dicts,
                skills_highlighted=tailored_data.skills_to_highlight,
                cover_letter_text=tailored_data.cover_letter,
                custom_qa_answers=tailored_data.assessment_answers,
                status="PENDING_APPROVAL",
            )

            db.add(resume_version)
            await db.commit()
            await db.refresh(resume_version)
            logger.info("Successfully generated tailored resume version (ID: %s) for internship %s", resume_version.id, internship.title)
            return resume_version

        except Exception as e:
            logger.error("Failed to generate resume tailoring: %s", str(e), exc_info=True)
            # Create a fallback draft
            fallback_version = ResumeVersion(
                user_id=user.id,
                internship_id=internship.id,
                version_number=1,
                tailored_headline=f"Aspiring {internship.title}",
                tailored_summary="Motivated developer with strong problem-solving skills.",
                bullet_diffs=[],
                skills_highlighted=user.primary_skills,
                cover_letter_text=f"I am excited to apply for the {internship.title} role at {internship.company_name}. My background in {', '.join(user.primary_skills[:3])} aligns well with your requirements.",
                custom_qa_answers={"Why should you be hired?": "I possess hands-on project experience matching your requirements."},
                status="PENDING_APPROVAL",
            )
            db.add(fallback_version)
            await db.commit()
            await db.refresh(fallback_version)
            return fallback_version
