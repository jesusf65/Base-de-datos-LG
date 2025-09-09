import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    API_KEY_CRM: str = os.environ.get("API_KEY_CRM")

    POSTGRES_USER: str = os.environ.get("PGUSER")  
    POSTGRES_PASSWORD: str = os.environ.get("PGPASSWORD")  
    POSTGRES_SERVER: str = os.environ.get("PGHOST")  
    POSTGRES_PORT: int = int(os.environ.get("PGPORT", "5432"))  
    POSTGRES_DB: str = os.environ.get("PGDATABASE")  
    
    DATABASE_URL: str = os.environ.get("DATABASE_URL")
    DATABASE_URI: str = (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
        f"{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()