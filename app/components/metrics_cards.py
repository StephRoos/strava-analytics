"""Metric cards and KPI display components."""

import streamlit as st
from typing import Optional, Union


def display_metric_card(
    label: str,
    value: Union[str, int, float],
    delta: Optional[Union[str, int, float]] = None,
    delta_color: str = "normal",
    help_text: Optional[str] = None
):
    """
    Display a metric card with optional delta.

    Args:
        label: Metric label
        value: Metric value
        delta: Optional delta value (change)
        delta_color: Delta color ("normal", "inverse", "off")
        help_text: Optional help tooltip
    """
    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text
    )


def display_kpi_row(metrics: list):
    """
    Display a row of KPI metrics.

    Args:
        metrics: List of metric dictionaries with keys:
                 - label: str
                 - value: str/int/float
                 - delta: Optional[str/int/float]
                 - help: Optional[str]

    Example:
        display_kpi_row([
            {"label": "Distance", "value": "150 km", "delta": "+10 km"},
            {"label": "Activités", "value": 12, "delta": "+2"},
            {"label": "Temps", "value": "8h 30m"}
        ])
    """
    cols = st.columns(len(metrics))

    for col, metric in zip(cols, metrics):
        with col:
            display_metric_card(
                label=metric.get("label", ""),
                value=metric.get("value", ""),
                delta=metric.get("delta"),
                delta_color=metric.get("delta_color", "normal"),
                help_text=metric.get("help")
            )


def display_stat_card(title: str, value: str, icon: str = "📊", color: str = "#1f77b4"):
    """
    Display a custom styled stat card.

    Args:
        title: Card title
        value: Main value to display
        icon: Emoji icon
        color: Card color (hex)
    """
    st.markdown(
        f"""
        <div style="
            background-color: {color}20;
            border-left: 4px solid {color};
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        ">
            <div style="font-size: 2em;">{icon}</div>
            <div style="color: #666; font-size: 0.9em; margin-top: 5px;">{title}</div>
            <div style="font-size: 1.8em; font-weight: bold; margin-top: 5px;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def display_progress_card(
    title: str,
    current: float,
    target: float,
    unit: str = "",
    show_percentage: bool = True
):
    """
    Display a progress card with progress bar.

    Args:
        title: Card title
        current: Current value
        target: Target value
        unit: Unit string (e.g., "km", "hours")
        show_percentage: Show percentage alongside progress bar
    """
    percentage = min((current / target * 100) if target > 0 else 0, 100)

    st.markdown(f"**{title}**")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.progress(percentage / 100)

    with col2:
        if show_percentage:
            st.markdown(f"**{percentage:.0f}%**")

    st.caption(f"{current:.1f} / {target:.1f} {unit}")


def display_comparison_metrics(
    left_label: str,
    left_value: Union[str, float],
    right_label: str,
    right_value: Union[str, float],
    comparison_text: Optional[str] = None
):
    """
    Display two metrics side by side for comparison.

    Args:
        left_label: Left metric label
        left_value: Left metric value
        right_label: Right metric label
        right_value: Right metric value
        comparison_text: Optional comparison text
    """
    col1, col2 = st.columns(2)

    with col1:
        st.metric(left_label, left_value)

    with col2:
        st.metric(right_label, right_value)

    if comparison_text:
        st.caption(comparison_text)
