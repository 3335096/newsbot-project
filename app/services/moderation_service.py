from app.services.llm_client import LLMClient
from app.db.models.moderation_rule import ModerationRule
from sqlalchemy.orm import Session
import re

class ModerationService:
    def __init__(self, db: Session):
        self.db = db
        self.llm_client = LLMClient()

    async def moderate_text(self, text: str) -> dict:
        flags = {}
        rules = self.db.query(ModerationRule).filter(ModerationRule.enabled == True).all()

        for rule in rules:
            if rule.kind == "keyword_blacklist" and rule.pattern:
                if rule.pattern.lower() in text.lower():
                    flags[rule.pattern] = {"action": rule.action}
            elif rule.kind == "regex" and rule.pattern:
                if re.search(rule.pattern, text, re.IGNORECASE):
                    flags[rule.pattern] = {"action": rule.action}
            elif rule.kind == "llm":
                # For LLM-based moderation, we'd typically send the text to an LLM
                # and parse its response. This is a placeholder.
                # prompt = f"Moderate the following text for {rule.name}: {text}"
                # llm_response = await self.llm_client.generate_text(model="some_moderation_model", prompt=prompt)
                # if "flagged" in llm_response.lower():
                #     flags[rule.name] = {"severity": rule.severity, "action": rule.action}
                pass
        return flags
