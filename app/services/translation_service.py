from app.services.llm_client import LLMClient
from core.config import settings

class TranslationService:
    def __init__(self):
        self.llm_client = LLMClient()

    async def translate_text(self, text: str, target_language: str = settings.DEFAULT_TARGET_LANGUAGE, model: str = settings.LLM_DEFAULT_MODEL_TRANSLATE) -> str:
        prompt = f"Translate the following text to {target_language}:\n\n{text}"
        response = await self.llm_client.generate_text(model=model, prompt=prompt)
        return response.get("choices", [{}])[0].get("message", {}).get("content", "")

