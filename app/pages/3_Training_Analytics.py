"""Training Analytics page with advanced metrics and visualizations."""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, date
from app.auth.strava_oauth import require_authentication
from app.components.sidebar import render_sidebar
from app.components.charts import plot_training_load_chart
from config.settings import get_database_session
from models import Activity, TrainingLoad
from sqlalchemy import func, extract
from utils.logger import get_logger

logger = get_logger(__name__)

# Page config
st.set_page_config(
    page_title="Training Analytics - Strava Analytics",
    page_icon="",
    layout="wide"
)

# Render sidebar
render_sidebar()


@require_authentication
def main():
    """Main training analytics page."""
    st.title(" Analyse d'Entraînement")

    athlete_id = st.session_state.athlete_id
    session = get_database_session()

    # Check data
    activity_count = session.query(Activity).filter_by(athlete_id=athlete_id).count()
    training_load_count = session.query(TrainingLoad).filter_by(athlete_id=athlete_id).count()

    if activity_count == 0:
        session.close()
        st.warning(" Aucune activité. Synchronisez vos données dans Settings.")
        st.stop()

    # Filters
    col1, col2, col3 = st.columns([2, 1, 1])

    with col2:
        period_days = st.selectbox(
            "Période d'analyse",
            [30, 90, 180, 365],
            format_func=lambda x: f"{x} jours",
            index=2
        )

    with col3:
        # Get available sport types for Run activities only
        sport_types = session.query(Activity.sport_type).filter(
            Activity.athlete_id == athlete_id,
            Activity.type == 'Run'
        ).distinct().all()
        sport_list = ["Tous"] + sorted([s[0] for s in sport_types if s[0]])

        selected_sport = st.selectbox(
            "Type de course",
            sport_list
        )

    start_date = date.today() - timedelta(days=period_days)
    sport_filter = None if selected_sport == "Tous" else selected_sport

    st.markdown("---")

    # Performance Trends
    render_performance_trends(session, athlete_id, start_date, sport_filter)
    st.markdown("---")

    # Volume Analysis
    render_volume_analysis(session, athlete_id, start_date, sport_filter)
    st.markdown("---")

    # Activity Distribution
    render_activity_distribution(session, athlete_id, start_date, sport_filter)

    session.close()


def render_training_load_section(session, athlete_id, start_date, sport_filter=None):
    """Render training load charts and metrics."""
    sport_label = f" - {sport_filter}" if sport_filter else ""
    st.markdown(f"### Charge d'Entraînement (CTL/ATL/TSB){sport_label}")

    # Get training loads
    loads = session.query(TrainingLoad).filter(
        TrainingLoad.athlete_id == athlete_id,
        TrainingLoad.date >= start_date
    ).order_by(TrainingLoad.date).all()

    if not loads:
        st.info("Aucune donnée de training load. Synchronisez vos activités.")
        return

    # Extract data
    dates = [load.date for load in loads]
    ctl_values = [load.ctl or 0 for load in loads]
    atl_values = [load.atl or 0 for load in loads]
    tsb_values = [load.tsb or 0 for load in loads]
    tss_values = [load.daily_tss or 0 for load in loads]

    # Current metrics
    latest = loads[-1]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "CTL (Fitness)",
            f"{latest.ctl:.1f}",
            help="Chronic Training Load - Votre niveau de forme sur 42 jours"
        )
        st.caption(f" {latest.fitness_level}")

    with col2:
        st.metric(
            "ATL (Fatigue)",
            f"{latest.atl:.1f}",
            help="Acute Training Load - Votre fatigue sur 7 jours"
        )

    with col3:
        delta_color = "normal" if latest.tsb and latest.tsb > -20 else "inverse"
        st.metric(
            "TSB (Form)",
            f"{latest.tsb:.1f}",
            delta_color=delta_color,
            help="Training Stress Balance - Votre fraîcheur"
        )
        st.caption(f" {latest.form_status}")

    with col4:
        # Calculate ramp rate
        if len(loads) >= 7:
            ctl_7_days_ago = loads[-7].ctl if len(loads) >= 7 else latest.ctl
            ramp_rate = latest.ctl - ctl_7_days_ago
            st.metric(
                "Ramp Rate",
                f"{ramp_rate:+.1f}/sem",
                help="Taux de progression du CTL par semaine"
            )
            if abs(ramp_rate) > 8:
                st.caption(" Progression rapide")
            else:
                st.caption("✅ Progression saine")

    # CTL/ATL/TSB Chart
    fig = plot_training_load_chart(dates, ctl_values, atl_values, tsb_values)
    st.plotly_chart(fig, use_container_width=True)

    # TSS Bar chart
    st.markdown("####  Training Stress Score (TSS) Quotidien")

    df_tss = pd.DataFrame({
        'Date': dates,
        'TSS': tss_values
    })

    fig_tss = px.bar(
        df_tss,
        x='Date',
        y='TSS',
        title="TSS Quotidien",
        labels={'TSS': 'Training Stress Score'}
    )
    fig_tss.update_traces(marker_color='#1f77b4')
    fig_tss.update_layout(height=300)

    st.plotly_chart(fig_tss, use_container_width=True)


