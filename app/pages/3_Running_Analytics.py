"""Running Analytics page with running-specific metrics."""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta, date
from app.auth.strava_oauth import require_authentication
from app.components.sidebar import render_sidebar
from config.settings import get_database_session
from models import Activity
from utils.logger import get_logger

logger = get_logger(__name__)

# Page config
st.set_page_config(
    page_title="Running Analytics - Strava Analytics",
    page_icon="",
    layout="wide"
)

# Render sidebar
render_sidebar()


@require_authentication
def main():
    """Main running analytics page."""
    st.title("Analyse Course à Pied")

    athlete_id = st.session_state.athlete_id
    session = get_database_session()

    # Check data
    run_count = session.query(Activity).filter(
        Activity.athlete_id == athlete_id,
        Activity.type == 'Run'
    ).count()

    if run_count == 0:
        session.close()
        st.warning("Aucune activité de course. Synchronisez vos données dans Settings.")
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
        # Get available sport types for Run activities
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


def render_performance_trends(session, athlete_id, start_date, sport_filter=None):
    """Render running performance trend charts."""
    sport_label = f" - {sport_filter}" if sport_filter else ""
    st.markdown(f"### Tendances de Performance{sport_label}")

    # Get running activities
    query = session.query(Activity).filter(
        Activity.athlete_id == athlete_id,
        Activity.type == 'Run',
        Activity.start_date >= start_date,
        Activity.distance > 0
    )

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
            'date': pd.Timestamp(a.start_date),
            'distance_km': a.distance_km if a.distance else 0,
            'pace_min_per_km': a.average_pace_min_per_km,
            'elevation_m': a.total_elevation_gain or 0,
            'hr': a.average_heartrate,
            'power': a.average_watts
        })

    df = pd.DataFrame(data)

    if df.empty:
        st.info("Aucune donnée.")
        return

    # Performance metrics
    col1, col2 = st.columns(2)

    with col1:
        # Distance trend
        st.markdown("#### Distance par Course")
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
        # Pace trend
        if df['pace_min_per_km'].notna().any():
            st.markdown("#### Allure Moyenne")
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

    # Heart rate and elevation
    col1, col2 = st.columns(2)

    with col1:
        if df['hr'].notna().any():
            st.markdown("#### Fréquence Cardiaque Moyenne")
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

    with col2:
        st.markdown("#### Dénivelé par Course")
        fig_elev = px.scatter(
            df,
            x='date',
            y='elevation_m',
            trendline="lowess",
            title="Évolution du dénivelé",
            labels={'date': 'Date', 'elevation_m': 'Dénivelé (m)'}
        )
        fig_elev.update_layout(height=300)
        st.plotly_chart(fig_elev, use_container_width=True)

    # Power trend (if available)
    if df['power'].notna().any():
        st.markdown("#### Puissance Moyenne")
        fig_power = px.scatter(
            df[df['power'].notna()],
            x='date',
            y='power',
            trendline="lowess",
            title="Évolution de la puissance moyenne",
            labels={'date': 'Date', 'power': 'Puissance (W)'}
        )
        fig_power.update_layout(height=300)
        st.plotly_chart(fig_power, use_container_width=True)


def render_volume_analysis(session, athlete_id, start_date, sport_filter=None):
    """Render running volume analysis charts."""
    sport_label = f" - {sport_filter}" if sport_filter else ""
    st.markdown(f"### Analyse de Volume{sport_label}")

    query = session.query(Activity).filter(
        Activity.athlete_id == athlete_id,
        Activity.type == 'Run',
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
            'Courses': data['activities'],
            'Dénivelé (m)': data['elevation']
        }
        for week, data in sorted(weekly_data.items())
    ])

    col1, col2 = st.columns(2)

    with col1:
        # Weekly distance
        st.markdown("#### Distance Hebdomadaire")
        fig_dist = px.bar(
            df_weekly,
            x='Week',
            y='Distance (km)',
            title="Kilomètres par semaine"
        )
        fig_dist.update_layout(height=300)
        st.plotly_chart(fig_dist, use_container_width=True)

    with col2:
        # Weekly elevation
        st.markdown("#### Dénivelé Hebdomadaire")
        fig_elev = px.bar(
            df_weekly,
            x='Week',
            y='Dénivelé (m)',
            title="Dénivelé par semaine"
        )
        fig_elev.update_layout(height=300)
        st.plotly_chart(fig_elev, use_container_width=True)

    # Summary stats
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Distance/semaine", f"{df_weekly['Distance (km)'].mean():.1f} km")

    with col2:
        st.metric("Temps/semaine", f"{df_weekly['Temps (h)'].mean():.1f}h")

    with col3:
        st.metric("Courses/semaine", f"{df_weekly['Courses'].mean():.1f}")

    with col4:
        st.metric("Dénivelé/semaine", f"{df_weekly['Dénivelé (m)'].mean():.0f} m")


def render_activity_distribution(session, athlete_id, start_date, sport_filter=None):
    """Render running activity distribution charts."""
    sport_label = f" - {sport_filter}" if sport_filter else ""
    st.markdown(f"### Distribution des Courses{sport_label}")

    query = session.query(Activity).filter(
        Activity.athlete_id == athlete_id,
        Activity.type == 'Run',
        Activity.start_date >= start_date
    )

    if sport_filter:
        query = query.filter(Activity.sport_type == sport_filter)

    activities = query.all()

    # Get all unique types and create color mapping
    all_types = set()
    for activity in activities:
        activity_type = activity.sport_type or "Run"
        all_types.add(activity_type)

    # Create consistent color map for all types
    color_sequence = px.colors.qualitative.Plotly
    color_map = {sport_type: color_sequence[i % len(color_sequence)]
                 for i, sport_type in enumerate(sorted(all_types))}

    col1, col2 = st.columns(2)

    with col1:
        # By sport type
        type_counts = {}
        for activity in activities:
            activity_type = activity.sport_type or "Run"
            type_counts[activity_type] = type_counts.get(activity_type, 0) + 1

        df_types = pd.DataFrame([
            {'Type': k, 'Count': v}
            for k, v in type_counts.items()
        ])

        fig_types = px.pie(
            df_types,
            values='Count',
            names='Type',
            title="Par type de course",
            color='Type',
            color_discrete_map=color_map
        )
        st.plotly_chart(fig_types, use_container_width=True)

    with col2:
        # By day of week with sport type distinction
        day_names = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

        # Build data with sport type breakdown
        day_type_data = []
        for activity in activities:
            day_idx = activity.start_date.weekday()
            sport_type = activity.sport_type or "Run"
            day_type_data.append({
                'Jour': day_names[day_idx],
                'Type': sport_type,
                'day_order': day_idx
            })

        if day_type_data:
            df_days = pd.DataFrame(day_type_data)
            # Count occurrences
            df_days_grouped = df_days.groupby(['Jour', 'Type', 'day_order']).size().reset_index(name='Count')
            # Sort by day order
            df_days_grouped = df_days_grouped.sort_values('day_order')

            fig_days = px.bar(
                df_days_grouped,
                x='Jour',
                y='Count',
                color='Type',
                title="Par jour de la semaine",
                category_orders={'Jour': day_names},
                color_discrete_map=color_map
            )
            fig_days.update_layout(barmode='stack')
            st.plotly_chart(fig_days, use_container_width=True)
        else:
            st.info("Aucune donnée")


if __name__ == "__main__":
    main()
