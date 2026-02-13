"""Activity History page with filters, table, and details."""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from app.auth.strava_oauth import require_authentication
from app.components.sidebar import render_sidebar
from app.components.activity_map import render_activity_map
from config.settings import get_database_session
from models import Activity
from utils.logger import get_logger

logger = get_logger(__name__)

# Page config
st.set_page_config(
    page_title="Activity History - Strava Analytics",
    page_icon="",
    layout="wide"
)

# Render sidebar
render_sidebar()


@require_authentication
def main():
    """Main activity history page."""
    st.title(" Historique des Activités")

    athlete_id = st.session_state.athlete_id
    session = get_database_session()

    # Check if activities exist
    total_activities = session.query(Activity).filter_by(athlete_id=athlete_id).count()

    if total_activities == 0:
        session.close()
        st.warning(" Aucune activité trouvée. Synchronisez vos données dans Settings.")
        if st.button(" Aller à Settings"):
            st.switch_page("app/pages/6_Settings.py")
        st.stop()

    st.markdown(f"**{total_activities:,} activités** au total")

    st.markdown("---")

    # Filters
    render_filters(session, athlete_id)

    st.markdown("---")

    # Activity table
    render_activity_table(session, athlete_id)

    session.close()


def render_filters(session, athlete_id):
    """Render filter controls."""
    st.markdown("###  Filtres")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Date range
        date_option = st.selectbox(
            "Période",
            ["7 derniers jours", "30 derniers jours", "3 derniers mois", "6 derniers mois", "Cette année", "Tout"],
            index=2
        )

        today = date.today()
        if date_option == "7 derniers jours":
            start_date = today - timedelta(days=7)
        elif date_option == "30 derniers jours":
            start_date = today - timedelta(days=30)
        elif date_option == "3 derniers mois":
            start_date = today - timedelta(days=90)
        elif date_option == "6 derniers mois":
            start_date = today - timedelta(days=180)
        elif date_option == "Cette année":
            start_date = date(today.year, 1, 1)
        else:
            start_date = None

        st.session_state.filter_start_date = start_date

    with col2:
        # Activity type filter
        activity_types = session.query(Activity.type).filter_by(
            athlete_id=athlete_id
        ).distinct().all()
        types = ["Tous"] + sorted([t[0] for t in activity_types if t[0]])

        selected_type = st.selectbox("Type d'activité", types)
        st.session_state.filter_type = None if selected_type == "Tous" else selected_type

    with col3:
        # Distance filter
        distance_option = st.selectbox(
            "Distance",
            ["Toutes", "< 5 km", "5-10 km", "10-20 km", "> 20 km"]
        )

        if distance_option == "< 5 km":
            st.session_state.filter_distance_min = 0
            st.session_state.filter_distance_max = 5000
        elif distance_option == "5-10 km":
            st.session_state.filter_distance_min = 5000
            st.session_state.filter_distance_max = 10000
        elif distance_option == "10-20 km":
            st.session_state.filter_distance_min = 10000
            st.session_state.filter_distance_max = 20000
        elif distance_option == "> 20 km":
            st.session_state.filter_distance_min = 20000
            st.session_state.filter_distance_max = None
        else:
            st.session_state.filter_distance_min = None
            st.session_state.filter_distance_max = None

    with col4:
        # Sort order
        sort_option = st.selectbox(
            "Trier par",
            ["Date (récent)", "Date (ancien)", "Distance", "Durée"]
        )
        st.session_state.sort_option = sort_option


