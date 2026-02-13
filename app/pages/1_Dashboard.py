"""Dashboard page with overview and key metrics."""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from app.auth.strava_oauth import require_authentication
from app.components.sidebar import render_sidebar
from app.components.metrics_cards import display_kpi_row
from app.components.charts import (
    plot_training_load_chart,
    plot_activity_distribution,
    plot_weekly_volume
)
from config.settings import get_database_session
from models import Activity, TrainingLoad
from sqlalchemy import func, extract
from utils.logger import get_logger

logger = get_logger(__name__)

# Page config
st.set_page_config(
    page_title="Dashboard - Strava Analytics",
    page_icon="",
    layout="wide"
)

# Render sidebar
render_sidebar()


@require_authentication
def main():
    """Main dashboard page logic."""
    st.title(" Dashboard")
    st.markdown("Vue d'ensemble de vos statistiques d'entraînement")

    athlete_id = st.session_state.athlete_id

    # Check if data exists
    session = get_database_session()
    activity_count = session.query(Activity).filter_by(athlete_id=athlete_id).count()

    if activity_count == 0:
        session.close()
        st.warning(" Aucune activité trouvée. Veuillez synchroniser vos données.")
        if st.button(" Aller à Settings pour synchroniser"):
            st.switch_page("app/pages/5_Settings.py")
        st.stop()

    # Time period selector
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("###  Période")
    with col2:
        period = st.selectbox(
            "Période",
            ["7 jours", "30 jours", "90 jours", "Cette année"],
            index=1,
            label_visibility="collapsed"
        )

    # Calculate date range
    today = date.today()
    if period == "7 jours":
        start_date = today - timedelta(days=7)
    elif period == "30 jours":
        start_date = today - timedelta(days=30)
    elif period == "90 jours":
        start_date = today - timedelta(days=90)
    else:  # This year
        start_date = date(today.year, 1, 1)

    st.markdown("---")

    # KPIs
    render_kpis(athlete_id, start_date, session)

    st.markdown("---")

    # Charts row 1
    col1, col2 = st.columns([2, 1])

    with col1:
        render_training_load_chart(athlete_id, start_date, session)

    with col2:
        render_activity_distribution(athlete_id, start_date, session)

    st.markdown("---")

    # Charts row 2
    render_weekly_volume(athlete_id, start_date, session)

    st.markdown("---")

    # Recent activities
    render_recent_activities(athlete_id, session)

    session.close()


def render_kpis(athlete_id: int, start_date: date, session):
    """Render key performance indicators."""
    # Query activities in period
    activities = session.query(Activity).filter(
        Activity.athlete_id == athlete_id,
        Activity.start_date >= start_date
    ).all()

    if not activities:
        st.info("Aucune activité dans cette période")
        return

    # Calculate metrics
    total_activities = len(activities)
    total_distance = sum(a.distance or 0 for a in activities) / 1000  # km
    total_time = sum(a.moving_time or 0 for a in activities) / 3600  # hours
    total_elevation = sum(a.total_elevation_gain or 0 for a in activities)

    # Average per activity
    avg_distance = total_distance / total_activities if total_activities > 0 else 0

    # Display KPIs
    display_kpi_row([
        {
            "label": "Activités",
            "value": f"{total_activities}",
            "help": "Nombre total d'activités"
        },
        {
            "label": "Distance Totale",
            "value": f"{total_distance:.1f} km",
            "help": f"Moyenne : {avg_distance:.1f} km/activité"
        },
        {
            "label": "Temps Total",
            "value": f"{total_time:.1f}h",
            "help": "Temps en mouvement"
        },
        {
            "label": "Dénivelé Total",
            "value": f"{total_elevation:.0f} m",
            "help": "Dénivelé positif cumulé"
        }
    ])


def render_training_load_chart(athlete_id: int, start_date: date, session):
    """Render CTL/ATL/TSB chart."""
    st.markdown("####  Charge d'Entraînement (CTL/ATL/TSB)")

    # Query training loads
    loads = session.query(TrainingLoad).filter(
        TrainingLoad.athlete_id == athlete_id,
        TrainingLoad.date >= start_date
    ).order_by(TrainingLoad.date).all()

    if not loads:
        st.info("Aucune donnée de charge d'entraînement. Synchronisez vos activités.")
        return

    # Extract data
    dates = [load.date for load in loads]
    ctl_values = [load.ctl or 0 for load in loads]
    atl_values = [load.atl or 0 for load in loads]
    tsb_values = [load.tsb or 0 for load in loads]

    # Plot
    fig = plot_training_load_chart(dates, ctl_values, atl_values, tsb_values)
    st.plotly_chart(fig, use_container_width=True)

    # Current status
    if loads:
        latest = loads[-1]
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("CTL (Fitness)", f"{latest.ctl:.1f}")
            st.caption(latest.fitness_level)

        with col2:
            st.metric("ATL (Fatigue)", f"{latest.atl:.1f}")

        with col3:
            st.metric("TSB (Form)", f"{latest.tsb:.1f}")
            st.caption(latest.form_status)


def render_activity_distribution(athlete_id: int, start_date: date, session):
    """Render activity type distribution pie chart."""
    st.markdown("####  Distribution par Type")

    # Query activity types
    type_counts = session.query(
        Activity.type,
        func.count(Activity.id).label("count")
    ).filter(
        Activity.athlete_id == athlete_id,
        Activity.start_date >= start_date
    ).group_by(Activity.type).all()

    if not type_counts:
        st.info("Aucune activité")
        return

    # Extract data
    types = [tc[0] for tc in type_counts]
    counts = [tc[1] for tc in type_counts]

    # Plot
    fig = plot_activity_distribution(types, counts)
    st.plotly_chart(fig, use_container_width=True)


def render_weekly_volume(athlete_id: int, start_date: date, session):
    """Render weekly training volume chart."""
    st.markdown("####  Volume Hebdomadaire")

    # Query activities
    activities = session.query(Activity).filter(
        Activity.athlete_id == athlete_id,
        Activity.start_date >= start_date
    ).all()

    if not activities:
        st.info("Aucune activité")
        return

    # Group by week
    weekly_data = {}
    for activity in activities:
        week = activity.start_date.isocalendar()[1]
        year = activity.start_date.year
        week_key = f"{year}-W{week:02d}"

        if week_key not in weekly_data:
            weekly_data[week_key] = 0

        weekly_data[week_key] += (activity.distance or 0) / 1000  # km

    # Sort by week
    weeks = sorted(weekly_data.keys())
    distances = [weekly_data[w] for w in weeks]

    # Plot
    fig = plot_weekly_volume(weeks, distances)
    st.plotly_chart(fig, use_container_width=True)


def render_recent_activities(athlete_id: int, session, limit: int = 10):
    """Display recent activities table."""
    st.markdown("### 🕐 Activités Récentes")

    activities = session.query(Activity).filter_by(
        athlete_id=athlete_id
    ).order_by(Activity.start_date.desc()).limit(limit).all()

    if not activities:
        st.info("Aucune activité")
        return

    # Build table data
    data = []
    for activity in activities:
        data.append({
            "Date": activity.start_date.strftime("%Y-%m-%d"),
            "Nom": activity.name,
            "Type": activity.type,
            "Distance": f"{activity.distance_km:.2f} km" if activity.distance else "-",
            "Durée": activity.duration_formatted if activity.moving_time else "-",
            "Dénivelé": f"{activity.elevation_gain_m:.0f} m" if activity.total_elevation_gain else "-"
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
