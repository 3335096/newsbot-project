import httpx
from core.config import settings

class LLMClient:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url="https://openrouter.ai/api/v1")
        self.headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

    async def generate_text(self, model: str, prompt: str, temperature: float = 0.7):
        if not settings.OPENROUTER_API_KEY:
            return ""

        data = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
        }
        response = await self.client.post("/chat/completions", headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
