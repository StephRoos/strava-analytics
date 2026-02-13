"""Weight Training Analytics page with strength training metrics."""

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
    page_title="Weight Training Analytics - Strava Analytics",
    page_icon="",
    layout="wide"
)

# Render sidebar
render_sidebar()


@require_authentication
def main():
    """Main weight training analytics page."""
    st.title("Analyse Musculation")

    athlete_id = st.session_state.athlete_id
    session = get_database_session()

    # Check data - WeightTraining and Workout types
    training_count = session.query(Activity).filter(
        Activity.athlete_id == athlete_id,
        Activity.type.in_(['WeightTraining', 'Workout', 'Crossfit'])
    ).count()

    if training_count == 0:
        session.close()
        st.warning("Aucune séance de musculation. Synchronisez vos données dans Settings.")
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
        # Get available sport types
        sport_types = session.query(Activity.sport_type).filter(
            Activity.athlete_id == athlete_id,
            Activity.type.in_(['WeightTraining', 'Workout', 'Crossfit'])
        ).distinct().all()
        sport_list = ["Tous"] + sorted([s[0] for s in sport_types if s[0]])

        selected_sport = st.selectbox(
            "Type d'entraînement",
            sport_list
        )

    start_date = date.today() - timedelta(days=period_days)
    sport_filter = None if selected_sport == "Tous" else selected_sport

    st.markdown("---")

    # Training Overview
    render_training_overview(session, athlete_id, start_date, sport_filter)
    st.markdown("---")

    # Volume Analysis
    render_volume_analysis(session, athlete_id, start_date, sport_filter)
    st.markdown("---")

    # Activity Distribution
    render_activity_distribution(session, athlete_id, start_date, sport_filter)

    session.close()


def render_training_overview(session, athlete_id, start_date, sport_filter=None):
    """Render training overview."""
    sport_label = f" - {sport_filter}" if sport_filter else ""
    st.markdown(f"### Vue d'Ensemble{sport_label}")

    # Get activities
    query = session.query(Activity).filter(
        Activity.athlete_id == athlete_id,
        Activity.type.in_(['WeightTraining', 'Workout', 'Crossfit']),
        Activity.start_date >= start_date
    )

    if sport_filter:
        query = query.filter(Activity.sport_type == sport_filter)

    activities = query.order_by(Activity.start_date).all()

    if not activities:
        st.info("Aucune activité dans la période sélectionnée.")
        return

    # Calculate metrics
    total_sessions = len(activities)
    total_time = sum(a.moving_time or 0 for a in activities) / 3600  # hours
    avg_duration = (total_time / total_sessions * 60) if total_sessions > 0 else 0  # minutes

    # KPIs
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Séances", f"{total_sessions}")

    with col2:
        st.metric("Temps Total", f"{total_time:.1f}h")

    with col3:
        st.metric("Durée Moyenne", f"{avg_duration:.0f} min")

    with col4:
        weeks = (date.today() - start_date).days / 7
        avg_per_week = total_sessions / weeks if weeks > 0 else 0
        st.metric("Séances/semaine", f"{avg_per_week:.1f}")

    # Session duration over time
    st.markdown("#### Durée des Séances")

    data = []
    for a in activities:
        data.append({
            'date': pd.Timestamp(a.start_date),
            'duration_min': (a.moving_time or 0) / 60
        })

    df = pd.DataFrame(data)

    if not df.empty:
        fig_duration = px.scatter(
            df,
            x='date',
            y='duration_min',
            trendline="lowess",
            title="Évolution de la durée des séances",
            labels={'date': 'Date', 'duration_min': 'Durée (min)'}
        )
        fig_duration.update_layout(height=300)
        st.plotly_chart(fig_duration, use_container_width=True)


def render_volume_analysis(session, athlete_id, start_date, sport_filter=None):
    """Render volume analysis charts."""
    sport_label = f" - {sport_filter}" if sport_filter else ""
    st.markdown(f"### Analyse de Volume{sport_label}")

    query = session.query(Activity).filter(
        Activity.athlete_id == athlete_id,
        Activity.type.in_(['WeightTraining', 'Workout', 'Crossfit']),
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
                'time': 0,
                'sessions': 0
            }

        weekly_data[week_key]['time'] += (activity.moving_time or 0) / 3600
        weekly_data[week_key]['sessions'] += 1

    # Create dataframe
    df_weekly = pd.DataFrame([
        {
            'Week': week,
            'Temps (h)': data['time'],
            'Séances': data['sessions']
        }
        for week, data in sorted(weekly_data.items())
    ])

    col1, col2 = st.columns(2)

    with col1:
        # Weekly sessions
        st.markdown("#### Séances par Semaine")
        fig_sessions = px.bar(
            df_weekly,
            x='Week',
            y='Séances',
            title="Nombre de séances"
        )
        fig_sessions.update_layout(height=300)
        st.plotly_chart(fig_sessions, use_container_width=True)

    with col2:
        # Weekly time
        st.markdown("#### Temps Hebdomadaire")
        fig_time = px.bar(
            df_weekly,
            x='Week',
            y='Temps (h)',
            title="Heures d'entraînement"
        )
        fig_time.update_layout(height=300)
        st.plotly_chart(fig_time, use_container_width=True)

    # Summary stats
    col1, col2 = st.columns(2)

    with col1:
        st.metric("Séances/semaine", f"{df_weekly['Séances'].mean():.1f}")

    with col2:
        st.metric("Temps/semaine", f"{df_weekly['Temps (h)'].mean():.1f}h")


def render_activity_distribution(session, athlete_id, start_date, sport_filter=None):
    """Render activity distribution charts."""
    sport_label = f" - {sport_filter}" if sport_filter else ""
    st.markdown(f"### Distribution des Séances{sport_label}")

    query = session.query(Activity).filter(
        Activity.athlete_id == athlete_id,
        Activity.type.in_(['WeightTraining', 'Workout', 'Crossfit']),
        Activity.start_date >= start_date
    )

    if sport_filter:
        query = query.filter(Activity.sport_type == sport_filter)

    activities = query.all()

    # Get all unique types and create color mapping
    all_types = set()
    for activity in activities:
        activity_type = activity.sport_type or activity.type
        all_types.add(activity_type)

    # Create consistent color map for all types
    color_sequence = px.colors.qualitative.Plotly
    color_map = {sport_type: color_sequence[i % len(color_sequence)]
                 for i, sport_type in enumerate(sorted(all_types))}

    col1, col2 = st.columns(2)

    with col1:
        # By type
        type_counts = {}
        for activity in activities:
            activity_type = activity.sport_type or activity.type
            type_counts[activity_type] = type_counts.get(activity_type, 0) + 1

        df_types = pd.DataFrame([
            {'Type': k, 'Count': v}
            for k, v in type_counts.items()
        ])

        fig_types = px.pie(
            df_types,
            values='Count',
            names='Type',
            title="Par type d'entraînement",
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
            sport_type = activity.sport_type or activity.type
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
