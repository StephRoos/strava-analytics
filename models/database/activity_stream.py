"""Activity stream model for storing detailed time-series data."""

from sqlalchemy import Column, Integer, BigInteger, String, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from models.database.base import Base


class ActivityStream(Base):
    """
    Detailed time-series data for activities.

    Stores streams like heart rate, power, cadence, altitude, etc.
    Data is stored as JSON arrays to handle variable-length series.
    """

    __tablename__ = "activity_streams"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to activity
    activity_id = Column(BigInteger, ForeignKey("activities.id"), nullable=False)

    # Stream type (time, distance, latlng, altitude, heartrate, watts, cadence, etc.)
    stream_type = Column(String(50), nullable=False)

    # Stream data (JSON array of values)
    # Examples:
    #   - time: [0, 1, 2, 3, ...]
    #   - heartrate: [120, 125, 128, ...]
    #   - latlng: [[lat1, lng1], [lat2, lng2], ...]
    data = Column(Text, nullable=False)

    # Metadata
    original_size = Column(Integer, nullable=True)  # Number of data points
    resolution = Column(String(20), nullable=True)  # low, medium, high

    # Relationship
    activity = relationship("Activity", back_populates="streams")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_activity_stream_type", "activity_id", "stream_type"),
        UniqueConstraint("activity_id", "stream_type", name="uix_activity_stream"),
    )

    def __repr__(self) -> str:
        return f"<ActivityStream(activity_id={self.activity_id}, type='{self.stream_type}', size={self.original_size})>"
