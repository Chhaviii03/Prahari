"""Smoke-test which LLM provider is active and that it returns JSON."""

from __future__ import annotations

import json
import sys

from app.config import settings
from app.llm.resilient_client import ResilientLLMClient


def main() -> int:
    print("llm_provider setting:", settings.llm_provider)
    print("groq_api_key set:", bool(settings.groq_api_key and settings.groq_api_key.strip()))
    print("ollama_url:", settings.ollama_base_url)

    client = ResilientLLMClient()
    print("resolved provider:", client.last_provider)
    print("resolved model:", client.last_model)

    out = client.complete_json(
        system=(
            "You are a Sensor Interpretation Agent for an industrial safety system. "
            "You receive raw sensor readings and a trend. Output ONLY facts derivable "
            "from the data — no speculation about cause."
        ),
        user='Zone state: {"zone_id": "C-12", "ch4_lel": 8.0, "forecast_eta_minutes": 40}',
        schema_hint='{"assessment": str, "trend_direction": str, "confidence": float}',
    )
    print("provider_after_call:", client.last_provider)
    print("model_after_call:", client.last_model)
    print("output:")
    print(json.dumps(out, indent=2, ensure_ascii=False))

    if client.last_provider == "mock":
        print(
            "\nRESULT: MOCK only — not a real LLM.\n"
            "Add GROQ_API_KEY to backend/.env (https://console.groq.com/keys)\n"
            "or install/start Ollama and set LLM_PROVIDER=ollama."
        )
        return 2

    print("\nRESULT: Real LLM responded successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
