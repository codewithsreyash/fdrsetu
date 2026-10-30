from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://fdrsetu:fdrsetu@localhost:5432/fdrsetu"
    JWT_SECRET: str = "fdrsetu-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 12
    UPLOAD_DIR: str = "../uploads"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    MOCK_BANK_API: bool = True
    # Optional real integrations (mock mode used when unset)
    OPENAI_API_KEY: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"


settings = Settings()
