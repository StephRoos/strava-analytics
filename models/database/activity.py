"""Activity model for storing Strava activity data."""

from sqlalchemy import Column, BigInteger, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from models.database.base import Base, TimestampMixin


class Activity(Base, TimestampMixin):
    """Strava activity model."""

    __tablename__ = "activities"

    # Primary key (Strava activity ID)
    id = Column(BigInteger, primary_key=True, autoincrement=False)

    # Foreign key to athlete
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)

    # Basic activity information
    name = Column(String(255), nullable=True)
    type = Column(String(50), nullable=True)  # Run, Ride, Swim, etc.
    sport_type = Column(String(50), nullable=True)  # More specific type (e.g., TrailRun, VirtualRide)
    distance = Column(Float, nullable=True)  # meters
    moving_time = Column(Integer, nullable=True)  # seconds
    elapsed_time = Column(Integer, nullable=True)  # seconds
    total_elevation_gain = Column(Float, nullable=True)  # meters

    # Timing information
    start_date = Column(DateTime, nullable=False, index=True)
    start_date_local = Column(DateTime, nullable=True)
    timezone = Column(String(100), nullable=True)

    # Speed metrics
    average_speed = Column(Float, nullable=True)  # m/s
    max_speed = Column(Float, nullable=True)  # m/s

    # Heart rate metrics
    average_heartrate = Column(Float, nullable=True)
    max_heartrate = Column(Integer, nullable=True)
    has_heartrate = Column(Boolean, default=False)

    # Power metrics (cycling)
    average_watts = Column(Float, nullable=True)
    max_watts = Column(Integer, nullable=True)
    weighted_average_watts = Column(Integer, nullable=True)  # Normalized Power
    kilojoules = Column(Float, nullable=True)

    # Cadence
    average_cadence = Column(Float, nullable=True)

    # Calories
    calories = Column(Float, nullable=True)

    # Training load metrics
    suffer_score = Column(Integer, nullable=True)  # Strava's relative effort
    training_stress_score = Column(Float, nullable=True)  # Calculated TSS
    intensity_factor = Column(Float, nullable=True)  # IF = NP/FTP

    # Map data
    start_latlng = Column(String(100), nullable=True)  # JSON array [lat, lng]
    end_latlng = Column(String(100), nullable=True)
    map_summary_polyline = Column(Text, nullable=True)
    map_detailed_polyline = Column(Text, nullable=True)

    # Achievement counts
    achievement_count = Column(Integer, nullable=True)
    kudos_count = Column(Integer, nullable=True)
    comment_count = Column(Integer, nullable=True)
    pr_count = Column(Integer, nullable=True)  # Personal records

    # Flags
    trainer = Column(Boolean, default=False)  # Indoor trainer
    commute = Column(Boolean, default=False)
    manual = Column(Boolean, default=False)  # Manually entered
    private = Column(Boolean, default=False)
    flagged = Column(Boolean, default=False)

    # Gear
    gear_id = Column(String(50), nullable=True)

    # Description
    description = Column(Text, nullable=True)

    # Relationships
    athlete = relationship("Athlete", back_populates="activities")
    streams = relationship("ActivityStream", back_populates="activity", cascade="all, delete-orphan")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_athlete_date", "athlete_id", "start_date"),
        Index("idx_type_date", "type", "start_date"),
        Index("idx_athlete_type", "athlete_id", "type"),
    )

    def __repr__(self) -> str:
        return f"<Activity(id={self.id}, name='{self.name}', type='{self.type}', date='{self.start_date}')>"

    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string (HH:MM:SS)."""
        if not self.moving_time:
            return "00:00:00"

        hours = self.moving_time // 3600
        minutes = (self.moving_time % 3600) // 60
        seconds = self.moving_time % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @property
    def distance_km(self) -> float:
        """Get distance in kilometers."""
        if not self.distance:
            return 0.0
        return self.distance / 1000.0

    @property
    def distance_miles(self) -> float:
        """Get distance in miles."""
        if not self.distance:
            return 0.0
        return self.distance / 1609.34

    @property
    def average_pace_min_per_km(self) -> float:
        """Get average pace in minutes per kilometer (for running)."""
        if not self.distance or not self.moving_time or self.distance == 0:
            return 0.0
        return (self.moving_time / 60.0) / (self.distance / 1000.0)

    @property
    def elevation_gain_m(self) -> float:
        """Get elevation gain in meters."""
        return self.total_elevation_gain or 0.0
