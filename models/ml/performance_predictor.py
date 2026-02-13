"""Performance prediction model using gradient boosting."""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from .base_model import BaseMLModel
from utils.logger import get_logger

logger = get_logger(__name__)


class PerformancePredictor(BaseMLModel):
    """
    Predict performance metrics (pace/speed) based on conditions.

    Uses Gradient Boosting to predict:
    - Running pace (min/km)
    - Cycling speed (km/h)
    - Power output (watts)
    """

    def __init__(self, target_metric: str = 'pace', model_dir: str = "models/ml/saved"):
        """
        Initialize performance predictor.

        Args:
            target_metric: Metric to predict ('pace', 'speed', 'power')
            model_dir: Directory to save/load models
        """
        model_name = f"performance_predictor_{target_metric}"
        super().__init__(model_name, model_dir)

        self.target_metric = target_metric
        self.scaler = StandardScaler()
        self.metadata['target_metric'] = target_metric

    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> Dict[str, Any]:
        """
        Train the performance predictor.

        Args:
            X: Training features (distance, elevation, CTL, conditions, etc.)
            y: Target values (pace/speed/power)
            **kwargs: Additional parameters for GradientBoostingRegressor

        Returns:
            Dictionary with training metrics
        """
        logger.info(f"Training performance predictor for {self.target_metric}")
        logger.info(f"Training samples: {len(X)}, Features: {len(X.columns)}")

        # Store feature names
        self.feature_names = list(X.columns)

        # Remove rows with missing target
        mask = y.notna() & (y > 0)
        X_clean = X[mask].copy()
        y_clean = y[mask].copy()

        # Filter out very short activities (likely warmups/cooldowns) for pace prediction
        if self.target_metric == 'pace' and 'distance_km' in X_clean.columns:
            distance_mask = X_clean['distance_km'] >= 3.0  # Keep only runs >= 3km
            X_clean = X_clean[distance_mask]
            y_clean = y_clean[distance_mask]
            logger.info(f"Filtered short runs (< 3km): {(~distance_mask).sum()} removed")

        logger.info(f"After cleaning: {len(X_clean)} samples")

        if len(X_clean) < 50:
            raise ValueError(f"Insufficient data for training: {len(X_clean)} samples. Need at least 50.")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_clean, y_clean, test_size=0.2, random_state=42
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Default hyperparameters
        default_params = {
            'n_estimators': 100,
            'learning_rate': 0.1,
            'max_depth': 5,
            'min_samples_split': 10,
            'min_samples_leaf': 5,
            'random_state': 42,
            'loss': 'huber'  # Robust to outliers
        }
        default_params.update(kwargs)

        # Train model
        logger.info("Training Gradient Boosting Regressor...")
        self.model = GradientBoostingRegressor(**default_params)
        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        train_metrics = self._calculate_metrics(y_train, self.model.predict(X_train_scaled))
        test_metrics = self._calculate_metrics(y_test, self.model.predict(X_test_scaled))

        # Cross-validation
        cv_scores = cross_val_score(
            self.model, X_train_scaled, y_train,
            cv=5, scoring='neg_mean_squared_error'
        )
        cv_rmse = np.sqrt(-cv_scores.mean())

        # Store metrics
        self.metadata['metrics'] = {
            'train': train_metrics,
            'test': test_metrics,
            'cv_rmse': float(cv_rmse),
            'n_features': len(self.feature_names),
            'n_samples': len(X_clean)
        }
        self.metadata['trained_at'] = pd.Timestamp.now().isoformat()

        logger.info(f"Training complete - Test RMSE: {test_metrics['rmse']:.3f}, R²: {test_metrics['r2']:.3f}")

        return self.metadata['metrics']

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict performance metric.

        Args:
            X: Features for prediction

        Returns:
            Predicted values array
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # Prepare features
        X_prepared = self.prepare_features(X)

        # Scale
        X_scaled = self.scaler.transform(X_prepared)

        # Predict
        predictions = self.model.predict(X_scaled)

        return predictions

    def predict_with_confidence(self, X: pd.DataFrame, n_estimators: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict with confidence intervals using prediction intervals from trees.

        Args:
            X: Features for prediction
            n_estimators: Number of estimators to use (None = all)

        Returns:
            Tuple of (predictions, std_deviations)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        X_prepared = self.prepare_features(X)
        X_scaled = self.scaler.transform(X_prepared)

        # Get predictions from each tree stage
        predictions = []
        for i, estimator in enumerate(self.model.estimators_[:n_estimators]):
            pred = estimator[0].predict(X_scaled)
            predictions.append(pred)

        predictions = np.array(predictions)

        # Calculate mean and std
        mean_pred = predictions.mean(axis=0)
        std_pred = predictions.std(axis=0)

        return mean_pred, std_pred

    def _calculate_metrics(self, y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
        """
        Calculate regression metrics.

        Args:
            y_true: True values
            y_pred: Predicted values

        Returns:
            Dictionary with metrics
        """
        return {
            'rmse': float(np.sqrt(mean_squared_error(y_true, y_pred))),
            'mae': float(mean_absolute_error(y_true, y_pred)),
            'r2': float(r2_score(y_true, y_pred)),
            'mape': float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100)
        }

    def get_feature_importance_plot_data(self) -> pd.DataFrame:
        """
        Get feature importance data formatted for plotting.

        Returns:
            DataFrame with features and importance scores
        """
        importance_df = self.get_feature_importance()
        if importance_df is not None:
            # Get top 15 features
            return importance_df.head(15)
        return pd.DataFrame()

    def predict_scenario(self,
                        distance_km: float,
                        elevation_gain_m: float,
                        current_ctl: float,
                        activity_type: str = 'Run',
                        **additional_features) -> Dict[str, Any]:
        """
        Predict performance for a specific scenario.

        Args:
            distance_km: Distance in kilometers
            elevation_gain_m: Elevation gain in meters
            current_ctl: Current CTL (fitness level)
            activity_type: Type of activity
            **additional_features: Additional feature values

        Returns:
            Dictionary with prediction and details
        """
        # Build feature dict
        scenario = {
            'distance_km': distance_km,
            'elevation_gain_m': elevation_gain_m,
            'elevation_per_km': elevation_gain_m / distance_km if distance_km > 0 else 0,
            'ctl': current_ctl,
            'is_run': 1 if activity_type == 'Run' else 0,
            'is_ride': 1 if activity_type == 'Ride' else 0,
            'is_swim': 1 if activity_type == 'Swim' else 0,
        }

        # Add additional features
        scenario.update(additional_features)

        # Fill missing features with 0
        for feature in self.feature_names:
            if feature not in scenario:
                scenario[feature] = 0

        # Create DataFrame
        X = pd.DataFrame([scenario])

        # Predict
        prediction = self.predict(X)[0]

        # Apply physiological constraints for pace prediction
        if self.target_metric == 'pace' and distance_km > 0:
            # Base pace adjustment: longer distances = slower pace
            # Rule of thumb: +3% per doubling of distance beyond 10km
            if distance_km > 10:
                distance_factor = (distance_km / 10) ** 0.045  # ~3% per doubling
                prediction = prediction * distance_factor

            # Elevation adjustment: +1 sec/km per 10m elevation gain per km
            if elevation_gain_m > 0:
                elevation_per_km = elevation_gain_m / distance_km
                elevation_penalty = elevation_per_km / 10 * (1/60)  # Convert to minutes
                prediction += elevation_penalty

        # Get confidence if possible
        try:
            _, std = self.predict_with_confidence(X)
            confidence_interval = (prediction - 1.96 * std[0], prediction + 1.96 * std[0])
        except:
            confidence_interval = None

        result = {
            'prediction': float(prediction),
            'target_metric': self.target_metric,
            'confidence_interval': confidence_interval,
            'scenario': scenario,
            'note': 'Prédiction ajustée avec contraintes physiologiques' if self.target_metric == 'pace' else None
        }

        return result
