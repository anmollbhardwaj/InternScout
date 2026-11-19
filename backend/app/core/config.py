from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "InternScout"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/internscout",
        description="Async PostgreSQL connection string"
    )

    # LLM Settings
    LLM_PROVIDER: str = Field(default="gemini", description="'gemini' or 'openai'")
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-pro"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"

    # Internshala Account & Scraper
    INTERNSHALA_EMAIL: Optional[str] = None
    INTERNSHALA_PASSWORD: Optional[str] = None
    INTERNSHALA_BASE_URL: str = "https://internshala.com"
    HEADLESS_BROWSER: bool = True
    MIN_MATCH_THRESHOLD: int = 75  # 0 to 100

    # Scraper Frequency
    HOURLY_DELTA_INTERVAL_MINUTES: int = 60
    DAILY_DEEP_SYNC_HOUR: int = 2  # 2 AM daily
    MAX_PAGES_DELTA: int = 2
    MAX_PAGES_DEEP: int = 8

    # Anti-Detection / Delays (seconds)
    SCRAPE_MIN_DELAY_SEC: float = 2.0
    SCRAPE_MAX_DELAY_SEC: float = 5.5
    ACTION_TIMEOUT_MS: int = 30000

    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    SESSION_DIR: Path = STORAGE_DIR / "sessions"
    RESUME_DIR: Path = STORAGE_DIR / "resumes"
    SCREENSHOT_DIR: Path = STORAGE_DIR / "screenshots"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    def init_storage(self) -> None:
        """Ensure runtime storage directories exist."""
        self.SESSION_DIR.mkdir(parents=True, exist_ok=True)
        self.RESUME_DIR.mkdir(parents=True, exist_ok=True)
        self.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.init_storage()
