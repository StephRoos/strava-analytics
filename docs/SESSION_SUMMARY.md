# Session de Développement - Strava Analytics

**Date:** 13 février 2026
**Durée:** ~3 heures
**Commit:** 28ff70e

---

## 🎯 Objectif Initial

Créer une application web complète pour analyser les données Strava avec :
- Synchronisation des données via l'API Strava
- Stockage dans une base SQLite
- Interface Streamlit pour la visualisation
- Modèles ML pour optimiser les plans d'entraînement

---

## ✅ Réalisations

### 1. Backend (Base de données & API)

**7 tables SQLite créées :**
- `athletes` - Profil athlète
- `activities` - 551 activités synchronisées
- `activity_streams` - Données temporelles détaillées
- `training_loads` - Historique CTL/ATL/TSB
- `training_zones` - Zones d'entraînement
- `oauth_tokens` - Tokens Strava
- `sync_metadata` - État de synchronisation

**Intégration Strava :**
- OAuth 2.0 fonctionnel avec refresh automatique
- Synchronisation complète (full + incremental)
- Rate limiting respecté (100 req/15min)
- 551 activités synchronisées avec succès

### 2. Frontend (Streamlit)

**4 pages créées :**

#### Home (Page d'accueil)
- Vue d'ensemble de l'application
- Authentification OAuth Strava

#### 1_Dashboard
- KPIs globaux (distance, activités, temps)
- Graphique CTL/ATL/TSB
- Activités récentes
- Distribution par type

#### 2_Activity_History
- Tableau filtrable et paginé
- Cartes interactives (Folium)
- Vue détaillée par activité
- Export CSV

#### 3_Training_Analytics
- **Filtre par sport_type** (Run/TrailRun)
- Tendances de performance (allure, vitesse, FC)
- Analyse de volume hebdomadaire
- Distribution des activités

#### 5_Settings
- Synchronisation manuelle
- Infos athlète
- Stats base de données

**Interface :**
- Thème dark
- Menu caché (interface épurée)
- Sans emojis (compatible WSL)
- Contraste optimisé

### 3. Machine Learning

**3 modèles développés :**

#### Performance Predictor
- Prédiction d'allure course (min/km)
- Gradient Boosting Regressor
- **Entraîné sur 152 courses route uniquement** (trails exclus)
- RMSE : 0.505 min/km (amélioration de 39%)
- Features : distance, dénivelé, CTL, conditions
- Contraintes physiologiques appliquées

#### Activity Clusterer
- K-Means (5 clusters)
- Patterns identifiés :
  - Récupération (236 activités)
  - Intervalles (51 activités)
  - Endurance Longue (37 activités)
- Silhouette score : 0.465

#### Training Load Optimizer
- Optimisation CTL/ATL/TSB
- Planification multi-semaines
- Détection risque surentraînement
- Suggestions récupération

**Infrastructure ML :**
- Feature engineering (56 features)
- Scripts d'entraînement automatisés
- Modèles sauvegardés (.pkl)
- 2 notebooks Jupyter créés

### 4. Problèmes Résolus

**OAuth Strava :**
- Token response sans athlete data → Fetch séparé
- RelaxedActivityType → Conversion string
- Attributs optionnels → getattr()

**Modèle ML :**
- Prédictions aberrantes → Contraintes physiologiques
- Trails faussant les prédictions → Exclusion (sport_type)
- Courses courtes → Filtrage < 3km
- Scaler non sauvegardé → Modification save/load

**Interface :**
- Emojis (carrés blancs WSL) → Suppression complète
- Contraste faible → Retrait CSS stMetric
- Menu principal visible → Caché via CSS + config

---

## 📂 Structure Finale

```
strava-analytics/
├── app/
│   ├── Home.py                    # Page d'accueil
│   ├── auth/                      # OAuth Strava
│   ├── components/                # UI components
│   └── pages/
│       ├── 1_Dashboard.py
│       ├── 2_Activity_History.py
│       ├── 3_Training_Analytics.py
│       └── 5_Settings.py
├── config/
│   └── settings.py                # Configuration centralisée
├── models/
│   ├── database/                  # SQLAlchemy models
│   └── ml/                        # ML models
│       ├── base_model.py
│       ├── performance_predictor.py
│       ├── activity_clustering.py
│       └── training_load_optimizer.py
├── utils/
│   ├── strava_client.py          # API wrapper
│   ├── sync_manager.py           # Synchronisation
│   ├── training_metrics.py       # TSS, CTL, ATL
│   └── feature_engineering.py    # ML features
├── scripts/
│   ├── init_db.py               # Init database
│   └── train_models.py          # Train ML models
├── notebooks/                    # Jupyter notebooks
│   ├── ml_exploration.ipynb
│   ├── model_training.ipynb
│   └── README.md
├── data/
│   └── strava.db                # SQLite database
└── .streamlit/
    └── config.toml              # Streamlit config
```

---

## 🔧 Configuration

### Dépendances installées
```
streamlit, stravalib, sqlalchemy, pandas, plotly
scikit-learn, scipy, statsmodels, joblib
folium, streamlit-folium, polyline
jupyter, matplotlib, seaborn
```

### Variables d'environnement (.env)
```
STRAVA_CLIENT_ID=202151
STRAVA_CLIENT_SECRET=***
DATABASE_URL=sqlite:///./data/strava.db
```

---

## 📊 Statistiques

- **Lignes de code :** 4,120 insertions
- **Fichiers créés :** 17
- **Activités synchronisées :** 551
- **Sports disponibles :** 14 types
- **Modèles ML :** 3 entraînés
- **Accuracy prédictions :** RMSE 0.505 min/km

---

## 🚀 Commandes Utiles

### Lancer l'application
```bash
uv run streamlit run app/Home.py
```

### Entraîner les modèles ML
```bash
uv run python scripts/train_models.py
```

### Lancer Jupyter
```bash
uv run jupyter lab
```

### Initialiser la base de données
```bash
uv run python scripts/init_db.py
```

---

## 🎓 Apprentissages Clés

1. **OAuth Strava** : Token refresh automatique essentiel
2. **WSL + Emojis** : Incompatibilité → Suppression complète
3. **ML pour sport** : Importance de filtrer par type (trails vs route)
4. **Feature engineering** : Rolling stats cruciales pour prédictions
5. **Streamlit** : CSS custom pour interface épurée

---

## 📝 Prochaines Étapes Suggérées

1. **Dashboard** : Ajouter heatmap calendrier
2. **ML** : Développer dans notebooks Jupyter
3. **Export** : Ajouter export PDF des rapports
4. **Zones** : Implémenter zones FC/puissance
5. **Objectifs** : Système de suivi d'objectifs
6. **Social** : Comparaison avec amis Strava

---

## 🔗 Liens

- **Repository :** https://github.com/StephRoos/strava-analytics
- **Commit :** 28ff70e
- **Strava API :** https://developers.strava.com/
- **Application locale :** http://localhost:8501

---

**Session complétée avec succès !** 🎉
