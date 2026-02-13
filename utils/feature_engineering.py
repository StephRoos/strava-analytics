"""Feature engineering for machine learning models."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from models import Activity, TrainingLoad
from utils.logger import get_logger

logger = get_logger(__name__)


class FeatureEngineer:
    """Extract and engineer features from activities for ML models."""

    def __init__(self, session: Session, athlete_id: int):
        """
        Initialize feature engineer.

        Args:
            session: Database session
            athlete_id: Athlete ID to extract features for
        """
        self.session = session
        self.athlete_id = athlete_id
        self.activities = None
        self.training_loads = None

    def load_data(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
        """
        Load activities and training loads from database.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
        """
        query = self.session.query(Activity).filter_by(athlete_id=self.athlete_id)

        if start_date:
            query = query.filter(Activity.start_date >= start_date)
        if end_date:
            query = query.filter(Activity.start_date <= end_date)

        self.activities = query.order_by(Activity.start_date).all()

        # Load training loads
        load_query = self.session.query(TrainingLoad).filter_by(athlete_id=self.athlete_id)
        if start_date:
            load_query = load_query.filter(TrainingLoad.date >= start_date)
        if end_date:
            load_query = load_query.filter(TrainingLoad.date <= end_date)

        self.training_loads = load_query.order_by(TrainingLoad.date).all()

        logger.info(f"Loaded {len(self.activities)} activities and {len(self.training_loads)} training loads")

    def extract_activity_features(self) -> pd.DataFrame:
        """
        Extract features from activities.

        Returns:
            DataFrame with activity features
        """
        if not self.activities:
            logger.warning("No activities loaded. Call load_data() first.")
            return pd.DataFrame()

        features = []

        for activity in self.activities:
            feature_dict = {
                # Basic identifiers
                'activity_id': activity.id,
                'athlete_id': activity.athlete_id,
                'date': activity.start_date,

                # Activity metadata
                'type': activity.type or 'Unknown',
                'sport_type': activity.sport_type or activity.type or 'Unknown',
                'is_run': 1 if activity.type == 'Run' else 0,
                'is_ride': 1 if activity.type == 'Ride' else 0,
                'is_swim': 1 if activity.type == 'Swim' else 0,
                'is_trail': 1 if activity.sport_type == 'TrailRun' else 0,
                'trainer': 1 if activity.trainer else 0,

                # Distance and time metrics
                'distance_km': activity.distance_km if activity.distance else 0,
                'moving_time_hours': (activity.moving_time / 3600) if activity.moving_time else 0,
                'elapsed_time_hours': (activity.elapsed_time / 3600) if activity.elapsed_time else 0,

                # Elevation
                'elevation_gain_m': activity.total_elevation_gain or 0,
                'elevation_per_km': (activity.total_elevation_gain / activity.distance_km) if activity.total_elevation_gain and activity.distance and activity.distance_km > 0 else 0,

                # Speed and pace
                'average_speed_kmh': activity.average_speed * 3.6 if activity.average_speed else 0,
                'max_speed_kmh': activity.max_speed * 3.6 if activity.max_speed else 0,
                'average_pace_min_per_km': activity.average_pace_min_per_km if activity.type == 'Run' and activity.average_pace_min_per_km else None,

                # Heart rate
                'average_heartrate': activity.average_heartrate or None,
                'max_heartrate': activity.max_heartrate or None,
                'has_heartrate': 1 if activity.average_heartrate else 0,

                # Power (cycling)
                'average_watts': activity.average_watts or None,
                'max_watts': activity.max_watts or None,
                'weighted_average_watts': activity.weighted_average_watts or None,
                'has_power': 1 if activity.average_watts else 0,

                # Training metrics
                'training_stress_score': activity.training_stress_score or 0,
                'intensity_factor': activity.intensity_factor or None,
                'calories': activity.calories or None,

                # Temporal features
                'day_of_week': activity.start_date.weekday(),  # 0=Monday, 6=Sunday
                'is_weekend': 1 if activity.start_date.weekday() >= 5 else 0,
                'hour_of_day': activity.start_date.hour,
                'month': activity.start_date.month,
                'season': self._get_season(activity.start_date.month),
            }

            features.append(feature_dict)

        df = pd.DataFrame(features)

        # Add rolling statistics
        df = self._add_rolling_features(df)

        return df

    def extract_training_load_features(self) -> pd.DataFrame:
        """
        Extract features from training loads.

        Returns:
            DataFrame with training load features
        """
        if not self.training_loads:
            logger.warning("No training loads loaded. Call load_data() first.")
            return pd.DataFrame()

        features = []

        for load in self.training_loads:
            feature_dict = {
                'date': load.date,
                'athlete_id': load.athlete_id,
                'daily_tss': load.daily_tss or 0,
                'ctl': load.ctl or 0,
                'atl': load.atl or 0,
                'tsb': load.tsb or 0,
                'ramp_rate': load.ctl_ramp_rate or 0,
                'fitness_level': load.fitness_level,
                'form_status': load.form_status,
            }
            features.append(feature_dict)

        return pd.DataFrame(features)

    def merge_features(self, activity_df: pd.DataFrame, training_load_df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge activity and training load features.

        Args:
            activity_df: Activity features DataFrame
            training_load_df: Training load features DataFrame

        Returns:
            Merged DataFrame
        """
        if activity_df.empty or training_load_df.empty:
            return activity_df if not activity_df.empty else training_load_df

        # Convert dates to date only for merging
        activity_df['merge_date'] = pd.to_datetime(activity_df['date']).dt.date
        training_load_df['merge_date'] = pd.to_datetime(training_load_df['date']).dt.date

        # Merge on date
        merged = activity_df.merge(
            training_load_df,
            on=['merge_date', 'athlete_id'],
            how='left',
            suffixes=('', '_tl')
        )

        # Drop duplicate date column
        merged = merged.drop(columns=['date_tl', 'merge_date'], errors='ignore')

        return merged

    def _add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add rolling statistics (7, 30, 90 days).

        Args:
            df: Activity features DataFrame

        Returns:
            DataFrame with rolling features added
        """
        # Sort by date
        df = df.sort_values('date').copy()

        # Convert date to datetime for rolling
        df['date_dt'] = pd.to_datetime(df['date'])
        df = df.set_index('date_dt')

        # Calculate rolling statistics
        for window in [7, 30, 90]:
            window_str = f'{window}D'

            # Distance
            df[f'distance_km_rolling_{window}d'] = df['distance_km'].rolling(window_str, min_periods=1).sum()
            df[f'distance_km_mean_{window}d'] = df['distance_km'].rolling(window_str, min_periods=1).mean()

            # Time
            df[f'moving_time_rolling_{window}d'] = df['moving_time_hours'].rolling(window_str, min_periods=1).sum()

            # Elevation
            df[f'elevation_rolling_{window}d'] = df['elevation_gain_m'].rolling(window_str, min_periods=1).sum()

            # TSS
            df[f'tss_rolling_{window}d'] = df['training_stress_score'].rolling(window_str, min_periods=1).sum()

            # Activity count
            df[f'activity_count_{window}d'] = df['activity_id'].rolling(window_str, min_periods=1).count()

        # Reset index
        df = df.reset_index(drop=True)

        return df

    def _get_season(self, month: int) -> str:
        """
        Get season from month (Northern Hemisphere).

        Args:
            month: Month number (1-12)

        Returns:
            Season name
        """
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'fall'

    def prepare_dataset(self,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       include_training_loads: bool = True) -> pd.DataFrame:
        """
        Prepare complete dataset with all features.

        Args:
            start_date: Optional start date
            end_date: Optional end date
            include_training_loads: Whether to include training load features

        Returns:
            Complete feature DataFrame
        """
        # Load data
        self.load_data(start_date, end_date)

        # Extract features
        activity_features = self.extract_activity_features()

        if include_training_loads and self.training_loads:
            training_load_features = self.extract_training_load_features()
            features = self.merge_features(activity_features, training_load_features)
        else:
            features = activity_features

        # Fill missing values
        features = self._fill_missing_values(features)

        logger.info(f"Prepared dataset with {len(features)} samples and {len(features.columns)} features")

        return features

    def _fill_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fill missing values with appropriate defaults.

        Args:
            df: DataFrame with features

        Returns:
            DataFrame with missing values filled
        """
        # Numeric columns: fill with 0
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)

        # Categorical columns: fill with 'Unknown'
        categorical_cols = df.select_dtypes(include=['object']).columns
        df[categorical_cols] = df[categorical_cols].fillna('Unknown')

        return df

    def get_feature_importance_groups(self) -> Dict[str, List[str]]:
        """
        Get logical groups of features for analysis.

        Returns:
            Dictionary mapping group names to feature lists
        """
        return {
            'basic': ['distance_km', 'moving_time_hours', 'elevation_gain_m'],
            'speed': ['average_speed_kmh', 'max_speed_kmh', 'average_pace_min_per_km'],
            'heartrate': ['average_heartrate', 'max_heartrate'],
            'power': ['average_watts', 'weighted_average_watts'],
            'training_load': ['training_stress_score', 'ctl', 'atl', 'tsb'],
            'temporal': ['day_of_week', 'hour_of_day', 'month', 'season'],
            'rolling_7d': [col for col in [] if '7d' in col],
            'rolling_30d': [col for col in [] if '30d' in col],
            'rolling_90d': [col for col in [] if '90d' in col],
        }
