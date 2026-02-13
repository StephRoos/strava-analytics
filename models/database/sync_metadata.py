"""Sync metadata model for tracking synchronization state."""

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from models.database.base import Base, TimestampMixin


class SyncMetadata(Base, TimestampMixin):
    """
    Metadata about data synchronization from Strava.

    Tracks sync history, status, and progress to enable incremental
    syncs and error recovery.
    """

    __tablename__ = "sync_metadata"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to athlete
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)

    # Sync information
    sync_type = Column(String(20), nullable=False)  # full, incremental, streams
    sync_status = Column(String(20), nullable=False)  # success, partial, failed, in_progress
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Sync results
    activities_synced = Column(Integer, default=0)
    activities_updated = Column(Integer, default=0)
    activities_skipped = Column(Integer, default=0)
    streams_synced = Column(Integer, default=0)

    # Last synced activity info (for incremental sync)
    last_activity_id = Column(BigInteger, nullable=True)
    last_activity_date = Column(DateTime, nullable=True)

    # Error information
    error_message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)

    # Relationship
    athlete = relationship("Athlete", back_populates="sync_metadata")

    def __repr__(self) -> str:
        return f"<SyncMetadata(athlete_id={self.athlete_id}, type='{self.sync_type}', status='{self.sync_status}', synced={self.activities_synced})>"

    @property
    def duration_seconds(self) -> int:
        """Get sync duration in seconds."""
        if not self.completed_at:
            return 0
        delta = self.completed_at - self.started_at
        return int(delta.total_seconds())

    @property
    def is_success(self) -> bool:
        """Check if sync completed successfully."""
        return self.sync_status == "success"

    @property
    def is_in_progress(self) -> bool:
        """Check if sync is currently in progress."""
        return self.sync_status == "in_progress"

    @property
    def total_processed(self) -> int:
        """Get total number of activities processed."""
        return self.activities_synced + self.activities_updated + self.activities_skipped
