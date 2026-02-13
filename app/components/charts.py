"""Chart components using Plotly."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import streamlit as st
from typing import List, Dict, Optional


def plot_training_load_chart(
    dates: List,
    ctl_values: List[float],
    atl_values: List[float],
    tsb_values: List[float],
    title: str = "Charge d'Entraînement (CTL/ATL/TSB)"
) -> go.Figure:
    """
    Plot training load chart with CTL, ATL, and TSB.

    Args:
        dates: List of dates
        ctl_values: Chronic Training Load values
        atl_values: Acute Training Load values
        tsb_values: Training Stress Balance values
        title: Chart title

    Returns:
        Plotly figure
    """
    fig = go.Figure()

    # CTL (Fitness)
    fig.add_trace(go.Scatter(
        x=dates,
        y=ctl_values,
        name="CTL (Fitness)",
        line=dict(color="#1f77b4", width=2),
        mode="lines"
    ))

    # ATL (Fatigue)
    fig.add_trace(go.Scatter(
        x=dates,
        y=atl_values,
        name="ATL (Fatigue)",
        line=dict(color="#ff7f0e", width=2),
        mode="lines"
    ))

    # TSB (Form)
    fig.add_trace(go.Scatter(
        x=dates,
        y=tsb_values,
        name="TSB (Form)",
        line=dict(color="#2ca02c", width=2),
        mode="lines",
        fill="tozeroy"
    ))

    # Layout
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Training Load",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=400
    )

    return fig


def plot_activity_distribution(
    activity_types: List[str],
    counts: List[int],
    title: str = "Distribution des Activités par Type"
) -> go.Figure:
    """
    Plot activity type distribution as pie chart.

    Args:
        activity_types: List of activity type names
        counts: List of activity counts
        title: Chart title

    Returns:
        Plotly figure
    """
    fig = go.Figure(data=[go.Pie(
        labels=activity_types,
        values=counts,
        hole=0.3,
        textinfo="label+percent",
        textposition="auto"
    )])

    fig.update_layout(
        title=title,
        height=400
    )

    return fig


def plot_time_in_zones(
    zone_numbers: List[int],
    time_values: List[float],
    zone_names: Optional[List[str]] = None,
    title: str = "Temps par Zone d'Entraînement"
) -> go.Figure:
    """
    Plot time in training zones as bar chart.

    Args:
        zone_numbers: List of zone numbers
        time_values: List of time values (seconds)
        zone_names: Optional list of zone names
        title: Chart title

    Returns:
        Plotly figure
    """
    # Convert seconds to minutes
    time_minutes = [t / 60.0 for t in time_values]

    # Create labels
    if zone_names:
        labels = [f"Zone {num}: {name}" for num, name in zip(zone_numbers, zone_names)]
    else:
        labels = [f"Zone {num}" for num in zone_numbers]

    # Color scale (green to red)
    colors = px.colors.sequential.RdYlGn_r[:len(zone_numbers)]

    fig = go.Figure(data=[go.Bar(
        x=labels,
        y=time_minutes,
        marker_color=colors,
        text=[f"{t:.0f} min" for t in time_minutes],
        textposition="auto"
    )])

    fig.update_layout(
        title=title,
        xaxis_title="Zone",
        yaxis_title="Temps (minutes)",
        height=400
    )

    return fig


def plot_activity_timeline(
    df: pd.DataFrame,
    x_col: str = "start_date",
    y_col: str = "distance_km",
    color_col: str = "type",
    title: str = "Historique des Activités"
) -> go.Figure:
    """
    Plot activity timeline as scatter plot.

    Args:
        df: DataFrame with activity data
        x_col: Column for x-axis (date)
        y_col: Column for y-axis (metric)
        color_col: Column for color grouping
        title: Chart title

    Returns:
        Plotly figure
    """
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        hover_data=["name", "distance_km", "moving_time"],
        title=title,
        labels={
            x_col: "Date",
            y_col: "Distance (km)",
            color_col: "Type"
        }
    )

    fig.update_layout(height=400)

    return fig


def plot_weekly_volume(
    weeks: List[str],
    distances: List[float],
    title: str = "Volume Hebdomadaire"
) -> go.Figure:
    """
    Plot weekly training volume as bar chart.

    Args:
        weeks: List of week labels
        distances: List of weekly distances
        title: Chart title

    Returns:
        Plotly figure
    """
    fig = go.Figure(data=[go.Bar(
        x=weeks,
        y=distances,
        marker_color="#1f77b4",
        text=[f"{d:.1f} km" for d in distances],
        textposition="auto"
    )])

    fig.update_layout(
        title=title,
        xaxis_title="Semaine",
        yaxis_title="Distance (km)",
        height=400
    )

    return fig


def plot_pace_distribution(
    pace_values: List[float],
    title: str = "Distribution de l'Allure"
) -> go.Figure:
    """
    Plot pace distribution as histogram.

    Args:
        pace_values: List of pace values (min/km)
        title: Chart title

    Returns:
        Plotly figure
    """
    fig = go.Figure(data=[go.Histogram(
        x=pace_values,
        nbinsx=20,
        marker_color="#1f77b4"
    )])

    fig.update_layout(
        title=title,
        xaxis_title="Allure (min/km)",
        yaxis_title="Nombre d'activités",
        height=400
    )

    return fig


@st.cache_data(ttl=3600)
def create_heatmap_calendar(df: pd.DataFrame, value_col: str = "tss") -> go.Figure:
    """
    Create a calendar heatmap (contribution graph style).

    Args:
        df: DataFrame with date and value columns
        value_col: Column name for values

    Returns:
        Plotly figure
    """
    # This is a placeholder - full implementation would require more complex logic
    fig = go.Figure()

    fig.update_layout(
        title="Calendrier d'Activités",
        height=200
    )

    return fig
