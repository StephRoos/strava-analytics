# Strava Analytics

Application web complète pour analyser vos données Strava, avec synchronisation automatique, visualisations interactives et recommandations basées sur le machine learning.

## Fonctionnalités

- **Synchronisation Strava** : Récupération automatique de vos activités via l'API Strava
- **Base de données locale** : Stockage SQLite de toutes vos données (activités, métriques, zones)
- **Tableaux de bord interactifs** : Interface Streamlit multi-pages avec visualisations Plotly
- **Analyse d'entraînement** : Calcul de CTL/ATL/TSB, distribution par zones, tendances de performance
- **Machine Learning** : Prédiction de performance, optimisation de charge, clustering d'activités
- **Cartes interactives** : Visualisation de vos parcours avec Folium

## Architecture

```
strava-analytics/
├── app/                    # Application Streamlit
│   ├── main.py            # Point d'entrée
│   ├── pages/             # Pages multi-pages
│   ├── components/        # Composants UI réutilisables
│   └── auth/              # OAuth Strava
├── config/                # Configuration centralisée
│   └── settings.py        # Gestion des variables d'environnement
├── models/
│   ├── database/          # Modèles SQLAlchemy (Athlete, Activity, etc.)
│   └── ml/                # Modèles machine learning
├── utils/                 # Utilitaires
│   ├── strava_client.py   # Client API Strava
│   ├── sync_manager.py    # Gestionnaire de synchronisation
│   ├── training_metrics.py # Calculs TSS, CTL, ATL, TSB
│   └── logger.py          # Configuration logging
├── scripts/               # Scripts d'initialisation
│   └── init_db.py         # Initialisation base de données
└── data/                  # Base SQLite et cache
```

## Prérequis

- Python 3.13+
- Compte Strava
- Application Strava API (credentials Client ID et Client Secret)

## Installation

### 1. Cloner le dépôt

```bash
git clone <url-du-repo>
cd strava-analytics
```

### 2. Installer les dépendances

Ce projet utilise `uv` comme gestionnaire de paquets :

```bash
# Installer uv si nécessaire
pip install uv

# Installer les dépendances
uv sync
```

### 3. Configuration Strava API

1. Allez sur https://www.strava.com/settings/api
2. Créez une application Strava
3. Notez votre **Client ID** et **Client Secret**
4. Configurez **Authorization Callback Domain** : `localhost`

### 4. Configuration de l'environnement

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer .env et ajouter vos credentials
nano .env  # ou votre éditeur préféré
```

Remplissez les variables suivantes dans `.env` :

```ini
# Strava API Credentials
STRAVA_CLIENT_ID=votre_client_id
STRAVA_CLIENT_SECRET=votre_client_secret

# Database (SQLite par défaut)
DATABASE_URL=sqlite:///./data/strava.db

# App Settings
APP_NAME=Strava Analytics
DEBUG=True
LOG_LEVEL=INFO
```

### 5. Initialiser la base de données

```bash
python scripts/init_db.py
```

Pour vérifier que tout fonctionne :

```bash
python scripts/init_db.py --check
```

## Utilisation

### Lancer l'application Streamlit

```bash
streamlit run app/main.py
```

L'application sera accessible sur http://localhost:8501

### Première utilisation

1. **Se connecter à Strava** : Page Settings → Connecter votre compte Strava
2. **Synchroniser les données** : Cliquez sur "Sync" pour récupérer vos activités
3. **Explorer** : Naviguez entre les différentes pages (Dashboard, Historique, Analytics, ML)

### Commandes utiles

```bash
# Réinitialiser la base de données (ATTENTION : efface toutes les données)
python scripts/init_db.py --drop

# Vérifier la connexion à la base
python scripts/init_db.py --check

# Lancer les tests
pytest tests/ -v

# Formater le code
black .
```

## Schéma de Base de Données

- **athletes** : Profil athlète (ID, nom, FTP, zones)
- **activities** : Activités Strava (distance, temps, métriques)
- **activity_streams** : Données temporelles détaillées (FC, puissance, cadence)
- **training_loads** : Historique CTL/ATL/TSB
- **training_zones** : Zones d'entraînement (FC, puissance, allure)
- **oauth_tokens** : Tokens d'accès Strava
- **sync_metadata** : État de synchronisation

## Métriques Calculées

### Training Stress Score (TSS)
Mesure de la charge d'entraînement d'une activité basée sur l'intensité et la durée.

### CTL (Chronic Training Load)
Moyenne mobile exponentielle sur 42 jours de votre charge d'entraînement. Représente votre **forme physique**.

### ATL (Acute Training Load)
Moyenne mobile exponentielle sur 7 jours de votre charge d'entraînement. Représente votre **fatigue**.

### TSB (Training Stress Balance)
Différence entre CTL et ATL (TSB = CTL - ATL). Représente votre **fraîcheur**.

- TSB < -30 : Très fatigué
- TSB -20 à -10 : Zone optimale d'entraînement
- TSB > 5 : Très frais / Risque de désentraînement

## Pages de l'Application

### 🏠 Dashboard
Vue d'ensemble de vos statistiques : distance totale, nombre d'activités, charge d'entraînement, activités récentes.

### 📊 Activity History
Historique complet de vos activités avec filtres, cartes interactives et profils d'élévation.

### 🎯 Training Analytics
Analyse approfondie : courbes CTL/ATL/TSB, distribution par zones, tendances de performance, volume d'entraînement.

### 🤖 ML Recommendations
Recommandations basées sur l'IA : prédictions de performance, suggestions d'entraînement, alertes de récupération.

### ⚙️ Settings
Configuration : connexion Strava, synchronisation, zones d'entraînement, profil athlète.

## Développement

### Structure du code

- **MVC Architecture** : Séparation modèles (database), vues (Streamlit), contrôleurs (utils)
- **SQLAlchemy ORM** : Abstraction de la base de données
- **Type hints** : Types Python pour meilleure maintenabilité
- **Logging structuré** : Traçabilité complète

### Ajouter une nouvelle page Streamlit

1. Créer `app/pages/X_🔹_Ma_Page.py`
2. Importer les composants nécessaires
3. Utiliser `st.session_state` pour l'état global
4. La page apparaîtra automatiquement dans la navigation

### Contribuer

1. Fork le projet
2. Créer une branche (`git checkout -b feature/ma-fonctionnalite`)
3. Commiter les changements (`git commit -m 'Ajout de ma fonctionnalité'`)
4. Pousser la branche (`git push origin feature/ma-fonctionnalite`)
5. Ouvrir une Pull Request

## Dépannage

### Erreur : "Required environment variable 'STRAVA_CLIENT_ID' is not set"

→ Vérifiez que votre fichier `.env` existe et contient vos credentials Strava.

### Erreur : "No module named 'stravalib'"

→ Installez les dépendances : `uv sync`

### La synchronisation échoue

→ Vérifiez que vos credentials Strava sont corrects et que vous avez autorisé l'application.

### Rate limit Strava

→ L'API Strava limite à 100 requêtes / 15 min et 1000 / jour. Attendez avant de re-synchroniser.

## Roadmap

- [x] Configuration et base de données
- [x] Modèles SQLAlchemy
- [x] Script d'initialisation
- [ ] Client Strava avec OAuth
- [ ] Synchronisation des données
- [ ] Interface Streamlit
- [ ] Calculs de métriques d'entraînement
- [ ] Modèles de machine learning
- [ ] Pages d'analyse avancée
- [ ] Tests unitaires

## Licence

MIT License

## Auteur

Créé avec ❤️ et Claude Code
