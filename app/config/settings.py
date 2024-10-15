from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    TITLE: str = "Fast API"
    DESCRIPTION: str = "Fast API for Welspy"
    
    DB_NAME: str
    DB_HOST: str
    DB_USER: str
    DB_PASSWORD: str
    DB_PORT: int
    
    REDIS_HOST: str
    REDIS_PORT: str

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()