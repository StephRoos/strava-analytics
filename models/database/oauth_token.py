"""OAuth token model for storing Strava authentication tokens."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from models.database.base import Base, TimestampMixin


class OAuthToken(Base, TimestampMixin):
    """Strava OAuth2 tokens for API authentication."""

    __tablename__ = "oauth_tokens"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to athlete
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)

    # OAuth tokens
    access_token = Column(String(255), nullable=False)
    refresh_token = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)  # Token expiration timestamp

    # Token metadata
    token_type = Column(String(20), default="Bearer")
    scope = Column(String(255), nullable=True)  # Granted permissions

    # Relationship
    athlete = relationship("Athlete", back_populates="oauth_tokens")

    def __repr__(self) -> str:
        return f"<OAuthToken(athlete_id={self.athlete_id}, expires_at={self.expires_at})>"

    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        return datetime.utcnow() >= self.expires_at

    def needs_refresh(self, buffer_seconds: int = 300) -> bool:
        """
        Check if the token needs to be refreshed.

        Args:
            buffer_seconds: Refresh this many seconds before actual expiry

        Returns:
            True if token should be refreshed
        """
        from datetime import timedelta
        expiry_with_buffer = self.expires_at - timedelta(seconds=buffer_seconds)
        return datetime.utcnow() >= expiry_with_buffer
