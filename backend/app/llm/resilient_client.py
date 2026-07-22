"""Groq primary → Ollama → Mock resilient client (never crash the demo)."""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.llm.client import Completer, LLMClient, MockLLMClient

logger = logging.getLogger("prahari.llm")


class ResilientLLMClient:
    """
    Provider selection:
      LLM_PROVIDER=mock|groq|ollama|auto
      auto = Groq (if key) → Ollama (if enabled) → Mock
    Failures never raise to the API — mock is the last resort so /demo/load-scenario stays 200.
    """

    def __init__(self):
        mode = (settings.llm_provider or "auto").lower()
        self.mode = mode
        self.last_provider: str = mode
        self.last_model: str = ""
        self._chain: list[Completer] = []

        if mode == "mock":
            self._chain = [MockLLMClient()]
        elif mode == "ollama":
            self._chain = [LLMClient("ollama"), MockLLMClient()]
        elif mode == "groq":
            self._chain = [LLMClient("groq")]
            if settings.llm_fallback_ollama:
                self._chain.append(LLMClient("ollama"))
            self._chain.append(MockLLMClient())
        else:  # auto
            if settings.groq_api_key and settings.groq_api_key.strip():
                self._chain.append(LLMClient("groq"))
            if settings.llm_fallback_ollama:
                self._chain.append(LLMClient("ollama"))
            self._chain.append(MockLLMClient())

        # Ensure at least mock
        if not self._chain:
            self._chain = [MockLLMClient()]

        first = self._chain[0]
        self._set_last(first)

    def _set_last(self, client: Completer) -> None:
        if isinstance(client, LLMClient):
            self.last_provider = client.provider
            self.last_model = client.model
        else:
            self.last_provider = "mock"
            self.last_model = "mock"

    def complete_json(self, system: str, user: str, schema_hint: str) -> dict[str, Any]:
        errors: list[str] = []
        for i, client in enumerate(self._chain):
            label = (
                client.provider if isinstance(client, LLMClient) else "mock"
            )
            try:
                result = client.complete_json(system, user, schema_hint)
                self._set_last(client)
                if i > 0:
                    logger.warning("LLM recovered via fallback provider=%s", label)
                return result
            except Exception as exc:
                errors.append(f"{label}: {exc}")
                logger.warning("LLM provider %s failed (%s); trying next", label, exc)
                continue

        # Should be unreachable because MockLLMClient does not raise
        logger.error("All LLM providers failed: %s", errors)
        self.last_provider = "mock"
        self.last_model = "mock"
        return MockLLMClient().complete_json(system, user, schema_hint)
