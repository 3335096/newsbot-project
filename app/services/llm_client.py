from __future__ import annotations

import asyncio
from typing import Any

import httpx

from core.config import settings


class LLMClient:
    def __init__(self, timeout_seconds: int = 60):
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://openrouter.ai/api/v1"

    async def generate_text(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        if not settings.OPENROUTER_API_KEY:
            return {}

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        # Basic resilient network behavior for MVP.
        delay = 1
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(
                    base_url=self.base_url, timeout=self.timeout_seconds
                ) as client:
                    response = await client.post("/chat/completions", headers=headers, json=payload)
                    response.raise_for_status()
                    return response.json()
            except (httpx.HTTPError, httpx.TimeoutException):
                if attempt == 2:
                    raise
                await asyncio.sleep(delay)
                delay *= 2

        return {}
