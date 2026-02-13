"""Activity map component using Folium."""

import folium
import polyline
import streamlit as st
from streamlit_folium import st_folium


def create_activity_map(activity_polyline: str, start_latlng: list = None, center: list = None, zoom: int = 13):
    """
    Create a Folium map with activity route.

    Args:
        activity_polyline: Google polyline encoded string
        start_latlng: [lat, lng] for start marker
        center: [lat, lng] for map center (if None, uses start_latlng)
        zoom: Initial zoom level

    Returns:
        Folium map object
    """
    if not activity_polyline:
        # No polyline, create simple map with marker
        if start_latlng:
            m = folium.Map(location=start_latlng, zoom_start=zoom)
            folium.Marker(
                start_latlng,
                popup="Start",
                icon=folium.Icon(color="green", icon="play")
            ).add_to(m)
            return m
        return None

    try:
        # Decode polyline to coordinates
        coordinates = polyline.decode(activity_polyline)

        if not coordinates:
            return None

        # Use center or first point
        map_center = center or coordinates[0]

        # Create map
        m = folium.Map(location=map_center, zoom_start=zoom)

        # Add route line
        folium.PolyLine(
            coordinates,
            color="red",
            weight=3,
            opacity=0.8
        ).add_to(m)

        # Add start marker
        if coordinates:
            folium.Marker(
                coordinates[0],
                popup="Départ",
                icon=folium.Icon(color="green", icon="play")
            ).add_to(m)

        # Add end marker
        if len(coordinates) > 1:
            folium.Marker(
                coordinates[-1],
                popup="Arrivée",
                icon=folium.Icon(color="red", icon="stop")
            ).add_to(m)

        # Fit bounds to route
        m.fit_bounds(coordinates)

        return m

    except Exception as e:
        st.error(f"Erreur lors de la création de la carte : {e}")
        return None


def render_activity_map(activity):
    """
    Render an activity map in Streamlit.

    Args:
        activity: Activity object with map_summary_polyline
    """
    if not activity.map_summary_polyline:
        st.info("🗺️ Aucune carte disponible pour cette activité")
        return

    # Parse start location
    start_latlng = None
    if activity.start_latlng:
        import json
        try:
            start_latlng = json.loads(activity.start_latlng)
        except:
            pass

    # Create and render map
    m = create_activity_map(
        activity.map_summary_polyline,
        start_latlng=start_latlng
    )

    if m:
        st_folium(m, width=700, height=500)
