import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Internship, User
from app.schemas.schemas import EligibilityEvaluation
from app.services.llm.client import llm_client

logger = logging.getLogger(__name__)

EVALUATOR_SYSTEM_PROMPT = """You are an expert Technical Recruiter and Job Fit Evaluator specializing in software engineering, data science, and technology internships.
Your job is to objectively evaluate a candidate's profile against an internship posting from Internshala.

CRITICAL INSTRUCTIONS:
1. Evaluate Hard Eligibility Criteria:
   - Graduation Year: Does the candidate meet the "Who can apply" graduation batch criteria?
   - Location: If not remote, is candidate in the preferred city or open to relocation?
   - Duration: Is candidate available for the specified duration (e.g. 3 or 6 months)?
   - CGPA / Degree: Does candidate meet any minimum academic cutoffs if stated?
2. Score Semantic Fit (0 to 100%):
   - 90-100: Exceptional alignment; matches all core technologies and role requirements.
   - 75-89: Strong match; possess core skills, minor peripheral skills can be quickly learned.
   - 50-74: Moderate match; missing 1-2 important stack components or experience.
   - < 50: Poor fit; fundamentally different domain or hard disqualifiers.
3. Extract missing keywords: list exact technology and domain keywords present in the JD that are absent from candidate's profile.
"""


class LLMEvaluator:
    @staticmethod
    async def evaluate_listing(user: User, internship: Internship) -> EligibilityEvaluation:
        """Evaluates whether an internship meets user's hard eligibility and calculates fit score."""
        user_profile_summary = f"""
Candidate Name: {user.full_name}
Degree & College: {user.degree}
Graduation Year: {user.graduation_year}
CGPA: {user.cgpa}
Target Roles: {', '.join(user.target_roles)}
Primary Skills: {', '.join(user.primary_skills)}
Preferred Locations: {', '.join(user.preferred_locations)}
Remote Work Allowed: {user.allow_remote}
Preferred Duration: {user.min_duration_months} - {user.max_duration_months} months
Base Resume Summary:
{user.base_resume_text[:2500]}
"""

        job_posting_summary = f"""
Title: {internship.title}
Company: {internship.company_name}
Locations: {', '.join(internship.locations)} (Is Remote: {internship.is_remote})
Stipend: {internship.stipend_raw}
Duration: {internship.duration_months} months
Skills Required: {', '.join(internship.skills_required)}
About the Internship:
{internship.about_internship or 'Not provided'}
Who Can Apply:
{internship.who_can_apply or 'Not provided'}
"""

        user_prompt = f"""
Please evaluate this candidate against the internship posting below:

### CANDIDATE PROFILE:
{user_profile_summary}

### INTERNSHIP POSTING:
{job_posting_summary}
"""

        try:
            evaluation: EligibilityEvaluation = await llm_client.generate_structured(
                prompt=user_prompt,
                system_instruction=EVALUATOR_SYSTEM_PROMPT,
                response_model=EligibilityEvaluation,
            )
            return evaluation
        except Exception as e:
            logger.error("LLM evaluation failed for internship %s: %s", internship.internshala_id, str(e))
            # Fallback safe response
            return EligibilityEvaluation(
                is_eligible=False,
                match_score=0,
                hard_criteria_checks=[],
                matching_skills=[],
                missing_skills=internship.skills_required,
                summary_verdict=f"Automated evaluation failed: {str(e)}",
            )
