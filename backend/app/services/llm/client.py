import json
import logging
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Unified client supporting both Google Gemini API and OpenAI API with Pydantic JSON schema extraction."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self._init_client()

    def _init_client(self):
        if self.provider == "gemini":
            import google.generativeai as genai
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                generation_config={"response_mime_type": "application/json"}
            )
        elif self.provider == "openai":
            from openai import AsyncOpenAI
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate_structured(
        self,
        prompt: str,
        system_instruction: str,
        response_model: Type[T]
    ) -> T:
        """Executes LLM call and returns validated Pydantic model instance."""
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        augmented_prompt = f"""
{prompt}

CRITICAL: Return ONLY valid JSON adhering strictly to the JSON schema below. Do not wrap in markdown or backticks.
Schema:
{schema_json}
"""
        if self.provider == "openai":
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": augmented_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            raw_text = response.choices[0].message.content or "{}"
            return response_model.model_validate_json(raw_text)

        else:
            # Google Gemini
            import google.generativeai as genai
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                system_instruction=system_instruction,
                generation_config={"response_mime_type": "application/json", "temperature": 0.2}
            )
            response = await model.generate_content_async(augmented_prompt)
            raw_text = response.text
            # Clean possible markdown fence if present
            cleaned_text = raw_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            return response_model.model_validate_json(cleaned_text.strip())


llm_client = LLMClient()
