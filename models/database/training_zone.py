"""Training zone model for storing heart rate, power, and pace zones."""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from models.database.base import Base, TimestampMixin


class TrainingZone(Base, TimestampMixin):
    """
    Training zones for different metrics (heart rate, power, pace).

    Zones are used to calculate training intensity distribution and
    time-in-zone analytics.
    """

    __tablename__ = "training_zones"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to athlete
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)

    # Zone type (heart_rate, power, pace)
    zone_type = Column(String(20), nullable=False)

    # Zone number (typically 1-7)
    zone_number = Column(Integer, nullable=False)

    # Zone boundaries
    min_value = Column(Float, nullable=False)
    max_value = Column(Float, nullable=False)

    # Zone description (e.g., "Recovery", "Endurance", "Tempo", "Threshold", "VO2Max")
    name = Column(String(50), nullable=True)
    description = Column(String(200), nullable=True)

    # Relationship
    athlete = relationship("Athlete", back_populates="training_zones")

    # Unique constraint: one zone per athlete, type, and number
    __table_args__ = (
        UniqueConstraint("athlete_id", "zone_type", "zone_number", name="uix_athlete_zone"),
    )

    def __repr__(self) -> str:
        return f"<TrainingZone(athlete_id={self.athlete_id}, type='{self.zone_type}', zone={self.zone_number}, range=[{self.min_value}, {self.max_value}])>"

    def contains(self, value: float) -> bool:
        """Check if a value falls within this zone."""
        return self.min_value <= value < self.max_value

    @classmethod
    def create_default_hr_zones(cls, athlete_id: int, max_hr: int) -> list:
        """
        Create default heart rate zones based on max HR.

        Uses standard 5-zone model:
        - Zone 1: 50-60% (Recovery)
        - Zone 2: 60-70% (Endurance)
        - Zone 3: 70-80% (Tempo)
        - Zone 4: 80-90% (Threshold)
        - Zone 5: 90-100% (VO2Max)
        """
        zones = [
            {"zone": 1, "name": "Recovery", "min_pct": 0.50, "max_pct": 0.60},
            {"zone": 2, "name": "Endurance", "min_pct": 0.60, "max_pct": 0.70},
            {"zone": 3, "name": "Tempo", "min_pct": 0.70, "max_pct": 0.80},
            {"zone": 4, "name": "Threshold", "min_pct": 0.80, "max_pct": 0.90},
            {"zone": 5, "name": "VO2Max", "min_pct": 0.90, "max_pct": 1.00},
        ]

        return [
            cls(
                athlete_id=athlete_id,
                zone_type="heart_rate",
                zone_number=z["zone"],
                name=z["name"],
                min_value=int(max_hr * z["min_pct"]),
                max_value=int(max_hr * z["max_pct"]),
            )
            for z in zones
        ]

    @classmethod
    def create_default_power_zones(cls, athlete_id: int, ftp: int) -> list:
        """
        Create default power zones based on FTP.

        Uses standard 7-zone model (Coggan zones):
        - Zone 1: <55% (Active Recovery)
        - Zone 2: 55-75% (Endurance)
        - Zone 3: 75-90% (Tempo)
        - Zone 4: 90-105% (Lactate Threshold)
        - Zone 5: 105-120% (VO2Max)
        - Zone 6: 120-150% (Anaerobic Capacity)
        - Zone 7: >150% (Neuromuscular Power)
        """
        zones = [
            {"zone": 1, "name": "Active Recovery", "min_pct": 0.00, "max_pct": 0.55},
            {"zone": 2, "name": "Endurance", "min_pct": 0.55, "max_pct": 0.75},
            {"zone": 3, "name": "Tempo", "min_pct": 0.75, "max_pct": 0.90},
            {"zone": 4, "name": "Lactate Threshold", "min_pct": 0.90, "max_pct": 1.05},
            {"zone": 5, "name": "VO2Max", "min_pct": 1.05, "max_pct": 1.20},
            {"zone": 6, "name": "Anaerobic", "min_pct": 1.20, "max_pct": 1.50},
            {"zone": 7, "name": "Neuromuscular", "min_pct": 1.50, "max_pct": 3.00},
        ]

        return [
            cls(
                athlete_id=athlete_id,
                zone_type="power",
                zone_number=z["zone"],
                name=z["name"],
                min_value=int(ftp * z["min_pct"]),
                max_value=int(ftp * z["max_pct"]),
            )
            for z in zones
        ]
