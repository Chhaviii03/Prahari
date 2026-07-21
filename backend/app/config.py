from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "PRAHARI"
    app_version: str = "1.0.0"
    database_url: str = "sqlite+aiosqlite:///./prahari.db"
    secret_key: str = "prahari-hackathon-dev-secret-change-in-prod"
    demo_plant_id: str = "vsp_1"
    demo_org_id: str = "org_vsp"
    anthropic_api_key: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
