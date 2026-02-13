"""Settings page for Strava connection and data synchronization."""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from datetime import datetime
from app.auth.strava_oauth import require_authentication, get_current_athlete
from app.components.sidebar import render_sidebar
from config.settings import get_database_session
from models import Athlete, Activity, SyncMetadata, TrainingZone
from utils.sync_manager import SyncManager
from utils.logger import get_logger

logger = get_logger(__name__)

# Page config
st.set_page_config(
    page_title="Settings - Strava Analytics",
    page_icon="⚙️",
    layout="wide"
)

# Render sidebar
render_sidebar()


@require_authentication
def main():
    """Main settings page logic."""
    st.title("⚙️ Paramètres")

    # Tabs for different settings sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔄 Synchronisation",
        "👤 Profil Athlète",
        "🎯 Zones d'Entraînement",
        "📊 Base de Données"
    ])

    with tab1:
        render_sync_section()

    with tab2:
        render_athlete_profile()

    with tab3:
        render_training_zones()

    with tab4:
        render_database_stats()


def render_sync_section():
    """Render data synchronization section."""
    st.markdown("### 🔄 Synchronisation des Données")

    athlete_id = st.session_state.athlete_id

    # Get last sync info
    session = get_database_session()
    last_sync = session.query(SyncMetadata).filter_by(
        athlete_id=athlete_id
    ).order_by(SyncMetadata.completed_at.desc()).first()

    # Activity count
    activity_count = session.query(Activity).filter_by(
        athlete_id=athlete_id
    ).count()

    session.close()

    # Display sync status
    col1, col2 = st.columns([2, 1])

    with col1:
        if last_sync and last_sync.completed_at:
            time_ago = datetime.utcnow() - last_sync.completed_at
            hours = int(time_ago.total_seconds() / 3600)

            if last_sync.sync_status == "success":
                st.success(f"✅ Dernière synchronisation réussie il y a {hours}h")
                st.caption(
                    f"**{last_sync.activities_synced}** activités synchronisées "
                    f"en {last_sync.duration_seconds}s"
                )
            elif last_sync.sync_status == "failed":
                st.error(f"❌ Dernière synchronisation échouée il y a {hours}h")
                if last_sync.error_message:
                    st.caption(f"Erreur : {last_sync.error_message}")
        else:
            st.warning("⚠️ Aucune synchronisation effectuée")
            st.caption("Cliquez sur 'Synchroniser Maintenant' pour commencer")

    with col2:
        st.metric("Activités en base", f"{activity_count:,}")

    st.markdown("---")

    # Sync options
    col1, col2 = st.columns(2)

    with col1:
        sync_type = st.radio(
            "Type de synchronisation",
            ["Incrémentale (nouveau uniquement)", "Complète (tout re-synchroniser)"],
            help="Incrémentale : synchronise seulement les nouvelles activités\n"
                 "Complète : re-synchronise toutes les activités"
        )

    with col2:
        sync_streams = st.checkbox(
            "Synchroniser les streams détaillés",
            value=True,
            help="Données temporelles (FC, puissance, cadence) pour les 90 derniers jours"
        )

    # Sync button
    if st.button("🔄 Synchroniser Maintenant", type="primary", use_container_width=True):
        perform_sync(
            athlete_id,
            sync_type="full" if "Complète" in sync_type else "incremental"
        )

    st.markdown("---")

    # Sync history
    with st.expander("📜 Historique des Synchronisations"):
        display_sync_history(athlete_id)


def perform_sync(athlete_id: int, sync_type: str = "incremental"):
    """Perform data synchronization with progress indicator."""
    progress_bar = st.progress(0)
    status_text = st.empty()

    def progress_callback(status: str, current: int, total: int):
        """Update progress bar and status."""
        progress = current / total if total > 0 else 0
        progress_bar.progress(progress)
        status_text.text(f"{status} ({current}/{total})")

    try:
        sync_manager = SyncManager(athlete_id=athlete_id)

        if sync_type == "full":
            status_text.text("🔄 Synchronisation complète en cours...")
            result = sync_manager.full_sync(progress_callback=progress_callback)
        else:
            status_text.text("🔄 Synchronisation incrémentale en cours...")
            result = sync_manager.incremental_sync(progress_callback=progress_callback)

        if result["status"] == "success":
            st.success(
                f"✅ Synchronisation terminée !\n\n"
                f"**{result['activities_synced']}** activités synchronisées\n\n"
                f"**{result.get('streams_synced', 0)}** streams synchronisés\n\n"
                f"Durée : {result.get('duration_seconds', 0)}s"
            )
            st.balloons()
        else:
            st.error(f"❌ Échec de la synchronisation : {result.get('error')}")

    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        st.error(f"❌ Erreur lors de la synchronisation : {str(e)}")

    finally:
        progress_bar.empty()
        status_text.empty()


def display_sync_history(athlete_id: int, limit: int = 10):
    """Display sync history table."""
    session = get_database_session()
    syncs = session.query(SyncMetadata).filter_by(
        athlete_id=athlete_id
    ).order_by(SyncMetadata.started_at.desc()).limit(limit).all()
    session.close()

    if not syncs:
        st.info("Aucun historique de synchronisation")
        return

    # Build table data
    data = []
    for sync in syncs:
        status_icon = "✅" if sync.sync_status == "success" else "❌"
        data.append({
            "Date": sync.started_at.strftime("%Y-%m-%d %H:%M"),
            "Type": sync.sync_type.capitalize(),
            "Statut": f"{status_icon} {sync.sync_status}",
            "Activités": sync.activities_synced or 0,
            "Durée": f"{sync.duration_seconds}s" if sync.completed_at else "N/A"
        })

    st.table(data)


