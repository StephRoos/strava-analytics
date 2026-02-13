"""Script to train all ML models."""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from config.settings import get_database_session
from models import Activity, TrainingLoad
from utils.feature_engineering import FeatureEngineer
from models.ml.performance_predictor import PerformancePredictor
from models.ml.activity_clustering import ActivityClusterer
from models.ml.training_load_optimizer import TrainingLoadOptimizer
from utils.logger import get_logger

logger = get_logger(__name__)


def train_performance_predictor(athlete_id: int, min_activities: int = 50):
    """
    Train performance prediction models.

    Args:
        athlete_id: Athlete ID
        min_activities: Minimum activities required

    Returns:
        Dictionary with training results
    """
    logger.info("=" * 60)
    logger.info("Training Performance Predictor")
    logger.info("=" * 60)

    session = get_database_session()

    # Check data availability
    activity_count = session.query(Activity).filter_by(athlete_id=athlete_id).count()
    logger.info(f"Found {activity_count} activities")

    if activity_count < min_activities:
        logger.warning(f"Insufficient data: {activity_count} activities. Need at least {min_activities}.")
        session.close()
        return {'status': 'insufficient_data', 'activity_count': activity_count}

    # Feature engineering
    engineer = FeatureEngineer(session, athlete_id)

    # Load data from last 2 years
    start_date = datetime.now() - timedelta(days=730)
    features = engineer.prepare_dataset(start_date=start_date, include_training_loads=True)

    logger.info(f"Prepared {len(features)} samples with {len(features.columns)} features")

    results = {}

    # Train separate models for different activity types
    activity_types = [
        ('Run', 'average_pace_min_per_km'),
        ('Ride', 'average_speed_kmh'),
        ('Ride', 'average_watts')
    ]

    for activity_type, target_metric in activity_types:
        logger.info(f"\nTraining {activity_type} - {target_metric}")

        # Filter for activity type
        type_features = features[features['type'] == activity_type].copy()

        # For running pace: exclude trails (use only road/track runs)
        if activity_type == 'Run' and target_metric == 'average_pace_min_per_km' and 'sport_type' in type_features.columns:
            before_count = len(type_features)
            type_features = type_features[type_features['sport_type'] != 'TrailRun'].copy()
            trails_removed = before_count - len(type_features)
            if trails_removed > 0:
                logger.info(f"Excluded {trails_removed} trail runs (road/track only for pace prediction)")

        if len(type_features) < min_activities:
            logger.warning(f"Insufficient {activity_type} activities: {len(type_features)}")
            continue

        # Check if target exists
        if target_metric not in type_features.columns:
            logger.warning(f"Target {target_metric} not found in features")
            continue

        # Remove rows with missing target
        type_features = type_features[type_features[target_metric].notna()]
        type_features = type_features[type_features[target_metric] > 0]

        if len(type_features) < min_activities:
            logger.warning(f"Insufficient {activity_type} activities with {target_metric}: {len(type_features)}")
            continue

        # Select features for training
        feature_cols = [
            'distance_km', 'elevation_gain_m', 'elevation_per_km',
            'ctl', 'atl', 'tsb',
            'day_of_week', 'is_weekend', 'hour_of_day',
            'distance_km_mean_7d', 'distance_km_mean_30d',
            'tss_rolling_7d', 'tss_rolling_30d',
            'trainer'
        ]

        # Keep only existing features
        feature_cols = [col for col in feature_cols if col in type_features.columns]

        X = type_features[feature_cols]
        y = type_features[target_metric]

        # Train model
        metric_name = target_metric.split('_')[-1]
        if 'pace' in target_metric:
            metric_name = 'pace'
        elif 'speed' in target_metric:
            metric_name = 'speed'
        elif 'watts' in target_metric:
            metric_name = 'power'

        model = PerformancePredictor(target_metric=metric_name)

        try:
            metrics = model.train(X, y)

            # Save model
            model_path = model.save(suffix=f"_{activity_type.lower()}")

            results[f'{activity_type}_{metric_name}'] = {
                'status': 'success',
                'metrics': metrics,
                'model_path': str(model_path),
                'n_samples': len(X)
            }

            logger.info(f"✅ Model saved: {model_path}")

        except Exception as e:
            logger.error(f"❌ Training failed: {e}")
            results[f'{activity_type}_{metric_name}'] = {
                'status': 'failed',
                'error': str(e)
            }

    session.close()
    return results


