"""LLM configuration and provider-agnostic OpenAI-compatible client."""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from openai import OpenAI

from app.config import settings

logger = logging.getLogger("prahari.llm")


class Completer(Protocol):
    def complete_json(self, system: str, user: str, schema_hint: str) -> dict[str, Any]: ...


class LLMClient:
    """OpenAI-compatible chat client — works for Groq, Ollama, OpenAI, Anthropic gateway, etc."""

    def __init__(self, provider: str | None = None):
        provider = (provider or settings.llm_provider).lower()
        self.provider = provider

        if provider == "groq":
            if not settings.groq_api_key:
                raise ValueError("GROQ_API_KEY is not set")
            self.client = OpenAI(
                api_key=settings.groq_api_key,
                base_url=settings.groq_base_url,
                timeout=45.0,
                max_retries=1,
            )
            self.model = settings.groq_model
        elif provider == "ollama":
            self.client = OpenAI(
                api_key="ollama",
                base_url=settings.ollama_base_url,
                timeout=5.0,
                max_retries=0,
            )
            self.model = settings.ollama_model
        elif provider == "mock":
            raise ValueError("Use MockLLMClient for provider=mock")
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    def complete_json(self, system: str, user: str, schema_hint: str) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system + f"\n\nRespond ONLY with valid JSON matching: {schema_hint}",
                },
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON from %s/%s — wrapping raw text", self.provider, self.model)
            return {"raw": content, "parse_error": True}


class MockLLMClient:
    """Deterministic stub for tests / CI — mirrors old template-quality output."""

    def complete_json(self, system: str, user: str, schema_hint: str) -> dict[str, Any]:
        lower = system.lower()
        # Check planner before compliance — planner prompt mentions "Compliance"
        if "planner agent" in lower or "you are the planner" in lower:
            return {
                "narrative": (
                    "Compound hazard indicated by rising gas with conflicting permits and open equipment flag (mock). "
                    "Recommend revoke hot-work, evacuate, and isolate before entry."
                ),
                "recommendations": [
                    {
                        "action": "Revoke hot-work permit; purge zone before entry",
                        "justification": "Eliminates ignition source near rising combustible gas",
                    },
                    {
                        "action": "Evacuate workers from the hazard zone",
                        "justification": "Removes personnel exposure while gas is elevated",
                    },
                ],
                "confidence": 0.8,
            }
        if "sensor interpretation" in lower or ("sensor" in lower and "permit" not in lower):
            return {
                "assessment": "CH₄ elevated with rising trend (mock)",
                "trend_direction": "rising",
                "confidence": 0.86,
            }
        if "permit conflict" in lower or "permit" in lower:
            return {
                "conflict_found": True,
                "conflict_description": "Hot work overlapping confined-entry schedule (mock)",
                "permits_involved": ["HOTWORK", "CONFINED_ENTRY"],
            }
        if "equipment risk" in lower or "equipment" in lower:
            return {
                "relevant": True,
                "note": "Open maintenance flag may relate to gas ingress (mock)",
                "work_order_ref": "WO-8841",
            }
        if "regulatory compliance" in lower or "compliance" in lower:
            return {
                "applicable_clauses": [
                    {
                        "framework": "OISD",
                        "ref": "OISD-GDN-105 §7.2",
                        "text": "Hot work shall not be carried out in or near confined spaces where flammable gas may be present.",
                    }
                ],
                "citation_text": "OISD-GDN-105 §7.2; Factory Act §36",
            }
        return {"assessment": "mocked", "confidence": 0.9}
