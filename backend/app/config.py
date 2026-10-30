from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://fdrsetu:fdrsetu@localhost:5432/fdrsetu"
    JWT_SECRET: str = "fdrsetu-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 12
    UPLOAD_DIR: str = "../uploads"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    MOCK_BANK_API: bool = True
    SEED_DEMO: bool = False          # seed demo data on startup when DB is empty
    # Optional real integrations (mock mode used when unset)
    OPENAI_API_KEY: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        # Render/Heroku-style URLs: postgres:// or postgresql:// — pin the driver
        if v.startswith("postgres://"):
            return "postgresql+psycopg2://" + v[len("postgres://"):]
        if v.startswith("postgresql://") and "+" not in v.split("://", 1)[0]:
            return "postgresql+psycopg2://" + v[len("postgresql://"):]
        return v

    class Config:
        env_file = ".env"


settings = Settings()
