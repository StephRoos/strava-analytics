"""Migrate data from SQLite to PostgreSQL."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_data():
    """Migrate all data from SQLite to PostgreSQL."""

    # Connect to SQLite (source)
    sqlite_url = "sqlite:///./data/strava.db"
    sqlite_engine = create_engine(sqlite_url)
    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_session = SqliteSession()

    # Connect to PostgreSQL (destination)
    postgres_url = os.getenv("DATABASE_URL")
    if not postgres_url:
        print("ERROR: DATABASE_URL not found in environment variables")
        print("Please set it in your .env file")
        return

    postgres_engine = create_engine(postgres_url)
    PostgresSession = sessionmaker(bind=postgres_engine)
    postgres_session = PostgresSession()

    print("🔄 Starting migration from SQLite to PostgreSQL...")
    print(f"Source: {sqlite_url}")
    print(f"Destination: {postgres_url[:50]}...")
    print()

    # List of tables to migrate (in order due to foreign keys)
    tables = [
        'athletes',
        'oauth_tokens',
        'activities',
        'activity_streams',
        'training_loads',
        'training_zones',
        'sync_metadata'
    ]

    for table in tables:
        try:
            # Count rows in SQLite
            result = sqlite_session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()

            if count == 0:
                print(f"⊘ {table}: No data to migrate")
                continue

            print(f"📦 Migrating {table}: {count} rows...")

            # Get all data from SQLite
            rows = sqlite_session.execute(text(f"SELECT * FROM {table}"))
            columns = rows.keys()
            data = rows.fetchall()

            # Insert into PostgreSQL
            for row in data:
                # Build INSERT statement
                cols = ', '.join(columns)
                placeholders = ', '.join([f':{col}' for col in columns])
                insert_sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

                # Convert row to dict
                row_dict = dict(zip(columns, row))

                postgres_session.execute(text(insert_sql), row_dict)

            postgres_session.commit()
            print(f"✅ {table}: {count} rows migrated successfully")

        except Exception as e:
            print(f"❌ {table}: Error - {str(e)}")
            postgres_session.rollback()
            continue

    # Close connections
    sqlite_session.close()
    postgres_session.close()

    print()
    print("✨ Migration completed!")
    print()
    print("Next steps:")
    print("1. Verify data in Supabase dashboard")
    print("2. Update DATABASE_URL in Streamlit secrets")
    print("3. Restart your Streamlit app")

if __name__ == "__main__":
    migrate_data()
