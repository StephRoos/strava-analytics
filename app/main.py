"""Main Streamlit application entry point."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from app.auth.strava_oauth import check_authentication, start_oauth_flow
from app.components.sidebar import render_sidebar
from utils.logger import get_logger

logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="Strava Analytics",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/anthropics/claude-code",
        "Report a bug": "https://github.com/anthropics/claude-code/issues",
        "About": "# Strava Analytics\nAnalysez vos données Strava avec ML"
    }
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding-top: 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 5px;
    }
    .stButton>button {
        width: 100%;
    }
    h1 {
        color: #FC4C02;
    }
    </style>
    """, unsafe_allow_html=True)


def main():
    """Main application logic."""
    # Render sidebar
    render_sidebar()

    # Check authentication
    if not check_authentication():
        # Show welcome page for unauthenticated users
        show_welcome_page()
    else:
        # Show main dashboard for authenticated users
        show_dashboard_home()


def show_welcome_page():
    """Display welcome page for unauthenticated users."""
    st.title("🚴 Bienvenue sur Strava Analytics")

    st.markdown("""
    ### Analysez vos données Strava avec des insights avancés

    Strava Analytics vous permet de :
    - 📊 **Visualiser** vos performances et progressions
    - 🎯 **Analyser** votre charge d'entraînement (CTL/ATL/TSB)
    - 🗺️ **Explorer** vos parcours sur des cartes interactives
    - 🤖 **Optimiser** vos plans d'entraînement avec le machine learning
    - 📈 **Suivre** vos métriques détaillées (zones, allure, puissance)
    """)

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📊 Tableaux de Bord")
        st.write("KPIs, graphiques interactifs et statistiques détaillées")

    with col2:
        st.markdown("### 🎯 Analyse Training Load")
        st.write("CTL, ATL, TSB pour optimiser votre entraînement")

    with col3:
        st.markdown("### 🤖 Intelligence Artificielle")
        st.write("Prédictions et recommandations personnalisées")

    st.markdown("---")

    # Authentication section
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### 🔐 Commencez maintenant")
        start_oauth_flow()

    st.markdown("---")

    # Features showcase
    with st.expander("📋 Fonctionnalités détaillées"):
        st.markdown("""
        #### 🏠 Dashboard
        - KPIs : distance, activités, temps d'entraînement
        - Graphique de charge d'entraînement
        - Activités récentes
        - Distribution par type d'activité

        #### 📊 Historique des Activités
        - Tableau filtrable et triable
        - Cartes interactives des parcours
        - Profils d'élévation
        - Export des données (CSV/Excel)

        #### 🎯 Analyse d'Entraînement
        - Courbes CTL/ATL/TSB
        - Distribution temps par zones
        - Tendances de performance
        - Analyse de volume hebdomadaire/mensuel

        #### 🤖 Recommandations ML
        - Prédiction de performance
        - Optimisation de la charge d'entraînement
        - Recommandations de récupération
        - Clustering d'activités (patterns)

        #### ⚙️ Paramètres
        - Connexion Strava
        - Synchronisation des données
        - Configuration zones d'entraînement
        - Édition profil (FTP, poids)
        """)

    with st.expander("❓ FAQ"):
        st.markdown("""
        **Q: Mes données sont-elles sécurisées ?**
        A: Oui, toutes vos données sont stockées localement dans une base SQLite sur votre machine.

        **Q: Combien de temps prend la synchronisation initiale ?**
        A: Environ 1-2 minutes pour 100 activités, selon votre connexion internet.

        **Q: Quelles sont les limites de l'API Strava ?**
        A: 100 requêtes par 15 minutes et 1000 par jour. L'application gère automatiquement ces limites.

        **Q: Puis-je utiliser l'application sans connexion Strava ?**
        A: Non, l'application nécessite une connexion Strava pour synchroniser vos données.

        **Q: Les modèles ML fonctionnent-ils immédiatement ?**
        A: Les modèles nécessitent au minimum 50 activités pour générer des prédictions précises.
        """)


def show_dashboard_home():
    """Display main dashboard for authenticated users."""
    st.title("🏠 Dashboard")

    st.info(
        "👈 **Navigation** : Utilisez la barre latérale pour accéder aux différentes pages.\n\n"
        "📄 Les pages principales sont :\n"
        "- **Dashboard** : Vue d'ensemble (vous êtes ici)\n"
        "- **Activity History** : Historique détaillé\n"
        "- **Training Analytics** : Analyse approfondie\n"
        "- **ML Recommendations** : Suggestions IA\n"
        "- **Settings** : Configuration et sync"
    )

    # Check if sync is needed
    if st.session_state.get("trigger_sync"):
        st.session_state.trigger_sync = False
        st.info("🔄 Redirection vers la page Settings pour synchroniser...")
        st.switch_page("app/pages/5_⚙️_Settings.py")

    st.markdown("---")

    # Quick metrics
    st.markdown("### 📊 Vue d'Ensemble")

    try:
        from config.settings import get_database_session
        from models import Activity
        from sqlalchemy import func
        from datetime import date, timedelta

        session = get_database_session()
        athlete_id = st.session_state.athlete_id

        # This month stats
        month_start = date.today().replace(day=1)
        month_activities = session.query(Activity).filter(
            Activity.athlete_id == athlete_id,
            Activity.start_date >= month_start
        ).all()

        # Calculate totals
        total_distance = sum(a.distance or 0 for a in month_activities) / 1000
        total_time = sum(a.moving_time or 0 for a in month_activities) / 3600
        total_elevation = sum(a.total_elevation_gain or 0 for a in month_activities)

        # Previous month for comparison
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
        prev_month_activities = session.query(Activity).filter(
            Activity.athlete_id == athlete_id,
            Activity.start_date >= prev_month_start,
            Activity.start_date < month_start
        ).all()

        prev_distance = sum(a.distance or 0 for a in prev_month_activities) / 1000
        prev_count = len(prev_month_activities)

        session.close()

        # Display metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            delta_activities = len(month_activities) - prev_count
            st.metric(
                "Activités ce mois",
                len(month_activities),
                delta=f"{delta_activities:+d}" if prev_count > 0 else None
            )

        with col2:
            delta_distance = total_distance - prev_distance
            st.metric(
                "Distance (km)",
                f"{total_distance:.1f}",
                delta=f"{delta_distance:+.1f}" if prev_distance > 0 else None
            )

        with col3:
            st.metric(
                "Temps total",
                f"{total_time:.1f}h"
            )

        with col4:
            st.metric(
                "Dénivelé (m)",
                f"{total_elevation:.0f}"
            )

    except Exception as e:
        logger.error(f"Error loading dashboard data: {e}")
        st.error("Erreur lors du chargement des données. Veuillez synchroniser vos activités.")

    st.markdown("---")

    # Guide for first-time users
    st.markdown("### 🚀 Premiers Pas")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **1. Synchroniser vos données**
        - Allez dans ⚙️ Settings
        - Cliquez sur "Synchroniser"
        - Attendez que la sync soit terminée
        """)

    with col2:
        st.markdown("""
        **2. Explorer vos données**
        - 📊 Activity History : voir toutes vos activités
        - 🎯 Training Analytics : analyser votre progression
        - 🤖 ML Recommendations : obtenir des suggestions
        """)


if __name__ == "__main__":
    main()
