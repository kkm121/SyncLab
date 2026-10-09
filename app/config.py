"""SyncLab configuration settings."""
import os
from functools import lru_cache


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./synclab.db")


@lru_cache
def get_settings() -> Settings:
    return Settings()
