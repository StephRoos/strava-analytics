"""Authentication module for Strava OAuth."""

from app.auth.strava_oauth import check_authentication, handle_oauth_callback, logout

__all__ = ["check_authentication", "handle_oauth_callback", "logout"]