def render_athlete_profile():
    """Render athlete profile editing section."""
    st.markdown("### 👤 Profil Athlète")

    athlete = get_current_athlete()

    if not athlete:
        st.error("Profil athlète non trouvé")
        return

    st.info(f"**ID Strava** : {athlete.id}")

    # Profile form
    with st.form("athlete_profile_form"):
        col1, col2 = st.columns(2)

        with col1:
            weight = st.number_input(
                "Poids (kg)",
                min_value=30.0,
                max_value=200.0,
                value=float(athlete.weight) if athlete.weight else 70.0,
                step=0.1,
                help="Votre poids en kilogrammes"
            )

            ftp = st.number_input(
                "FTP (Watts)",
                min_value=0,
                max_value=500,
                value=int(athlete.ftp) if athlete.ftp else 200,
                help="Functional Threshold Power pour cyclisme"
            )

        with col2:
            max_hr = st.number_input(
                "Fréquence Cardiaque Maximale",
                min_value=100,
                max_value=250,
                value=int(athlete.max_heart_rate) if athlete.max_heart_rate else 180,
                help="Votre FC maximale"
            )

            resting_hr = st.number_input(
                "Fréquence Cardiaque au Repos",
                min_value=30,
                max_value=100,
                value=int(athlete.resting_heart_rate) if athlete.resting_heart_rate else 60,
                help="Votre FC au repos"
            )

        submitted = st.form_submit_button("💾 Sauvegarder", use_container_width=True)

        if submitted:
            try:
                session = get_database_session()
                athlete = session.query(Athlete).filter_by(id=athlete.id).first()

                athlete.weight = weight
                athlete.ftp = ftp
                athlete.max_heart_rate = max_hr
                athlete.resting_heart_rate = resting_hr

                session.commit()
                session.close()

                st.success("✅ Profil mis à jour avec succès !")
                st.rerun()

            except Exception as e:
                logger.error(f"Error updating athlete profile: {e}")
                st.error(f"❌ Erreur lors de la mise à jour : {str(e)}")


def render_training_zones():
    """Render training zones configuration."""
    st.markdown("### 🎯 Zones d'Entraînement")

    athlete = get_current_athlete()

    if not athlete:
        st.error("Profil athlète non trouvé")
        return

    # Zone type selection
    zone_type = st.radio(
        "Type de zones",
        ["Fréquence Cardiaque", "Puissance"],
        horizontal=True
    )

    zone_type_key = "heart_rate" if zone_type == "Fréquence Cardiaque" else "power"

    # Get existing zones
    session = get_database_session()
    zones = session.query(TrainingZone).filter_by(
        athlete_id=athlete.id,
        zone_type=zone_type_key
    ).order_by(TrainingZone.zone_number).all()
    session.close()

    if zones:
        st.markdown(f"**Zones {zone_type} configurées :**")

        # Display zones table
        zone_data = []
        for zone in zones:
            zone_data.append({
                "Zone": zone.zone_number,
                "Nom": zone.name or "-",
                "Min": int(zone.min_value),
                "Max": int(zone.max_value)
            })

        st.table(zone_data)

    else:
        st.info(f"Aucune zone {zone_type.lower()} configurée")

        # Auto-generate button
        if st.button(f"🎯 Générer Zones {zone_type} par Défaut"):
            generate_default_zones(athlete, zone_type_key)


def generate_default_zones(athlete: Athlete, zone_type: str):
    """Generate default training zones."""
    try:
        session = get_database_session()

        if zone_type == "heart_rate":
            if not athlete.max_heart_rate:
                st.error("❌ Veuillez d'abord configurer votre FC maximale dans le profil")
                return

            zones = TrainingZone.create_default_hr_zones(
                athlete.id,
                athlete.max_heart_rate
            )

        elif zone_type == "power":
            if not athlete.ftp:
                st.error("❌ Veuillez d'abord configurer votre FTP dans le profil")
                return

            zones = TrainingZone.create_default_power_zones(
                athlete.id,
                athlete.ftp
            )

        for zone in zones:
            session.add(zone)

        session.commit()
        session.close()

        st.success(f"✅ Zones {zone_type} générées avec succès !")
        st.rerun()

    except Exception as e:
        logger.error(f"Error generating zones: {e}")
        st.error(f"❌ Erreur : {str(e)}")


def render_database_stats():
    """Render database statistics."""
    st.markdown("### 📊 Statistiques de la Base de Données")

    try:
        session = get_database_session()
        athlete_id = st.session_state.athlete_id

        # Count records
        activity_count = session.query(Activity).filter_by(athlete_id=athlete_id).count()
        from models import ActivityStream, TrainingLoad
        stream_count = session.query(ActivityStream).join(Activity).filter(
            Activity.athlete_id == athlete_id
        ).count()
        training_load_count = session.query(TrainingLoad).filter_by(
            athlete_id=athlete_id
        ).count()

        session.close()

        # Display stats
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Activités", f"{activity_count:,}")

        with col2:
            st.metric("Streams", f"{stream_count:,}")

        with col3:
            st.metric("Training Loads", f"{training_load_count:,}")

        st.markdown("---")

        # Database file info
        import os
        db_path = "data/strava.db"
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
            st.info(f"📁 Taille de la base de données : **{db_size:.2f} MB**")

    except Exception as e:
        logger.error(f"Error fetching database stats: {e}")
        st.error("Erreur lors du chargement des statistiques")


if __name__ == "__main__":
    main()