def render_performance_trends(session, athlete_id, start_date, sport_filter=None):
    """Render performance trend charts."""
    sport_label = f" - {sport_filter}" if sport_filter else ""
    st.markdown(f"### Tendances de Performance{sport_label}")

    # Get activities
    query = session.query(Activity).filter(
        Activity.athlete_id == athlete_id,
        Activity.start_date >= start_date,
        Activity.distance > 0
    )

    # Apply sport filter
    if sport_filter:
        query = query.filter(Activity.sport_type == sport_filter)

    activities = query.order_by(Activity.start_date).all()

    if not activities:
        st.info("Aucune activité dans la période sélectionnée.")
        return

    # Build dataframe
    data = []
    for a in activities:
        data.append({
            'date': pd.Timestamp(a.start_date),  # Convert to pandas Timestamp
            'distance_km': a.distance_km if a.distance else 0,
            'pace_min_per_km': a.average_pace_min_per_km if a.type == "Run" else None,
            'speed_kmh': a.average_speed * 3.6 if a.average_speed else None,
            'hr': a.average_heartrate,
            'power': a.average_watts
        })

    df = pd.DataFrame(data)

    if df.empty:
        st.info("Aucune donnée pour ce type d'activité.")
        return

    # Performance metrics
    col1, col2 = st.columns(2)

    with col1:
        # Distance trend
        st.markdown("####  Distance par Activité")
        fig_dist = px.scatter(
            df,
            x='date',
            y='distance_km',
            trendline="lowess",
            title="Évolution de la distance",
            labels={'date': 'Date', 'distance_km': 'Distance (km)'}
        )
        fig_dist.update_layout(height=300)
        st.plotly_chart(fig_dist, use_container_width=True)

    with col2:
        # Speed/Pace trend - Show pace for running sports
        is_running_sport = sport_filter in ['Run', 'TrailRun'] if sport_filter else False
        has_pace_data = df['pace_min_per_km'].notna().any()

        if (is_running_sport or not sport_filter) and has_pace_data:
            st.markdown("####  Allure Moyenne")
            fig_pace = px.scatter(
                df[df['pace_min_per_km'].notna()],
                x='date',
                y='pace_min_per_km',
                trendline="lowess",
                title="Évolution de l'allure",
                labels={'date': 'Date', 'pace_min_per_km': 'Allure (min/km)'}
            )
            fig_pace.update_yaxes(autorange="reversed")
            fig_pace.update_layout(height=300)
            st.plotly_chart(fig_pace, use_container_width=True)
        elif df['speed_kmh'].notna().any():
            st.markdown("####  Vitesse Moyenne")
            fig_speed = px.scatter(
                df[df['speed_kmh'].notna()],
                x='date',
                y='speed_kmh',
                trendline="lowess",
                title="Évolution de la vitesse",
                labels={'date': 'Date', 'speed_kmh': 'Vitesse (km/h)'}
            )
            fig_speed.update_layout(height=300)
            st.plotly_chart(fig_speed, use_container_width=True)

    # Heart rate trend
    if df['hr'].notna().any():
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("####  Fréquence Cardiaque Moyenne")
            fig_hr = px.scatter(
                df[df['hr'].notna()],
                x='date',
                y='hr',
                trendline="lowess",
                title="Évolution de la FC moyenne",
                labels={'date': 'Date', 'hr': 'FC (bpm)'}
            )
            fig_hr.update_layout(height=300)
            st.plotly_chart(fig_hr, use_container_width=True)


