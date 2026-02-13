"""Streamlit OAuth handler for Strava authentication."""

import streamlit as st
from urllib.parse import parse_qs, urlparse
from utils.strava_client import StravaClient
from config.settings import get_database_session
from models.database.athlete import Athlete
from utils.logger import get_logger

logger = get_logger(__name__)


def init_session_state():
    """Initialize session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "athlete_id" not in st.session_state:
        st.session_state.athlete_id = None
    if "athlete_name" not in st.session_state:
        st.session_state.athlete_name = None
    if "oauth_code" not in st.session_state:
        st.session_state.oauth_code = None


def check_authentication() -> bool:
    """
    Check if user is authenticated.

    Returns:
        True if authenticated, False otherwise
    """
    init_session_state()

    # Check for OAuth callback in query parameters
    query_params = st.query_params

    if "code" in query_params and not st.session_state.authenticated:
        # Handle OAuth callback
        code = query_params["code"]
        if isinstance(code, list):
            code = code[0]

        success = handle_oauth_callback(code)

        # Clear query parameters
        st.query_params.clear()

        if success:
            st.rerun()

    return st.session_state.authenticated


def handle_oauth_callback(code: str) -> bool:
    """
    Handle OAuth callback and exchange code for token.

    Args:
        code: Authorization code from Strava

    Returns:
        True if authentication successful, False otherwise
    """
    try:
        logger.info("Handling OAuth callback")

        # Create client and exchange code for token
        client = StravaClient()
        token_response = client.exchange_code_for_token(code)

        # Extract athlete info
        athlete_info = token_response.get("athlete", {})
        athlete_id = athlete_info.get("id")

        if not athlete_id:
            logger.error("No athlete ID in token response")
            st.error("❌ Échec de l'authentification : aucun ID athlète reçu")
            return False

        # Save athlete profile to database
        from config.settings import get_database_session
        from models.database.athlete import Athlete

        session = get_database_session()
        try:
            # Check if athlete exists
            athlete = session.query(Athlete).filter_by(id=athlete_id).first()

            if not athlete:
                athlete = Athlete(id=athlete_id)
                session.add(athlete)

            # Update athlete data
            athlete.username = athlete_info.get("username")
            athlete.firstname = athlete_info.get("firstname")
            athlete.lastname = athlete_info.get("lastname")
            athlete.profile_medium = athlete_info.get("profile_medium")
            athlete.profile = athlete_info.get("profile")

            session.commit()
            logger.info(f"Saved athlete profile for {athlete_id}")

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving athlete profile: {e}")
        finally:
            session.close()

        # Update session state
        st.session_state.authenticated = True
        st.session_state.athlete_id = athlete_id
        st.session_state.athlete_name = f"{athlete_info.get('firstname', '')} {athlete_info.get('lastname', '')}".strip()

        logger.info(f"Successfully authenticated athlete {athlete_id}")
        st.success(f"✅ Authentification réussie ! Bienvenue {st.session_state.athlete_name}")

        return True

    except Exception as e:
        logger.error(f"OAuth callback failed: {e}", exc_info=True)
        st.error(f"❌ Erreur lors de l'authentification : {str(e)}")
        return False


def start_oauth_flow():
    """
    Start the OAuth authentication flow.

    Displays a button that redirects to Strava authorization page.
    """
    init_session_state()

    st.markdown("### 🔐 Connexion à Strava")
    st.write("Connectez votre compte Strava pour synchroniser vos données.")

    # Create Strava client and get authorization URL
    client = StravaClient()
    auth_url = client.get_authorization_url()

    # Display connect button
    st.markdown(
        f"""
        <a href="{auth_url}" target="_self">
            <button style="
                background-color: #FC4C02;
                color: white;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                text-decoration: none;
            ">
                🚴 Se connecter avec Strava
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.info(
        "ℹ️ **Note** : Vous serez redirigé vers Strava pour autoriser l'accès. "
        "Cette application nécessite l'accès en lecture à vos activités et votre profil."
    )


def logout():
    """Logout user and clear session state."""
    st.session_state.authenticated = False
    st.session_state.athlete_id = None
    st.session_state.athlete_name = None
    st.session_state.oauth_code = None

    logger.info("User logged out")
    st.success("✅ Déconnexion réussie")
    st.rerun()


def get_current_athlete() -> Athlete:
    """
    Get current authenticated athlete from database.

    Returns:
        Athlete object or None
    """
    if not st.session_state.authenticated or not st.session_state.athlete_id:
        return None

    try:
        session = get_database_session()
        athlete = session.query(Athlete).filter_by(
            id=st.session_state.athlete_id
        ).first()
        session.close()
        return athlete
    except Exception as e:
        logger.error(f"Error fetching athlete: {e}")
        return None


def require_authentication(func):
    """
    Decorator to require authentication for a page.

    Usage:
        @require_authentication
        def my_page():
            st.write("This page requires authentication")
    """
    def wrapper(*args, **kwargs):
        if not check_authentication():
            st.warning("⚠️ Vous devez vous connecter pour accéder à cette page.")
            start_oauth_flow()
            st.stop()
        return func(*args, **kwargs)
    return wrapper
