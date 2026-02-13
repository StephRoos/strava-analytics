"""Sidebar component with athlete info and navigation."""

import streamlit as st
from datetime import datetime
from app.auth.strava_oauth import get_current_athlete, logout
from config.settings import get_database_session
from models import Activity, SyncMetadata
from utils.logger import get_logger

logger = get_logger(__name__)


def render_sidebar():
    """Render sidebar with athlete info, stats, and controls."""
    with st.sidebar:
        st.title("🚴 Strava Analytics")

        if st.session_state.get("authenticated", False):
            _render_athlete_info()
            st.divider()
            _render_quick_stats()
            st.divider()
            _render_sync_controls()
            st.divider()
            _render_logout_button()
        else:
            st.info("👤 Non connecté")
            st.markdown("Connectez-vous pour accéder à vos données Strava.")


def _render_athlete_info():
    """Display authenticated athlete information."""
    athlete = get_current_athlete()

    if athlete:
        # Profile picture
        if athlete.profile_medium:
            st.image(athlete.profile_medium, width=100)

        # Name
        st.markdown(f"### {athlete.fullname}")

        # Location
        if athlete.city and athlete.country:
            st.caption(f"📍 {athlete.city}, {athlete.country}")
        elif athlete.country:
            st.caption(f"📍 {athlete.country}")

        # Key metrics
        col1, col2 = st.columns(2)
        with col1:
            if athlete.weight:
                st.metric("Poids", f"{athlete.weight:.1f} kg")
        with col2:
            if athlete.ftp:
                st.metric("FTP", f"{athlete.ftp} W")

        # Account type
        if athlete.premium and athlete.premium != "False":
            st.caption("⭐ Compte Premium")
    else:
        st.warning("⚠️ Profil non trouvé")


def _render_quick_stats():
    """Display quick statistics."""
    st.markdown("### 📊 Statistiques")

    if not st.session_state.get("athlete_id"):
        return

    try:
        session = get_database_session()
        athlete_id = st.session_state.athlete_id

        # Count total activities
        total_activities = session.query(Activity).filter_by(
            athlete_id=athlete_id
        ).count()

        # Count activities this month
        from datetime import date
        current_month_start = date.today().replace(day=1)
        monthly_activities = session.query(Activity).filter(
            Activity.athlete_id == athlete_id,
            Activity.start_date >= current_month_start
        ).count()

        # Total distance (km)
        from sqlalchemy import func
        total_distance = session.query(
            func.sum(Activity.distance)
        ).filter_by(athlete_id=athlete_id).scalar() or 0
        total_distance_km = total_distance / 1000.0

        session.close()

        # Display metrics
        st.metric("Activités totales", f"{total_activities:,}")
        st.metric("Ce mois-ci", f"{monthly_activities}")
        st.metric("Distance totale", f"{total_distance_km:,.1f} km")

    except Exception as e:
        logger.error(f"Error fetching quick stats: {e}")
        st.error("Erreur lors du chargement des statistiques")


def _render_sync_controls():
    """Display sync status and controls."""
    st.markdown("### 🔄 Synchronisation")

    if not st.session_state.get("athlete_id"):
        return

    try:
        session = get_database_session()
        athlete_id = st.session_state.athlete_id

        # Get last sync
        last_sync = session.query(SyncMetadata).filter_by(
            athlete_id=athlete_id
        ).order_by(SyncMetadata.completed_at.desc()).first()

        if last_sync and last_sync.completed_at:
            # Calculate time since last sync
            time_since = datetime.utcnow() - last_sync.completed_at
            hours = int(time_since.total_seconds() / 3600)
            minutes = int((time_since.total_seconds() % 3600) / 60)

            if hours > 0:
                time_str = f"il y a {hours}h {minutes}m"
            else:
                time_str = f"il y a {minutes}m"

            # Status indicator
            if last_sync.sync_status == "success":
                st.success(f"✅ Dernière sync : {time_str}")
                st.caption(f"{last_sync.activities_synced} activités synchronisées")
            else:
                st.error(f"❌ Dernière sync : {time_str}")
                st.caption(f"Statut : {last_sync.sync_status}")
        else:
            st.warning("⚠️ Aucune synchronisation effectuée")

        session.close()

        # Sync button
        if st.button("🔄 Synchroniser", use_container_width=True):
            st.session_state.trigger_sync = True
            st.rerun()

    except Exception as e:
        logger.error(f"Error rendering sync controls: {e}")


def _render_logout_button():
    """Display logout button."""
    if st.button("🚪 Se déconnecter", use_container_width=True):
        logout()
