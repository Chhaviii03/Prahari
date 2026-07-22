from app.llm.client import MockLLMClient
from app.llm.resilient_client import ResilientLLMClient


class Boom:
    def complete_json(self, system, user, schema_hint):
        raise ConnectionError("simulated failure")


c = ResilientLLMClient()
c._chain = [Boom(), Boom(), MockLLMClient()]
out = c.complete_json(
    "You are a Sensor Interpretation Agent.",
    "Zone: C-12 ch4=8",
    '{"assessment": str}',
)
print("provider", c.last_provider)
print("ok", out.get("assessment") or out)