def train_activity_clusterer(athlete_id: int, min_activities: int = 50):
    """
    Train activity clustering model.

    Args:
        athlete_id: Athlete ID
        min_activities: Minimum activities required

    Returns:
        Dictionary with training results
    """
    logger.info("=" * 60)
    logger.info("Training Activity Clusterer")
    logger.info("=" * 60)

    session = get_database_session()

    # Feature engineering
    engineer = FeatureEngineer(session, athlete_id)

    # Load data
    start_date = datetime.now() - timedelta(days=730)
    features = engineer.prepare_dataset(start_date=start_date, include_training_loads=False)

    logger.info(f"Prepared {len(features)} samples")

    if len(features) < min_activities:
        logger.warning(f"Insufficient data: {len(features)} activities")
        session.close()
        return {'status': 'insufficient_data'}

    # Select features for clustering
    cluster_features = [
        'distance_km', 'elevation_gain_m', 'average_speed_kmh',
        'moving_time_hours', 'training_stress_score',
        'average_heartrate', 'is_weekend'
    ]

    # Keep only existing features
    cluster_features = [col for col in cluster_features if col in features.columns]

    X = features[cluster_features]

    # Train model
    model = ActivityClusterer(n_clusters=5, method='kmeans')

    try:
        metrics = model.train(X)

        # Save model
        model_path = model.save()

        # Get cluster summary
        summary = model.get_cluster_summary()
        logger.info("\nCluster Summary:")
        logger.info(summary.to_string())

        result = {
            'status': 'success',
            'metrics': metrics,
            'model_path': str(model_path),
            'n_samples': len(X),
            'cluster_summary': summary.to_dict()
        }

        logger.info(f"✅ Model saved: {model_path}")

    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        result = {
            'status': 'failed',
            'error': str(e)
        }

    session.close()
    return result


def train_load_optimizer(athlete_id: int):
    """
    Train (calibrate) training load optimizer.

    Args:
        athlete_id: Athlete ID

    Returns:
        Dictionary with calibration results
    """
    logger.info("=" * 60)
    logger.info("Calibrating Training Load Optimizer")
    logger.info("=" * 60)

    session = get_database_session()

    # Load training loads
    training_loads = session.query(TrainingLoad).filter_by(
        athlete_id=athlete_id
    ).order_by(TrainingLoad.date).all()

    if len(training_loads) < 30:
        logger.warning(f"Insufficient training load data: {len(training_loads)} days")
        session.close()
        return {'status': 'insufficient_data'}

    # Convert to DataFrame
    load_data = []
    for load in training_loads:
        load_data.append({
            'date': load.date,
            'daily_tss': load.daily_tss or 0,
            'ctl': load.ctl or 0,
            'atl': load.atl or 0,
            'tsb': load.tsb or 0
        })

    import pandas as pd
    df = pd.DataFrame(load_data)

    # Calibrate optimizer
    optimizer = TrainingLoadOptimizer()

    try:
        result = optimizer.train(df)

        # Save model
        model_path = optimizer.save()

        result['status'] = 'success'
        result['model_path'] = str(model_path)

        logger.info(f"✅ Optimizer calibrated and saved: {model_path}")

    except Exception as e:
        logger.error(f"❌ Calibration failed: {e}")
        result = {
            'status': 'failed',
            'error': str(e)
        }

    session.close()
    return result


def main(athlete_id: int = None):
    """
    Train all ML models.

    Args:
        athlete_id: Athlete ID (if None, uses first athlete in DB)
    """
    logger.info("🤖 Starting ML Model Training Pipeline")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")

    session = get_database_session()

    # Get athlete ID
    if athlete_id is None:
        from models import Athlete
        athlete = session.query(Athlete).first()
        if not athlete:
            logger.error("No athlete found in database")
            session.close()
            return
        athlete_id = athlete.id
        logger.info(f"Using athlete: {athlete.username} (ID: {athlete_id})")

    session.close()

    results = {
        'athlete_id': athlete_id,
        'timestamp': datetime.now().isoformat(),
        'models': {}
    }

    # Train models
    try:
        # 1. Performance Predictor
        perf_results = train_performance_predictor(athlete_id, min_activities=50)
        results['models']['performance_predictor'] = perf_results

        # 2. Activity Clusterer
        cluster_results = train_activity_clusterer(athlete_id, min_activities=50)
        results['models']['activity_clusterer'] = cluster_results

        # 3. Training Load Optimizer
        optimizer_results = train_load_optimizer(athlete_id)
        results['models']['training_load_optimizer'] = optimizer_results

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        results['status'] = 'failed'
        results['error'] = str(e)
        return results

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Training Pipeline Complete")
    logger.info("=" * 60)

    for model_name, model_result in results['models'].items():
        status = model_result.get('status', 'unknown')
        logger.info(f"{model_name}: {status}")

    results['status'] = 'complete'
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Train ML models for Strava analytics')
    parser.add_argument('--athlete-id', type=int, help='Athlete ID to train models for')
    args = parser.parse_args()

    main(athlete_id=args.athlete_id)
