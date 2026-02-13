"""Database initialization script."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings, get_database_engine
from models.database.base import Base
from models import (
    Athlete,
    Activity,
    ActivityStream,
    TrainingLoad,
    TrainingZone,
    OAuthToken,
    SyncMetadata,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def init_database(drop_existing: bool = False):
    """
    Initialize the database schema.

    Args:
        drop_existing: If True, drop all existing tables before creating

    This will create all tables defined in the SQLAlchemy models.
    """
    logger.info("Initializing database...")
    logger.info(f"Database URL: {settings.DATABASE_URL}")

    try:
        engine = get_database_engine()

        if drop_existing:
            logger.warning("Dropping all existing tables...")
            Base.metadata.drop_all(engine)
            logger.info("Existing tables dropped")

        # Create all tables
        logger.info("Creating database schema...")
        Base.metadata.create_all(engine)

        # List created tables
        table_names = Base.metadata.tables.keys()
        logger.info(f"Created {len(table_names)} tables:")
        for table_name in sorted(table_names):
            logger.info(f"  - {table_name}")

        logger.info("Database initialization completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        return False


def check_database():
    """Check database connection and schema."""
    logger.info("Checking database connection...")

    try:
        engine = get_database_engine()

        # Test connection
        with engine.connect() as conn:
            logger.info("Database connection successful")

        # Check tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        logger.info(f"Found {len(existing_tables)} existing tables:")
        for table_name in sorted(existing_tables):
            logger.info(f"  - {table_name}")

        # Check if all required tables exist
        required_tables = set(Base.metadata.tables.keys())
        missing_tables = required_tables - set(existing_tables)

        if missing_tables:
            logger.warning(f"Missing tables: {missing_tables}")
            logger.warning("Run 'python scripts/init_db.py' to create missing tables")
            return False
        else:
            logger.info("All required tables exist")
            return True

    except Exception as e:
        logger.error(f"Database check failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize Strava Analytics database")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables before creating (WARNING: deletes all data)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check database connection and schema without making changes"
    )

    args = parser.parse_args()

    if args.check:
        success = check_database()
    else:
        if args.drop:
            confirm = input(
                "WARNING: This will delete all existing data. Are you sure? (yes/no): "
            )
            if confirm.lower() != "yes":
                print("Aborted.")
                sys.exit(0)

        success = init_database(drop_existing=args.drop)

    sys.exit(0 if success else 1)
