"""Centralized configuration management using environment variables."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Load environment variables from .env file
load_dotenv()

# Project root directory
ROOT_DIR = Path(__file__).parent.parent


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        """Initialize settings and validate required environment variables."""
        # Strava API Configuration
        self.STRAVA_CLIENT_ID: str = self._get_required_env("STRAVA_CLIENT_ID")
        self.STRAVA_CLIENT_SECRET: str = self._get_required_env("STRAVA_CLIENT_SECRET")
        self.STRAVA_REDIRECT_URI: str = os.getenv(
            "STRAVA_REDIRECT_URI",
            "http://localhost:8501"
        )

        # Database Configuration
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            f"sqlite:///{ROOT_DIR}/data/strava.db"
        )

        # Ensure data directory exists for SQLite
        if self.DATABASE_URL.startswith("sqlite"):
            data_dir = ROOT_DIR / "data"
            data_dir.mkdir(exist_ok=True)

        # App Settings
        self.APP_NAME: str = os.getenv("APP_NAME", "Strava Analytics")
        self.DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

        # Sync Settings
        self.AUTO_SYNC_ENABLED: bool = os.getenv("AUTO_SYNC_ENABLED", "True").lower() == "true"
        self.SYNC_STREAM_DATA_DAYS: int = int(os.getenv("SYNC_STREAM_DATA_DAYS", "90"))
        self.SYNC_BATCH_SIZE: int = int(os.getenv("SYNC_BATCH_SIZE", "50"))

        # ML Settings
        self.MIN_ACTIVITIES_FOR_ML: int = int(os.getenv("MIN_ACTIVITIES_FOR_ML", "50"))
        self.MODEL_RETRAIN_DAYS: int = int(os.getenv("MODEL_RETRAIN_DAYS", "7"))
        self.MODEL_DIR: Path = ROOT_DIR / "models" / "trained"
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)

        # Strava API Rate Limits
        self.STRAVA_RATE_LIMIT_15MIN: int = 100
        self.STRAVA_RATE_LIMIT_DAILY: int = 1000

        # Cache Settings
        self.CACHE_DIR: Path = ROOT_DIR / "data" / "cache"
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.CACHE_EXPIRY_HOURS: int = int(os.getenv("CACHE_EXPIRY_HOURS", "24"))

    @staticmethod
    def _get_required_env(key: str) -> str:
        """Get required environment variable or raise error."""
        value = os.getenv(key)
        if not value:
            raise ValueError(
                f"Required environment variable '{key}' is not set. "
                f"Please check your .env file."
            )
        return value

    def get_database_url(self) -> str:
        """Get database URL."""
        return self.DATABASE_URL

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.DEBUG


# Global settings instance
settings = Settings()


# Database engine and session management
_engine: Optional[object] = None
_SessionLocal: Optional[sessionmaker] = None


def get_database_engine():
    """Get or create database engine singleton."""
    global _engine
    if _engine is None:
        connect_args = {}
        if settings.DATABASE_URL.startswith("sqlite"):
            # SQLite specific configuration
            connect_args = {"check_same_thread": False}

        _engine = create_engine(
            settings.DATABASE_URL,
            connect_args=connect_args,
            echo=settings.DEBUG,  # Log SQL queries in debug mode
            pool_pre_ping=True,  # Verify connections before using
        )
    return _engine


def get_session_maker() -> sessionmaker:
    """Get or create session maker."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_database_engine()
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
    return _SessionLocal


def get_database_session() -> Session:
    """Get a new database session."""
    SessionLocal = get_session_maker()
    return SessionLocal()


def validate_settings():
    """Validate all settings are correctly configured."""
    errors = []

    # Check Strava credentials
    if not settings.STRAVA_CLIENT_ID or settings.STRAVA_CLIENT_ID == "your_client_id":
        errors.append("STRAVA_CLIENT_ID is not configured")

    if not settings.STRAVA_CLIENT_SECRET or settings.STRAVA_CLIENT_SECRET == "your_client_secret":
        errors.append("STRAVA_CLIENT_SECRET is not configured")

    # Check database URL
    if not settings.DATABASE_URL:
        errors.append("DATABASE_URL is not configured")

    if errors:
        error_msg = "\n".join([f"  - {err}" for err in errors])
        raise ValueError(f"Configuration errors:\n{error_msg}\n\nPlease update your .env file.")

    return True
