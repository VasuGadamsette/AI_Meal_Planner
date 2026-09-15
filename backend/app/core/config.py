from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    jwt_secret: str = "change-this-local-secret"
    access_token_expire_minutes: int = 1440
    admin_email: str = "admin@example.com"
    admin_password: str = "ChangeMe123!"
    database_url: str = "sqlite:///./meal_planner.db"
    recipe_dataset: str = "local"
    recipe_limit: int = 5000
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