def render_activity_table(session, athlete_id):
    """Render activities table with filters applied."""
    st.markdown("###  Liste des Activités")

    # Build query with filters
    query = session.query(Activity).filter_by(athlete_id=athlete_id)

    # Apply date filter
    if st.session_state.get('filter_start_date'):
        query = query.filter(Activity.start_date >= st.session_state.filter_start_date)

    # Apply type filter
    if st.session_state.get('filter_type'):
        query = query.filter(Activity.type == st.session_state.filter_type)

    # Apply distance filters
    if st.session_state.get('filter_distance_min') is not None:
        query = query.filter(Activity.distance >= st.session_state.filter_distance_min)
    if st.session_state.get('filter_distance_max') is not None:
        query = query.filter(Activity.distance <= st.session_state.filter_distance_max)

    # Apply sorting
    sort_option = st.session_state.get('sort_option', 'Date (récent)')
    if sort_option == "Date (récent)":
        query = query.order_by(Activity.start_date.desc())
    elif sort_option == "Date (ancien)":
        query = query.order_by(Activity.start_date.asc())
    elif sort_option == "Distance":
        query = query.order_by(Activity.distance.desc())
    elif sort_option == "Durée":
        query = query.order_by(Activity.moving_time.desc())

    # Pagination
    activities = query.all()
    total_filtered = len(activities)

    st.markdown(f"**{total_filtered:,} activités** correspondent aux filtres")

    if total_filtered == 0:
        st.info("Aucune activité ne correspond aux filtres sélectionnés.")
        return

    # Pagination controls
    items_per_page = 20
    total_pages = (total_filtered + items_per_page - 1) // items_per_page

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=1,
            key="activity_page"
        )

    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_activities = activities[start_idx:end_idx]

    # Build table data
    table_data = []
    for activity in page_activities:
        table_data.append({
            "ID": activity.id,
            "Date": activity.start_date.strftime("%Y-%m-%d %H:%M"),
            "Nom": activity.name,
            "Type": activity.type,
            "Distance": f"{activity.distance_km:.2f} km" if activity.distance else "-",
            "Durée": activity.duration_formatted if activity.moving_time else "-",
            "Dénivelé": f"{activity.elevation_gain_m:.0f} m" if activity.total_elevation_gain else "-",
            "Pace": f"{activity.average_pace_min_per_km:.2f} min/km" if activity.type == "Run" and activity.average_pace_min_per_km else "-"
        })

    df = pd.DataFrame(table_data)

    # Display table with selection
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )

    # Show activity details if one is selected
    if event.selection and event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_activity = page_activities[selected_idx]
        render_activity_details(selected_activity)

    # Export button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Exporter en CSV",
            data=csv,
            file_name=f"strava_activities_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )


def render_activity_details(activity):
    """Render detailed view of selected activity."""
    st.markdown("---")
    st.markdown(f"###  Détails : {activity.name}")

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Distance", f"{activity.distance_km:.2f} km" if activity.distance else "N/A")

    with col2:
        st.metric("Durée", activity.duration_formatted if activity.moving_time else "N/A")

    with col3:
        st.metric("Dénivelé", f"{activity.elevation_gain_m:.0f} m" if activity.total_elevation_gain else "N/A")

    with col4:
        if activity.average_heartrate:
            st.metric("FC moyenne", f"{activity.average_heartrate:.0f} bpm")
        elif activity.average_watts:
            st.metric("Puissance", f"{activity.average_watts:.0f} W")
        else:
            st.metric("Type", activity.type)

    st.markdown("---")

    # Map and details in columns
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("####  Carte du parcours")
        render_activity_map(activity)

    with col2:
        st.markdown("####  Statistiques")

        if activity.average_speed:
            st.write(f"**Vitesse moy.** : {activity.average_speed * 3.6:.1f} km/h")

        if activity.type == "Run" and activity.average_pace_min_per_km:
            pace = activity.average_pace_min_per_km
            st.write(f"**Allure moy.** : {int(pace)}:{int((pace % 1) * 60):02d} min/km")

        if activity.average_heartrate:
            st.write(f"**FC moy.** : {activity.average_heartrate:.0f} bpm")
            if activity.max_heartrate:
                st.write(f"**FC max** : {activity.max_heartrate} bpm")

        if activity.average_watts:
            st.write(f"**Puissance moy.** : {activity.average_watts:.0f} W")
            if activity.weighted_average_watts:
                st.write(f"**NP** : {activity.weighted_average_watts} W")

        if activity.training_stress_score:
            st.write(f"**TSS** : {activity.training_stress_score:.1f}")

        if activity.calories:
            st.write(f"**Calories** : {activity.calories:.0f} kcal")

        # Flags
        flags = []
        if activity.trainer:
            flags.append(" Indoor")
        if activity.commute:
            flags.append(" Trajet")
        if activity.manual:
            flags.append("✍️ Manuel")

        if flags:
            st.write(" ".join(flags))


if __name__ == "__main__":
    main()
