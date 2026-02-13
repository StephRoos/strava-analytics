"""Training load model for tracking fitness metrics over time."""

from sqlalchemy import Column, Integer, Date, Float, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from models.database.base import Base


class TrainingLoad(Base):
    """
    Daily training load and fitness metrics.

    Tracks Training Stress Score (TSS) and derived metrics:
    - CTL (Chronic Training Load): 42-day exponential moving average
    - ATL (Acute Training Load): 7-day exponential moving average
    - TSB (Training Stress Balance): CTL - ATL (form/freshness)
    """

    __tablename__ = "training_loads"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to athlete
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)

    # Date
    date = Column(Date, nullable=False)

    # Daily metrics
    daily_tss = Column(Float, default=0.0, nullable=False)  # Total TSS for the day
    activity_count = Column(Integer, default=0)  # Number of activities

    # Fitness metrics (exponential moving averages)
    ctl = Column(Float, nullable=True)  # Chronic Training Load (fitness)
    atl = Column(Float, nullable=True)  # Acute Training Load (fatigue)
    tsb = Column(Float, nullable=True)  # Training Stress Balance (form)

    # Ramp rate (rate of CTL change)
    ctl_ramp_rate = Column(Float, nullable=True)  # CTL change per week

    # Relationship
    athlete = relationship("Athlete", back_populates="training_loads")

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint("athlete_id", "date", name="uix_athlete_date"),
        Index("idx_athlete_date_load", "athlete_id", "date"),
    )

    def __repr__(self) -> str:
        return f"<TrainingLoad(athlete_id={self.athlete_id}, date={self.date}, CTL={self.ctl:.1f}, TSB={self.tsb:.1f})>"

    @property
    def fitness_level(self) -> str:
        """Get fitness level description based on CTL."""
        if not self.ctl:
            return "Unknown"
        if self.ctl < 30:
            return "Detraining"
        elif self.ctl < 50:
            return "Maintenance"
        elif self.ctl < 70:
            return "Building"
        elif self.ctl < 90:
            return "Fit"
        else:
            return "Peak Fitness"

    @property
    def form_status(self) -> str:
        """Get form/freshness status based on TSB."""
        if not self.tsb:
            return "Unknown"
        if self.tsb < -30:
            return "Very Fatigued"
        elif self.tsb < -20:
            return "Fatigued"
        elif self.tsb < -10:
            return "Optimal Training"
        elif self.tsb < 5:
            return "Fresh"
        elif self.tsb < 15:
            return "Very Fresh"
        else:
            return "Detraining Risk"
