# Notebooks ML

Notebooks Jupyter pour développer et tester les modèles de Machine Learning.

## Notebooks disponibles

### 1. `ml_exploration.ipynb`
Exploration et analyse des modèles ML entraînés :
- Chargement des données
- Visualisation des features
- Test des prédictions
- Analyse des clusters
- Optimisation training load

### 2. `model_training.ipynb`
Entraînement des modèles :
- Performance Predictor (allure course)
- Activity Clusterer (patterns d'entraînement)
- Training Load Optimizer (planification)

## Démarrage

### Lancer Jupyter Lab

```bash
uv run jupyter lab
```

Ou Jupyter Notebook classique :

```bash
uv run jupyter notebook
```

### Utilisation

1. Ouvrir `ml_exploration.ipynb` pour commencer
2. Exécuter les cellules dans l'ordre
3. Modifier et expérimenter selon vos besoins

## Structure du projet ML

```
strava-analytics/
├── models/ml/               # Modèles ML
│   ├── base_model.py       # Classe de base
│   ├── performance_predictor.py
│   ├── activity_clustering.py
│   └── training_load_optimizer.py
├── models/ml/saved/        # Modèles entraînés (.pkl)
├── utils/
│   └── feature_engineering.py  # Extraction features
├── scripts/
│   └── train_models.py     # Script d'entraînement
└── notebooks/              # Ce dossier
    ├── ml_exploration.ipynb
    └── model_training.ipynb
```

## Exemples d'utilisation

### Charger un modèle entraîné

```python
from models.ml.performance_predictor import PerformancePredictor

predictor = PerformancePredictor(target_metric='pace')
predictor.load()  # Charge le dernier modèle

# Prédire
result = predictor.predict_scenario(
    distance_km=10,
    elevation_gain_m=100,
    current_ctl=50
)
print(f"Allure prédite: {result['prediction']:.2f} min/km")
```

### Entraîner un nouveau modèle

```python
from scripts.train_models import train_performance_predictor

results = train_performance_predictor(
    athlete_id=43145310,
    min_activities=50
)
print(results)
```

### Feature Engineering

```python
from utils.feature_engineering import FeatureEngineer
from config.settings import get_database_session

session = get_database_session()
engineer = FeatureEngineer(session, athlete_id=43145310)
features = engineer.prepare_dataset(include_training_loads=True)
print(features.shape)
```

## Notes

- Les modèles entraînés sont sauvegardés dans `models/ml/saved/`
- Les features incluent : distance, dénivelé, CTL/ATL/TSB, rolling stats, etc.
- Le Performance Predictor est entraîné **uniquement sur sorties route/piste** (trails exclus)