def render_volume_analysis(session, athlete_id, start_date, sport_filter=None):
    """Render volume analysis charts."""
    sport_label = f" - {sport_filter}" if sport_filter else ""
    st.markdown(f"### Analyse de Volume{sport_label}")

    query = session.query(Activity).filter(
        Activity.athlete_id == athlete_id,
        Activity.start_date >= start_date
    )

    if sport_filter:
        query = query.filter(Activity.sport_type == sport_filter)

    activities = query.order_by(Activity.start_date).all()

    if not activities:
        return

    # Group by week
    weekly_data = {}
    for activity in activities:
        week = activity.start_date.isocalendar()[1]
        year = activity.start_date.year
        week_key = f"{year}-W{week:02d}"

        if week_key not in weekly_data:
            weekly_data[week_key] = {
                'distance': 0,
                'time': 0,
                'activities': 0,
                'elevation': 0
            }

        weekly_data[week_key]['distance'] += (activity.distance or 0) / 1000
        weekly_data[week_key]['time'] += (activity.moving_time or 0) / 3600
        weekly_data[week_key]['activities'] += 1
        weekly_data[week_key]['elevation'] += activity.total_elevation_gain or 0

    # Create dataframe
    df_weekly = pd.DataFrame([
        {
            'Week': week,
            'Distance (km)': data['distance'],
            'Temps (h)': data['time'],
            'Activités': data['activities'],
            'Dénivelé (m)': data['elevation']
        }
        for week, data in sorted(weekly_data.items())
    ])

    col1, col2 = st.columns(2)

    with col1:
        # Weekly distance
        st.markdown("####  Distance Hebdomadaire")
        fig_dist = px.bar(
            df_weekly,
            x='Week',
            y='Distance (km)',
            title="Volume hebdomadaire"
        )
        fig_dist.update_layout(height=300)
        st.plotly_chart(fig_dist, use_container_width=True)

    with col2:
        # Weekly time
        st.markdown("####  Temps d'Entraînement Hebdomadaire")
        fig_time = px.bar(
            df_weekly,
            x='Week',
            y='Temps (h)',
            title="Heures d'entraînement"
        )
        fig_time.update_layout(height=300)
        st.plotly_chart(fig_time, use_container_width=True)

    # Summary stats
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Distance/semaine", f"{df_weekly['Distance (km)'].mean():.1f} km")

    with col2:
        st.metric("Temps/semaine", f"{df_weekly['Temps (h)'].mean():.1f}h")

    with col3:
        st.metric("Activités/semaine", f"{df_weekly['Activités'].mean():.1f}")

    with col4:
        st.metric("Dénivelé/semaine", f"{df_weekly['Dénivelé (m)'].mean():.0f} m")


def render_activity_distribution(session, athlete_id, start_date, sport_filter=None):
    """Render activity distribution charts."""
    sport_label = f" - {sport_filter}" if sport_filter else ""
    st.markdown(f"### Distribution des Activités{sport_label}")

    query = session.query(Activity).filter(
        Activity.athlete_id == athlete_id,
        Activity.start_date >= start_date
    )

    if sport_filter:
        query = query.filter(Activity.sport_type == sport_filter)

    activities = query.all()

    col1, col2 = st.columns(2)

    with col1:
        # By type
        type_counts = {}
        for activity in activities:
            activity_type = activity.type or "Unknown"
            type_counts[activity_type] = type_counts.get(activity_type, 0) + 1

        df_types = pd.DataFrame([
            {'Type': k, 'Count': v}
            for k, v in type_counts.items()
        ])

        fig_types = px.pie(
            df_types,
            values='Count',
            names='Type',
            title="Par type d'activité"
        )
        st.plotly_chart(fig_types, use_container_width=True)

    with col2:
        # By day of week
        day_counts = {i: 0 for i in range(7)}
        for activity in activities:
            day_counts[activity.start_date.weekday()] += 1

        day_names = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        df_days = pd.DataFrame([
            {'Jour': day_names[i], 'Count': day_counts[i]}
            for i in range(7)
        ])

        fig_days = px.bar(
            df_days,
            x='Jour',
            y='Count',
            title="Par jour de la semaine"
        )
        st.plotly_chart(fig_days, use_container_width=True)


if __name__ == "__main__":
    main()
