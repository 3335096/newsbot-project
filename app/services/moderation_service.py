from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.db.models.moderation_rule import ModerationRule


@dataclass
class ModerationOutcome:
    blocked: bool
    flagged: bool
    flags: list[dict]


class ModerationService:
    def __init__(self, db: Session):
        self.db = db

    def evaluate_article(
        self,
        *,
        url: str,
        title: str | None,
        content: str | None,
    ) -> ModerationOutcome:
        rules = self.db.query(ModerationRule).filter(ModerationRule.enabled.is_(True)).all()
        flags: list[dict] = []

        text_for_scan = f"{title or ''}\n{content or ''}"
        hostname = urlparse(url).netloc.lower()

        for rule in rules:
            if not rule.pattern:
                continue
            matched = False

            if rule.kind == "domain_blacklist":
                matched = self._match(rule.pattern, hostname) or self._match(rule.pattern, url)
            elif rule.kind == "keyword_blacklist":
                matched = self._match(rule.pattern, text_for_scan)

            if matched:
                flags.append(
                    {
                        "rule_id": rule.id,
                        "kind": rule.kind,
                        "pattern": rule.pattern,
                        "action": rule.action,
                        "comment": rule.comment,
                    }
                )

        blocked = any(f["action"] == "block" for f in flags)
        flagged = any(f["action"] == "flag" for f in flags) or blocked
        return ModerationOutcome(blocked=blocked, flagged=flagged, flags=flags)

    def list_rules(self) -> list[ModerationRule]:
        return (
            self.db.query(ModerationRule)
            .order_by(ModerationRule.id.asc())
            .all()
        )

    def create_rule(
        self,
        *,
        kind: str,
        pattern: str,
        action: str,
        enabled: bool = True,
        comment: str | None = None,
    ) -> ModerationRule:
        if kind not in {"domain_blacklist", "keyword_blacklist"}:
            raise ValueError("Unsupported rule kind")
        if action not in {"block", "flag"}:
            raise ValueError("Unsupported action")
        rule = ModerationRule(
            kind=kind,
            pattern=pattern,
            action=action,
            enabled=enabled,
            comment=comment,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def toggle_rule(self, rule_id: int) -> ModerationRule:
        rule = self.db.query(ModerationRule).filter(ModerationRule.id == rule_id).first()
        if not rule:
            raise ValueError("Rule not found")
        rule.enabled = not rule.enabled
        self.db.commit()
        self.db.refresh(rule)
        return rule

    @staticmethod
    def _match(pattern: str, target: str) -> bool:
        target = target or ""
        try:
            return re.search(pattern, target, re.IGNORECASE) is not None
        except re.error:
            return pattern.lower() in target.lower()
