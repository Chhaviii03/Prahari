from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "PRAHARI"
    app_version: str = "1.0.0"
    database_url: str = "postgresql+asyncpg://prahari:prahari_dev@localhost:5433/prahari"
    secret_key: str = "prahari-hackathon-dev-secret-change-in-prod"
    demo_plant_id: str = "vsp_1"
    demo_org_id: str = "org_vsp"
    anthropic_api_key: str | None = None

    # LLM — mock | groq | ollama | auto (Groq if key set, else Ollama, else mock)
    llm_provider: str = "auto"
    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.1:8b"
    llm_fallback_ollama: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
