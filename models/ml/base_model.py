"""Base class for all machine learning models."""

from abc import ABC, abstractmethod
import joblib
import json
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseMLModel(ABC):
    """Abstract base class for machine learning models."""

    def __init__(self, model_name: str, model_dir: str = "models/ml/saved"):
        """
        Initialize base model.

        Args:
            model_name: Name of the model
            model_dir: Directory to save/load models
        """
        self.model_name = model_name
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.model = None
        self.feature_names = []
        self.metadata = {
            'model_name': model_name,
            'created_at': None,
            'trained_at': None,
            'version': '1.0.0',
            'metrics': {}
        }

    @abstractmethod
    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> Dict[str, Any]:
        """
        Train the model.

        Args:
            X: Training features
            y: Training target
            **kwargs: Additional training parameters

        Returns:
            Dictionary with training metrics
        """
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions.

        Args:
            X: Features for prediction

        Returns:
            Predictions array
        """
        pass

    def save(self, suffix: str = "") -> Path:
        """
        Save model to disk.

        Args:
            suffix: Optional suffix for filename

        Returns:
            Path to saved model
        """
        if self.model is None:
            raise ValueError("Model not trained yet. Call train() first.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.model_name}_{timestamp}{suffix}.pkl"
        model_path = self.model_dir / filename

        # Save entire object (includes model, scaler, and other attributes)
        save_dict = {
            'model': self.model,
            'feature_names': self.feature_names,
            'metadata': self.metadata
        }

        # Include scaler if it exists
        if hasattr(self, 'scaler'):
            save_dict['scaler'] = self.scaler

        # Include any other model-specific attributes
        if hasattr(self, 'cluster_labels'):
            save_dict['cluster_labels'] = self.cluster_labels
        if hasattr(self, 'cluster_profiles'):
            save_dict['cluster_profiles'] = self.cluster_profiles
        if hasattr(self, 'constraints_config'):
            save_dict['constraints_config'] = self.constraints_config

        joblib.dump(save_dict, model_path)

        # Save metadata separately for easy reading
        metadata_path = model_path.with_suffix('.json')
        self.metadata['saved_at'] = timestamp
        self.metadata['feature_names'] = self.feature_names

        with open(metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)

        logger.info(f"Model saved to {model_path}")
        logger.info(f"Metadata saved to {metadata_path}")

        return model_path

    def load(self, model_path: Optional[Path] = None) -> None:
        """
        Load model from disk.

        Args:
            model_path: Path to model file. If None, loads latest model.
        """
        if model_path is None:
            # Find latest model
            model_files = list(self.model_dir.glob(f"{self.model_name}_*.pkl"))
            if not model_files:
                raise FileNotFoundError(f"No saved models found for {self.model_name}")
            model_path = max(model_files, key=lambda p: p.stat().st_mtime)

        # Load saved dictionary
        saved_data = joblib.load(model_path)

        # Check if it's the new format (dict) or old format (just model)
        if isinstance(saved_data, dict):
            self.model = saved_data.get('model')
            self.feature_names = saved_data.get('feature_names', [])
            self.metadata = saved_data.get('metadata', {})

            # Restore scaler if present
            if 'scaler' in saved_data:
                self.scaler = saved_data['scaler']

            # Restore model-specific attributes
            if 'cluster_labels' in saved_data:
                self.cluster_labels = saved_data['cluster_labels']
            if 'cluster_profiles' in saved_data:
                self.cluster_profiles = saved_data['cluster_profiles']
            if 'constraints_config' in saved_data:
                self.constraints_config = saved_data['constraints_config']
        else:
            # Old format: just the model
            self.model = saved_data

        logger.info(f"Model loaded from {model_path}")

        # Load metadata from JSON file
        metadata_path = model_path.with_suffix('.json')
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata_json = json.load(f)
                # Merge with loaded metadata
                self.metadata.update(metadata_json)
                if 'feature_names' in metadata_json:
                    self.feature_names = metadata_json['feature_names']
            logger.info(f"Metadata loaded from {metadata_path}")

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """
        Evaluate model performance.

        Args:
            X: Test features
            y: Test target

        Returns:
            Dictionary with evaluation metrics
        """
        if self.model is None:
            raise ValueError("Model not trained yet. Call train() first.")

        predictions = self.predict(X)
        return self._calculate_metrics(y, predictions)

    @abstractmethod
    def _calculate_metrics(self, y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
        """
        Calculate evaluation metrics.

        Args:
            y_true: True values
            y_pred: Predicted values

        Returns:
            Dictionary with metrics
        """
        pass

    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """
        Get feature importance if available.

        Returns:
            DataFrame with feature names and importance scores, or None
        """
        if self.model is None:
            return None

        # Check if model has feature_importances_ attribute
        if hasattr(self.model, 'feature_importances_'):
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': self.model.feature_importances_
            })
            return importance_df.sort_values('importance', ascending=False)

        # Check if model has coef_ attribute (linear models)
        elif hasattr(self.model, 'coef_'):
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': np.abs(self.model.coef_)
            })
            return importance_df.sort_values('importance', ascending=False)

        return None

    def prepare_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for prediction (ensure correct columns).

        Args:
            X: Input features

        Returns:
            DataFrame with correct feature columns
        """
        if not self.feature_names:
            logger.warning("No feature names stored. Using all columns from X.")
            return X

        # Select only trained features
        missing_features = set(self.feature_names) - set(X.columns)
        if missing_features:
            logger.warning(f"Missing features: {missing_features}. Filling with 0.")
            for feature in missing_features:
                X[feature] = 0

        return X[self.feature_names]

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get model information.

        Returns:
            Dictionary with model metadata
        """
        info = self.metadata.copy()
        info['is_trained'] = self.model is not None
        info['n_features'] = len(self.feature_names)
        return info

    def __repr__(self) -> str:
        """String representation of model."""
        trained_status = "trained" if self.model is not None else "not trained"
        return f"{self.__class__.__name__}(name='{self.model_name}', status='{trained_status}')"
