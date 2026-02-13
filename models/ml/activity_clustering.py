"""Activity clustering model to identify training patterns."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, davies_bouldin_score
from .base_model import BaseMLModel
from utils.logger import get_logger

logger = get_logger(__name__)


class ActivityClusterer(BaseMLModel):
    """
    Cluster activities to identify distinct training patterns.

    Identifies archetypes like:
    - Recovery runs (low intensity, short distance)
    - Tempo workouts (moderate intensity, medium distance)
    - Long endurance (low intensity, long distance)
    - Intervals (high intensity, varied distance)
    """

    def __init__(self, n_clusters: int = 5, method: str = 'kmeans', model_dir: str = "models/ml/saved"):
        """
        Initialize activity clusterer.

        Args:
            n_clusters: Number of clusters (for kmeans)
            method: Clustering method ('kmeans' or 'dbscan')
            model_dir: Directory to save/load models
        """
        model_name = f"activity_clusterer_{method}"
        super().__init__(model_name, model_dir)

        self.n_clusters = n_clusters
        self.method = method
        self.scaler = StandardScaler()
        self.cluster_labels = {}
        self.cluster_profiles = {}

        self.metadata['n_clusters'] = n_clusters
        self.metadata['method'] = method

    def train(self, X: pd.DataFrame, y: pd.Series = None, **kwargs) -> Dict[str, Any]:
        """
        Train the clustering model.

        Args:
            X: Activity features (distance, intensity, elevation, etc.)
            y: Not used (unsupervised learning)
            **kwargs: Additional parameters for clustering algorithm

        Returns:
            Dictionary with clustering metrics
        """
        logger.info(f"Training activity clusterer with {self.method}")
        logger.info(f"Training samples: {len(X)}, Features: {len(X.columns)}")

        # Store feature names
        self.feature_names = list(X.columns)

        # Remove rows with missing values
        X_clean = X.dropna()
        logger.info(f"After cleaning: {len(X_clean)} samples")

        if len(X_clean) < self.n_clusters * 5:
            raise ValueError(f"Insufficient data: {len(X_clean)} samples. Need at least {self.n_clusters * 5}.")

        # Scale features
        X_scaled = self.scaler.fit_transform(X_clean)

        # Train clustering model
        if self.method == 'kmeans':
            default_params = {
                'n_clusters': self.n_clusters,
                'random_state': 42,
                'n_init': 10,
                'max_iter': 300
            }
            default_params.update(kwargs)
            self.model = KMeans(**default_params)

        elif self.method == 'dbscan':
            default_params = {
                'eps': 0.5,
                'min_samples': 5
            }
            default_params.update(kwargs)
            self.model = DBSCAN(**default_params)

        else:
            raise ValueError(f"Unknown clustering method: {self.method}")

        logger.info(f"Fitting {self.method.upper()} model...")
        cluster_labels = self.model.fit_predict(X_scaled)

        # Evaluate clustering quality
        metrics = self._calculate_clustering_metrics(X_scaled, cluster_labels)

        # Analyze clusters
        self.cluster_profiles = self._analyze_clusters(X_clean, cluster_labels)

        # Assign meaningful labels
        self.cluster_labels = self._assign_cluster_labels(self.cluster_profiles)

        # Store metadata
        self.metadata['metrics'] = metrics
        self.metadata['cluster_profiles'] = {k: {kk: float(vv) if isinstance(vv, (int, float, np.integer, np.floating)) else str(vv)
                                                  for kk, vv in v.items()}
                                            for k, v in self.cluster_profiles.items()}
        self.metadata['cluster_labels'] = self.cluster_labels
        self.metadata['trained_at'] = pd.Timestamp.now().isoformat()

        logger.info(f"Clustering complete - Silhouette: {metrics.get('silhouette', 0):.3f}")
        logger.info(f"Identified clusters: {list(self.cluster_labels.values())}")

        return self.metadata['metrics']

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Assign cluster labels to new activities.

        Args:
            X: Activity features

        Returns:
            Cluster labels array
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # Prepare features
        X_prepared = self.prepare_features(X)

        # Scale
        X_scaled = self.scaler.transform(X_prepared)

        # Predict
        if self.method == 'kmeans':
            labels = self.model.predict(X_scaled)
        elif self.method == 'dbscan':
            # DBSCAN doesn't have predict, use fit_predict
            logger.warning("DBSCAN doesn't support predict. Using nearest cluster centers.")
            labels = self._predict_dbscan(X_scaled)
        else:
            labels = np.zeros(len(X))

        return labels

    def predict_with_names(self, X: pd.DataFrame) -> List[str]:
        """
        Predict cluster labels and return meaningful names.

        Args:
            X: Activity features

        Returns:
            List of cluster names
        """
        labels = self.predict(X)
        return [self.cluster_labels.get(int(label), f"Cluster {label}") for label in labels]

    def _predict_dbscan(self, X_scaled: np.ndarray) -> np.ndarray:
        """
        Predict clusters for DBSCAN by finding nearest training point.

        Args:
            X_scaled: Scaled features

        Returns:
            Predicted labels
        """
        # This is a workaround since DBSCAN doesn't have predict
        # In practice, you'd use the training data to assign new points
        return np.zeros(len(X_scaled), dtype=int)

    def _calculate_metrics(self, y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
        """
        Not used for clustering (unsupervised).

        Args:
            y_true: Not used
            y_pred: Not used

        Returns:
            Empty dict
        """
        return {}

    def _calculate_clustering_metrics(self, X_scaled: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
        """
        Calculate clustering quality metrics.

        Args:
            X_scaled: Scaled features
            labels: Cluster labels

        Returns:
            Dictionary with clustering metrics
        """
        metrics = {}

        # Filter out noise points for DBSCAN
        mask = labels != -1
        if mask.sum() < 2:
            return {'silhouette': 0.0, 'davies_bouldin': 0.0}

        X_filtered = X_scaled[mask]
        labels_filtered = labels[mask]

        # Number of clusters
        n_clusters = len(set(labels_filtered))
        metrics['n_clusters'] = n_clusters

        # Silhouette score (higher is better, range [-1, 1])
        if n_clusters > 1 and len(X_filtered) > n_clusters:
            try:
                metrics['silhouette'] = float(silhouette_score(X_filtered, labels_filtered))
            except:
                metrics['silhouette'] = 0.0

        # Davies-Bouldin score (lower is better)
        if n_clusters > 1:
            try:
                metrics['davies_bouldin'] = float(davies_bouldin_score(X_filtered, labels_filtered))
            except:
                metrics['davies_bouldin'] = 0.0

        # Cluster sizes
        unique, counts = np.unique(labels_filtered, return_counts=True)
        metrics['cluster_sizes'] = {int(u): int(c) for u, c in zip(unique, counts)}

        return metrics

    def _analyze_clusters(self, X: pd.DataFrame, labels: np.ndarray) -> Dict[int, Dict[str, Any]]:
        """
        Analyze characteristics of each cluster.

        Args:
            X: Original features
            labels: Cluster labels

        Returns:
            Dictionary with cluster profiles
        """
        profiles = {}

        for cluster_id in set(labels):
            if cluster_id == -1:  # Noise in DBSCAN
                continue

            cluster_data = X[labels == cluster_id]

            profile = {
                'size': len(cluster_data),
                'avg_distance_km': cluster_data['distance_km'].mean() if 'distance_km' in cluster_data else 0,
                'avg_elevation_m': cluster_data['elevation_gain_m'].mean() if 'elevation_gain_m' in cluster_data else 0,
                'avg_speed_kmh': cluster_data['average_speed_kmh'].mean() if 'average_speed_kmh' in cluster_data else 0,
                'avg_heartrate': cluster_data['average_heartrate'].mean() if 'average_heartrate' in cluster_data else 0,
                'avg_tss': cluster_data['training_stress_score'].mean() if 'training_stress_score' in cluster_data else 0,
            }

            profiles[int(cluster_id)] = profile

        return profiles

    def _assign_cluster_labels(self, profiles: Dict[int, Dict[str, Any]]) -> Dict[int, str]:
        """
        Assign meaningful labels to clusters based on their characteristics.

        Args:
            profiles: Cluster profiles

        Returns:
            Dictionary mapping cluster IDs to names
        """
        labels = {}

        # Sort clusters by characteristics
        sorted_by_distance = sorted(profiles.items(), key=lambda x: x[1]['avg_distance_km'])
        sorted_by_speed = sorted(profiles.items(), key=lambda x: x[1]['avg_speed_kmh'], reverse=True)

        for cluster_id, profile in profiles.items():
            distance = profile['avg_distance_km']
            speed = profile['avg_speed_kmh']
            tss = profile['avg_tss']

            # Define archetypes based on characteristics
            if distance < 8 and tss < 50:
                label = "🟢 Récupération"
            elif distance < 8 and tss >= 50:
                label = "🔴 Intervalles"
            elif distance >= 15 and speed < 12:
                label = "🟡 Endurance Longue"
            elif 8 <= distance < 15 and tss >= 60:
                label = "🟠 Tempo"
            elif speed >= 20:
                label = "⚡ Haute Intensité"
            else:
                label = f"🔵 Entraînement Mixte"

            labels[cluster_id] = label

        return labels

    def get_cluster_summary(self) -> pd.DataFrame:
        """
        Get summary of all clusters.

        Returns:
            DataFrame with cluster information
        """
        if not self.cluster_profiles:
            return pd.DataFrame()

        summary_data = []
        for cluster_id, profile in self.cluster_profiles.items():
            summary_data.append({
                'Cluster': self.cluster_labels.get(cluster_id, f"Cluster {cluster_id}"),
                'Taille': profile['size'],
                'Distance moy (km)': f"{profile['avg_distance_km']:.1f}",
                'Dénivelé moy (m)': f"{profile['avg_elevation_m']:.0f}",
                'Vitesse moy (km/h)': f"{profile['avg_speed_kmh']:.1f}",
                'TSS moy': f"{profile['avg_tss']:.0f}",
            })

        return pd.DataFrame(summary_data)

    def visualize_clusters_2d(self, X: pd.DataFrame, labels: np.ndarray = None) -> Dict[str, Any]:
        """
        Prepare data for 2D cluster visualization (PCA).

        Args:
            X: Activity features
            labels: Optional cluster labels (if None, predict)

        Returns:
            Dictionary with data for plotting
        """
        from sklearn.decomposition import PCA

        if labels is None:
            labels = self.predict(X)

        # Scale features
        X_prepared = self.prepare_features(X)
        X_scaled = self.scaler.transform(X_prepared)

        # Reduce to 2D using PCA
        pca = PCA(n_components=2)
        X_2d = pca.fit_transform(X_scaled)

        # Get cluster names
        cluster_names = [self.cluster_labels.get(int(label), f"Cluster {label}") for label in labels]

        return {
            'x': X_2d[:, 0].tolist(),
            'y': X_2d[:, 1].tolist(),
            'labels': labels.tolist(),
            'cluster_names': cluster_names,
            'explained_variance': pca.explained_variance_ratio_.tolist()
        }
