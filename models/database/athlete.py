"""Athlete model for storing Strava athlete profile information."""

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from models.database.base import Base, TimestampMixin


class Athlete(Base, TimestampMixin):
    """Strava athlete profile model."""

    __tablename__ = "athletes"

    # Primary key (Strava athlete ID)
    id = Column(Integer, primary_key=True, autoincrement=False)

    # Profile information
    username = Column(String(100), nullable=True)
    firstname = Column(String(100), nullable=True)
    lastname = Column(String(100), nullable=True)
    sex = Column(String(1), nullable=True)  # M, F, or None
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    profile_medium = Column(String(500), nullable=True)  # Profile picture URL
    profile = Column(String(500), nullable=True)  # Larger profile picture URL

    # Physical characteristics
    weight = Column(Float, nullable=True)  # kg

    # Performance thresholds
    ftp = Column(Integer, nullable=True)  # Functional Threshold Power (watts)
    max_heart_rate = Column(Integer, nullable=True)
    resting_heart_rate = Column(Integer, nullable=True)

    # Account information
    created_at_strava = Column(DateTime, nullable=True)  # When Strava account was created
    premium = Column(String(20), nullable=True)  # Subscription status

    # Relationships
    activities = relationship("Activity", back_populates="athlete", cascade="all, delete-orphan")
    training_zones = relationship("TrainingZone", back_populates="athlete", cascade="all, delete-orphan")
    training_loads = relationship("TrainingLoad", back_populates="athlete", cascade="all, delete-orphan")
    oauth_tokens = relationship("OAuthToken", back_populates="athlete", cascade="all, delete-orphan")
    sync_metadata = relationship("SyncMetadata", back_populates="athlete", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Athlete(id={self.id}, username='{self.username}')>"

    @property
    def fullname(self) -> str:
        """Get athlete's full name."""
        if self.firstname and self.lastname:
            return f"{self.firstname} {self.lastname}"
        return self.username or f"Athlete {self.id}"
