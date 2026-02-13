"""Synchronization manager for Strava data."""

import json
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any, Callable
from sqlalchemy.orm import Session
from config.settings import settings, get_database_session
from models import (
    Athlete, Activity, ActivityStream, TrainingLoad,
    TrainingZone, SyncMetadata
)
from utils.strava_client import StravaClient
from utils.training_metrics import TrainingMetrics, calculate_activity_tss
from utils.logger import get_logger

logger = get_logger(__name__)


class SyncManager:
    """
    Manages synchronization of Strava data to local database.

    Handles:
    - Full sync (initial data load)
    - Incremental sync (new activities only)
    - Stream sync (detailed time-series data)
    - Training load calculations
    """

    def __init__(self, athlete_id: int):
        """
        Initialize sync manager for an athlete.

        Args:
            athlete_id: Athlete ID to sync data for
        """
        self.athlete_id = athlete_id
        self.client = StravaClient(athlete_id=athlete_id)
        self.session: Optional[Session] = None
        self.metrics = TrainingMetrics()

    def full_sync(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Perform full synchronization of all Strava data.

        Args:
            progress_callback: Optional callback function(status, current, total)

        Returns:
            Sync results dictionary
        """
        logger.info(f"Starting full sync for athlete {self.athlete_id}")

        self.session = get_database_session()
        sync_record = self._create_sync_record("full", "in_progress")

        try:
            # 1. Sync athlete profile
            logger.info("Syncing athlete profile")
            if progress_callback:
                progress_callback("Syncing athlete profile", 0, 100)

            athlete = self._sync_athlete_profile()

            # 2. Sync all activities
            logger.info("Syncing activities")
            if progress_callback:
                progress_callback("Syncing activities", 10, 100)

            activities_synced = self._sync_all_activities(progress_callback)
            sync_record.activities_synced = activities_synced

            # 3. Calculate training loads
            logger.info("Calculating training loads")
            if progress_callback:
                progress_callback("Calculating training loads", 80, 100)

            self._calculate_training_loads()

            # 4. Sync recent activity streams
            logger.info("Syncing activity streams")
            if progress_callback:
                progress_callback("Syncing activity streams", 90, 100)

            streams_synced = self._sync_recent_streams()
            sync_record.streams_synced = streams_synced

            # Complete sync
            sync_record.sync_status = "success"
            sync_record.completed_at = datetime.utcnow()
            self.session.commit()

            logger.info(f"Full sync completed: {activities_synced} activities, {streams_synced} streams")

            if progress_callback:
                progress_callback("Sync completed", 100, 100)

            return {
                "status": "success",
                "activities_synced": activities_synced,
                "streams_synced": streams_synced,
                "duration_seconds": sync_record.duration_seconds
            }

        except Exception as e:
            logger.error(f"Full sync failed: {e}", exc_info=True)
            sync_record.sync_status = "failed"
            sync_record.error_message = str(e)
            sync_record.completed_at = datetime.utcnow()
            self.session.commit()

            return {
                "status": "failed",
                "error": str(e)
            }

        finally:
            if self.session:
                self.session.close()

    def incremental_sync(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Perform incremental sync (only new activities since last sync).

        Args:
            progress_callback: Optional callback function(status, current, total)

        Returns:
            Sync results dictionary
        """
        logger.info(f"Starting incremental sync for athlete {self.athlete_id}")

        self.session = get_database_session()
        sync_record = self._create_sync_record("incremental", "in_progress")

        try:
            # Get last sync date
            last_sync = self._get_last_successful_sync()
            after_date = last_sync.last_activity_date if last_sync else None

            logger.info(f"Syncing activities after {after_date}")

            if progress_callback:
                progress_callback("Fetching new activities", 0, 100)

            # Sync new activities
            activities_synced = self._sync_activities_after(after_date, progress_callback)
            sync_record.activities_synced = activities_synced

            if activities_synced > 0:
                # Recalculate training loads for affected dates
                if progress_callback:
                    progress_callback("Updating training loads", 80, 100)

                self._calculate_training_loads(after_date)

                # Sync streams for new activities
                if progress_callback:
                    progress_callback("Syncing activity streams", 90, 100)

                streams_synced = self._sync_recent_streams()
                sync_record.streams_synced = streams_synced
            else:
                streams_synced = 0
                logger.info("No new activities to sync")

            # Complete sync
            sync_record.sync_status = "success"
            sync_record.completed_at = datetime.utcnow()
            self.session.commit()

            logger.info(f"Incremental sync completed: {activities_synced} new activities")

            if progress_callback:
                progress_callback("Sync completed", 100, 100)

            return {
                "status": "success",
                "activities_synced": activities_synced,
                "streams_synced": streams_synced,
                "duration_seconds": sync_record.duration_seconds
            }

        except Exception as e:
            logger.error(f"Incremental sync failed: {e}", exc_info=True)
            sync_record.sync_status = "failed"
            sync_record.error_message = str(e)
            sync_record.completed_at = datetime.utcnow()
            self.session.commit()

            return {
                "status": "failed",
                "error": str(e)
            }

        finally:
            if self.session:
                self.session.close()

    def _sync_athlete_profile(self) -> Athlete:
        """Sync athlete profile from Strava."""
        strava_athlete = self.client.get_athlete()

        # Check if athlete exists
        athlete = self.session.query(Athlete).filter_by(id=strava_athlete.id).first()

        if not athlete:
            athlete = Athlete(id=strava_athlete.id)
            self.session.add(athlete)

        # Update athlete data
        athlete.username = strava_athlete.username
        athlete.firstname = strava_athlete.firstname
        athlete.lastname = strava_athlete.lastname
        athlete.sex = strava_athlete.sex
        athlete.city = strava_athlete.city
        athlete.state = strava_athlete.state
        athlete.country = strava_athlete.country
        athlete.profile_medium = strava_athlete.profile_medium
        athlete.profile = strava_athlete.profile
        athlete.weight = getattr(strava_athlete, 'weight', None)
        athlete.premium = str(getattr(strava_athlete, 'premium', False))

        if hasattr(strava_athlete, 'created_at'):
            athlete.created_at_strava = strava_athlete.created_at

        self.session.commit()
        logger.info(f"Synced athlete profile: {athlete.fullname}")

        return athlete

    def _sync_all_activities(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> int:
        """Sync all activities from Strava."""
        activities = list(self.client.get_activities())
        total = len(activities)

        logger.info(f"Fetched {total} activities from Strava")

        synced = 0
        for i, strava_activity in enumerate(activities):
            if progress_callback and i % 10 == 0:
                progress_callback(f"Syncing activities", 10 + int(70 * i / total), 100)

            self._sync_activity(strava_activity)
            synced += 1

        self.session.commit()
        return synced

    def _sync_activities_after(
        self,
        after_date: Optional[datetime],
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> int:
        """Sync activities after a specific date."""
        activities = list(self.client.get_activities(after=after_date))
        total = len(activities)

        logger.info(f"Fetched {total} new activities from Strava")

        synced = 0
        for i, strava_activity in enumerate(activities):
            if progress_callback and total > 0:
                progress_callback(f"Syncing activities", int(70 * i / total), 100)

            self._sync_activity(strava_activity)
            synced += 1

        self.session.commit()
        return synced

    def _sync_activity(self, strava_activity) -> Activity:
        """Sync a single activity to database."""
        # Check if activity exists
        activity = self.session.query(Activity).filter_by(id=strava_activity.id).first()

        if not activity:
            activity = Activity(id=strava_activity.id)
            self.session.add(activity)

        # Update activity data
        activity.athlete_id = self.athlete_id
        activity.name = strava_activity.name

        # Handle RelaxedActivityType object - extract string value
        if hasattr(strava_activity.type, 'root'):
            activity.type = str(strava_activity.type.root)
        elif hasattr(strava_activity.type, 'value'):
            activity.type = str(strava_activity.type.value)
        else:
            activity.type = str(strava_activity.type)

        # Handle RelaxedSportType object
        sport_type = getattr(strava_activity, 'sport_type', None)
        if sport_type:
            if hasattr(sport_type, 'root'):
                activity.sport_type = str(sport_type.root)
            elif hasattr(sport_type, 'value'):
                activity.sport_type = str(sport_type.value)
            else:
                activity.sport_type = str(sport_type)
        else:
            activity.sport_type = None
        activity.distance = float(strava_activity.distance) if strava_activity.distance else None

        # Handle timedelta objects - convert to total seconds
        if strava_activity.moving_time:
            if hasattr(strava_activity.moving_time, 'total_seconds'):
                activity.moving_time = int(strava_activity.moving_time.total_seconds())
            elif hasattr(strava_activity.moving_time, 'seconds'):
                activity.moving_time = int(strava_activity.moving_time.seconds)
            else:
                activity.moving_time = int(strava_activity.moving_time)
        else:
            activity.moving_time = None

        if strava_activity.elapsed_time:
            if hasattr(strava_activity.elapsed_time, 'total_seconds'):
                activity.elapsed_time = int(strava_activity.elapsed_time.total_seconds())
            elif hasattr(strava_activity.elapsed_time, 'seconds'):
                activity.elapsed_time = int(strava_activity.elapsed_time.seconds)
            else:
                activity.elapsed_time = int(strava_activity.elapsed_time)
        else:
            activity.elapsed_time = None

        activity.total_elevation_gain = float(strava_activity.total_elevation_gain) if strava_activity.total_elevation_gain else None
        activity.start_date = strava_activity.start_date
        activity.start_date_local = strava_activity.start_date_local
        activity.timezone = str(strava_activity.timezone) if strava_activity.timezone else None

        # Speed metrics (use getattr for safety)
        average_speed = getattr(strava_activity, 'average_speed', None)
        activity.average_speed = float(average_speed) if average_speed else None

        max_speed = getattr(strava_activity, 'max_speed', None)
        activity.max_speed = float(max_speed) if max_speed else None

        # Heart rate
        average_heartrate = getattr(strava_activity, 'average_heartrate', None)
        activity.average_heartrate = float(average_heartrate) if average_heartrate else None

        max_heartrate = getattr(strava_activity, 'max_heartrate', None)
        activity.max_heartrate = int(max_heartrate) if max_heartrate else None

        activity.has_heartrate = getattr(strava_activity, 'has_heartrate', False)

        # Power
        average_watts = getattr(strava_activity, 'average_watts', None)
        activity.average_watts = float(average_watts) if average_watts else None

        max_watts = getattr(strava_activity, 'max_watts', None)
        activity.max_watts = int(max_watts) if max_watts else None

        weighted_average_watts = getattr(strava_activity, 'weighted_average_watts', None)
        activity.weighted_average_watts = int(weighted_average_watts) if weighted_average_watts else None

        kilojoules = getattr(strava_activity, 'kilojoules', None)
        activity.kilojoules = float(kilojoules) if kilojoules else None

        # Cadence and calories (use getattr for optional attributes)
        average_cadence = getattr(strava_activity, 'average_cadence', None)
        activity.average_cadence = float(average_cadence) if average_cadence else None

        calories = getattr(strava_activity, 'calories', None)
        activity.calories = float(calories) if calories else None

        # Training metrics
        activity.suffer_score = getattr(strava_activity, 'suffer_score', None)

        # Map data
        start_latlng = getattr(strava_activity, 'start_latlng', None)
        if start_latlng:
            try:
                activity.start_latlng = json.dumps([float(start_latlng.lat), float(start_latlng.lon)])
            except:
                activity.start_latlng = None

        end_latlng = getattr(strava_activity, 'end_latlng', None)
        if end_latlng:
            try:
                activity.end_latlng = json.dumps([float(end_latlng.lat), float(end_latlng.lon)])
            except:
                activity.end_latlng = None

        activity_map = getattr(strava_activity, 'map', None)
        if activity_map:
            activity.map_summary_polyline = getattr(activity_map, 'summary_polyline', None)

        # Flags (use getattr for all)
        activity.trainer = getattr(strava_activity, 'trainer', False)
        activity.commute = getattr(strava_activity, 'commute', False)
        activity.manual = getattr(strava_activity, 'manual', False)
        activity.private = getattr(strava_activity, 'private', False)
        activity.flagged = getattr(strava_activity, 'flagged', False)

        # Calculate TSS if we have athlete thresholds
        athlete = self.session.query(Athlete).filter_by(id=self.athlete_id).first()
        if athlete:
            activity_dict = {
                "moving_time": activity.moving_time,
                "weighted_average_watts": activity.weighted_average_watts,
                "average_heartrate": activity.average_heartrate
            }
            activity.training_stress_score = calculate_activity_tss(
                activity_dict,
                athlete_ftp=athlete.ftp,
                athlete_threshold_hr=athlete.max_heart_rate * 0.95 if athlete.max_heart_rate else None
            )

            # Calculate intensity factor
            if activity.weighted_average_watts and athlete.ftp:
                activity.intensity_factor = self.metrics.calculate_intensity_factor(
                    activity.weighted_average_watts,
                    athlete.ftp
                )

        return activity

    def _sync_recent_streams(self, days: Optional[int] = None) -> int:
        """Sync activity streams for recent activities."""
        if days is None:
            days = settings.SYNC_STREAM_DATA_DAYS

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get recent activities without streams
        activities = self.session.query(Activity).filter(
            Activity.athlete_id == self.athlete_id,
            Activity.start_date >= cutoff_date,
            ~Activity.streams.any()  # No streams yet
        ).limit(50).all()  # Limit to avoid rate limits

        synced = 0
        for activity in activities:
            try:
                self._sync_activity_streams(activity.id)
                synced += 1
            except Exception as e:
                logger.warning(f"Failed to sync streams for activity {activity.id}: {e}")
                continue

        self.session.commit()
        return synced

    def _sync_activity_streams(self, activity_id: int):
        """Sync streams for a single activity."""
        try:
            streams_dict = self.client.get_activity_streams(activity_id)

            for stream_type, stream_data in streams_dict.items():
                # Check if stream already exists
                stream = self.session.query(ActivityStream).filter_by(
                    activity_id=activity_id,
                    stream_type=stream_type
                ).first()

                if not stream:
                    stream = ActivityStream(
                        activity_id=activity_id,
                        stream_type=stream_type
                    )
                    self.session.add(stream)

                # Convert stream data to JSON
                stream.data = json.dumps(stream_data.data)
                stream.original_size = len(stream_data.data)
                stream.resolution = stream_data.resolution

            logger.debug(f"Synced streams for activity {activity_id}")

        except Exception as e:
            logger.error(f"Error syncing streams for activity {activity_id}: {e}")
            raise

    def _calculate_training_loads(self, after_date: Optional[datetime] = None):
        """Calculate CTL, ATL, TSB for athlete."""
        # Get all activities ordered by date
        query = self.session.query(Activity).filter(
            Activity.athlete_id == self.athlete_id
        )

        if after_date:
            # Recalculate from a specific date
            query = query.filter(Activity.start_date >= after_date)

        activities = query.order_by(Activity.start_date).all()

        if not activities:
            logger.info("No activities to calculate training loads")
            return

        # Get existing training loads to continue from previous values
        previous_load = self.session.query(TrainingLoad).filter(
            TrainingLoad.athlete_id == self.athlete_id
        ).order_by(TrainingLoad.date.desc()).first()

        previous_ctl = previous_load.ctl if previous_load else 0.0
        previous_atl = previous_load.atl if previous_load else 0.0

        # Group activities by date and calculate daily TSS
        daily_tss: Dict[date, float] = {}
        for activity in activities:
            activity_date = activity.start_date.date()
            tss = activity.training_stress_score or 0.0
            daily_tss[activity_date] = daily_tss.get(activity_date, 0.0) + tss

        # Calculate CTL, ATL, TSB for each day
        current_ctl = previous_ctl
        current_atl = previous_atl

        for day, daily_tss_value in sorted(daily_tss.items()):
            # Update CTL and ATL
            current_ctl = self.metrics.calculate_ctl([daily_tss_value], current_ctl)
            current_atl = self.metrics.calculate_atl([daily_tss_value], current_atl)
            current_tsb = self.metrics.calculate_tsb(current_ctl, current_atl)

            # Save or update training load
            load = self.session.query(TrainingLoad).filter_by(
                athlete_id=self.athlete_id,
                date=day
            ).first()

            if not load:
                load = TrainingLoad(
                    athlete_id=self.athlete_id,
                    date=day
                )
                self.session.add(load)

            load.daily_tss = daily_tss_value
            load.ctl = current_ctl
            load.atl = current_atl
            load.tsb = current_tsb

        self.session.commit()
        logger.info(f"Calculated training loads for {len(daily_tss)} days")

    def _create_sync_record(self, sync_type: str, status: str) -> SyncMetadata:
        """Create a sync metadata record."""
        sync_record = SyncMetadata(
            athlete_id=self.athlete_id,
            sync_type=sync_type,
            sync_status=status,
            started_at=datetime.utcnow()
        )
        self.session.add(sync_record)
        self.session.commit()
        return sync_record

    def _get_last_successful_sync(self) -> Optional[SyncMetadata]:
        """Get the last successful sync record."""
        return self.session.query(SyncMetadata).filter(
            SyncMetadata.athlete_id == self.athlete_id,
            SyncMetadata.sync_status == "success"
        ).order_by(SyncMetadata.completed_at.desc()).first()
