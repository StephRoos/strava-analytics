"""Strava API client with OAuth, rate limiting, and error handling."""

import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from stravalib.client import Client
from stravalib.exc import RateLimitExceeded, AccessUnauthorized
from config.settings import settings, get_database_session
from models.database.oauth_token import OAuthToken
from utils.logger import get_logger

logger = get_logger(__name__)


class StravaClient:
    """
    Wrapper around stravalib Client with enhanced features:
    - OAuth2 authentication and token refresh
    - Rate limiting and exponential backoff
    - Error handling and retry logic
    - Token persistence
    """

    def __init__(self, athlete_id: Optional[int] = None):
        """
        Initialize Strava client.

        Args:
            athlete_id: Athlete ID to load stored tokens (optional)
        """
        self.client = Client()
        self.athlete_id = athlete_id
        self._token: Optional[OAuthToken] = None

        # Rate limiting tracking
        self._request_count_15min = 0
        self._request_count_daily = 0
        self._window_15min_start = datetime.utcnow()
        self._window_daily_start = datetime.utcnow()

        # Load existing token if athlete_id provided
        if athlete_id:
            self._load_token()

    def _load_token(self) -> bool:
        """Load OAuth token from database."""
        try:
            session = get_database_session()
            token = session.query(OAuthToken).filter_by(
                athlete_id=self.athlete_id
            ).order_by(OAuthToken.created_at.desc()).first()

            if token:
                self._token = token
                # Check if token needs refresh
                if token.needs_refresh():
                    logger.info(f"Token for athlete {self.athlete_id} needs refresh")
                    self._refresh_access_token()
                else:
                    # Set access token in client
                    self.client.access_token = token.access_token
                    logger.info(f"Loaded valid token for athlete {self.athlete_id}")
                return True
            else:
                logger.warning(f"No token found for athlete {self.athlete_id}")
                return False

        except Exception as e:
            logger.error(f"Error loading token: {e}", exc_info=True)
            return False

    def get_authorization_url(self, redirect_uri: Optional[str] = None) -> str:
        """
        Get Strava OAuth authorization URL.

        Args:
            redirect_uri: Callback URL after authorization

        Returns:
            Authorization URL to redirect user to
        """
        redirect_uri = redirect_uri or settings.STRAVA_REDIRECT_URI
        auth_url = self.client.authorization_url(
            client_id=settings.STRAVA_CLIENT_ID,
            redirect_uri=redirect_uri,
            scope=["activity:read_all", "profile:read_all"]
        )
        logger.info(f"Generated authorization URL: {auth_url}")
        return auth_url

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Token response dictionary with athlete info
        """
        try:
            logger.info("Exchanging authorization code for token")
            token_response = self.client.exchange_code_for_token(
                client_id=settings.STRAVA_CLIENT_ID,
                client_secret=settings.STRAVA_CLIENT_SECRET,
                code=code
            )

            # Convert stravalib response to dictionary properly
            if isinstance(token_response, dict):
                token_dict = token_response
            else:
                # Handle stravalib object - convert to dict
                token_dict = dict(token_response)

            logger.info(f"Token received, keys: {token_dict.keys()}")

            # Set access token in client to make API calls
            self.client.access_token = token_dict["access_token"]

            # Fetch athlete info separately (Strava doesn't include it in token response anymore)
            logger.info("Fetching athlete information...")
            athlete = self.client.get_athlete()

            # Add athlete info to token dict
            token_dict["athlete"] = {
                "id": athlete.id,
                "username": athlete.username,
                "firstname": athlete.firstname,
                "lastname": athlete.lastname,
                "profile_medium": athlete.profile_medium,
                "profile": athlete.profile
            }

            logger.info(f"Athlete info retrieved: {athlete.id} - {athlete.firstname} {athlete.lastname}")

            # Save token to database (now with athlete info)
            self._save_token(token_dict)

            logger.info(f"Successfully obtained token for athlete {athlete.id}")
            return token_dict

        except Exception as e:
            logger.error(f"Error exchanging code for token: {e}", exc_info=True)
            raise

    def _refresh_access_token(self) -> bool:
        """
        Refresh expired access token using refresh token.

        Returns:
            True if refresh successful, False otherwise
        """
        if not self._token:
            logger.error("No token available to refresh")
            return False

        try:
            logger.info(f"Refreshing access token for athlete {self.athlete_id}")
            refresh_response = self.client.refresh_access_token(
                client_id=settings.STRAVA_CLIENT_ID,
                client_secret=settings.STRAVA_CLIENT_SECRET,
                refresh_token=self._token.refresh_token
            )

            # Update token in database
            self._save_token(refresh_response)

            logger.info(f"Successfully refreshed token for athlete {self.athlete_id}")
            return True

        except Exception as e:
            logger.error(f"Error refreshing token: {e}", exc_info=True)
            return False

    def _save_token(self, token_response: Dict[str, Any]):
        """
        Save or update OAuth token in database.

        Args:
            token_response: Token response from Strava
        """
        try:
            session = get_database_session()

            # Extract athlete ID from response (handle both dict and object)
            athlete_data = token_response.get("athlete", {})
            if isinstance(athlete_data, dict):
                athlete_id = athlete_data.get("id")
            else:
                # Handle object with attributes
                athlete_id = getattr(athlete_data, "id", None)

            if not athlete_id:
                # Log the response for debugging
                logger.error(f"Token response structure: {token_response}")
                raise ValueError(f"No athlete ID in token response. Athlete data: {athlete_data}")

            self.athlete_id = athlete_id

            # Create or update token
            expires_at = datetime.fromtimestamp(token_response["expires_at"])

            # Handle scope (might be list or string)
            scope = token_response.get("scope", [])
            if isinstance(scope, list):
                scope_str = ",".join(scope)
            else:
                scope_str = str(scope)

            token = OAuthToken(
                athlete_id=athlete_id,
                access_token=token_response["access_token"],
                refresh_token=token_response["refresh_token"],
                expires_at=expires_at,
                token_type=token_response.get("token_type", "Bearer"),
                scope=scope_str
            )

            session.add(token)
            session.commit()

            self._token = token
            self.client.access_token = token.access_token

            logger.info(f"Saved token for athlete {athlete_id}, expires at {expires_at}")

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving token: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def _check_rate_limit(self):
        """Check and enforce rate limits."""
        now = datetime.utcnow()

        # Reset 15-minute window
        if (now - self._window_15min_start) > timedelta(minutes=15):
            self._request_count_15min = 0
            self._window_15min_start = now

        # Reset daily window
        if (now - self._window_daily_start) > timedelta(days=1):
            self._request_count_daily = 0
            self._window_daily_start = now

        # Check limits
        if self._request_count_15min >= settings.STRAVA_RATE_LIMIT_15MIN:
            wait_time = 900 - (now - self._window_15min_start).seconds
            logger.warning(f"15-minute rate limit reached, waiting {wait_time}s")
            time.sleep(wait_time + 1)
            self._request_count_15min = 0
            self._window_15min_start = datetime.utcnow()

        if self._request_count_daily >= settings.STRAVA_RATE_LIMIT_DAILY:
            wait_time = 86400 - (now - self._window_daily_start).seconds
            logger.warning(f"Daily rate limit reached, waiting {wait_time}s")
            raise RateLimitExceeded("Daily rate limit exceeded")

        # Increment counters
        self._request_count_15min += 1
        self._request_count_daily += 1

    def _make_request_with_retry(self, func, *args, max_retries: int = 3, **kwargs):
        """
        Make API request with exponential backoff retry logic.

        Args:
            func: Function to call
            max_retries: Maximum number of retries
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result
        """
        self._check_rate_limit()

        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                return result

            except RateLimitExceeded as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 60  # Exponential backoff: 1m, 2m, 4m
                    logger.warning(f"Rate limit exceeded, retrying in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    logger.error("Rate limit exceeded, max retries reached")
                    raise

            except AccessUnauthorized as e:
                logger.error("Access unauthorized, attempting token refresh")
                if self._refresh_access_token():
                    # Retry with refreshed token
                    continue
                else:
                    raise

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s
                    logger.warning(f"Request failed: {e}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    raise

    def get_athlete(self):
        """Get authenticated athlete profile."""
        logger.info("Fetching athlete profile")
        return self._make_request_with_retry(self.client.get_athlete)

    def get_activities(
        self,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
        limit: Optional[int] = None
    ):
        """
        Get activities for authenticated athlete.

        Args:
            before: Return activities before this date
            after: Return activities after this date
            limit: Maximum number of activities to return

        Returns:
            Iterator of activity summaries
        """
        logger.info(f"Fetching activities (before={before}, after={after}, limit={limit})")
        return self._make_request_with_retry(
            self.client.get_activities,
            before=before,
            after=after,
            limit=limit
        )

    def get_activity(self, activity_id: int, include_all_efforts: bool = False):
        """
        Get detailed activity by ID.

        Args:
            activity_id: Activity ID
            include_all_efforts: Include all segment efforts

        Returns:
            Detailed activity object
        """
        logger.info(f"Fetching activity {activity_id}")
        return self._make_request_with_retry(
            self.client.get_activity,
            activity_id,
            include_all_efforts=include_all_efforts
        )

    def get_activity_streams(
        self,
        activity_id: int,
        types: Optional[List[str]] = None,
        resolution: str = "medium"
    ):
        """
        Get activity streams (time-series data).

        Args:
            activity_id: Activity ID
            types: Stream types to fetch (time, latlng, distance, altitude, heartrate, watts, cadence, etc.)
            resolution: Data resolution (low, medium, high)

        Returns:
            Dictionary of stream data
        """
        if types is None:
            types = ["time", "distance", "latlng", "altitude", "heartrate", "watts", "cadence", "temp"]

        logger.info(f"Fetching streams for activity {activity_id}: {types}")
        return self._make_request_with_retry(
            self.client.get_activity_streams,
            activity_id,
            types=types,
            resolution=resolution
        )

    def get_athlete_zones(self):
        """Get athlete's heart rate and power zones."""
        logger.info("Fetching athlete zones")
        return self._make_request_with_retry(self.client.get_athlete_zones)

    @property
    def is_authenticated(self) -> bool:
        """Check if client has valid authentication."""
        return self._token is not None and not self._token.is_expired()

    @property
    def rate_limit_status(self) -> Dict[str, int]:
        """Get current rate limit status."""
        return {
            "15min_used": self._request_count_15min,
            "15min_limit": settings.STRAVA_RATE_LIMIT_15MIN,
            "daily_used": self._request_count_daily,
            "daily_limit": settings.STRAVA_RATE_LIMIT_DAILY,
        }


def create_strava_client(athlete_id: Optional[int] = None) -> StravaClient:
    """
    Factory function to create a Strava client.

    Args:
        athlete_id: Athlete ID to load stored tokens

    Returns:
        Configured StravaClient instance
    """
    return StravaClient(athlete_id=athlete_id)
