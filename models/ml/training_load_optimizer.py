"""Training load optimization model to suggest optimal training plans."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from scipy.optimize import minimize
from .base_model import BaseMLModel
from utils.logger import get_logger

logger = get_logger(__name__)


class TrainingLoadOptimizer(BaseMLModel):
    """
    Optimize training load to achieve fitness goals while avoiding overtraining.

    Uses constraint optimization to suggest weekly TSS distribution that:
    - Maximizes CTL growth toward target
    - Keeps TSB above -30 (avoid overtraining)
    - Maintains gradual CTL progression (avoid injury)
    """

    def __init__(self, model_dir: str = "models/ml/saved"):
        """
        Initialize training load optimizer.

        Args:
            model_dir: Directory to save/load models
        """
        model_name = "training_load_optimizer"
        super().__init__(model_name, model_dir)

        self.constraints_config = {
            'min_tsb': -30,  # Minimum TSB to avoid overtraining
            'max_tsb': 25,   # Maximum TSB (too fresh = losing fitness)
            'max_weekly_tss_increase': 50,  # Max TSS increase per week
            'max_ctl_ramp_rate': 8,  # Max CTL increase per week
            'min_recovery_days': 1,  # Min recovery days per week
        }

    def train(self, X: pd.DataFrame, y: pd.Series = None, **kwargs) -> Dict[str, Any]:
        """
        'Training' for optimizer means calibrating based on athlete's history.

        Args:
            X: Historical training load data (CTL, ATL, TSB, weekly TSS)
            y: Not used
            **kwargs: Additional parameters

        Returns:
            Dictionary with calibration metrics
        """
        logger.info("Calibrating training load optimizer")

        # Store feature names
        self.feature_names = list(X.columns)

        # Analyze athlete's training patterns
        athlete_profile = self._analyze_athlete_profile(X)

        self.metadata['athlete_profile'] = athlete_profile
        self.metadata['trained_at'] = pd.Timestamp.now().isoformat()

        # Adjust constraints based on athlete's history
        if athlete_profile['avg_weekly_tss'] > 0:
            # Set baseline as athlete's typical load
            self.constraints_config['baseline_weekly_tss'] = athlete_profile['avg_weekly_tss']

        # Set model to constraints config (this is not a traditional ML model)
        self.model = self.constraints_config

        logger.info(f"Calibration complete - Avg weekly TSS: {athlete_profile['avg_weekly_tss']:.0f}")

        return {'athlete_profile': athlete_profile}

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Not used - optimizer generates recommendations, not predictions.

        Args:
            X: Not used

        Returns:
            Empty array
        """
        return np.array([])

    def _calculate_metrics(self, y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
        """
        Not used for optimizer.

        Args:
            y_true: Not used
            y_pred: Not used

        Returns:
            Empty dict
        """
        return {}

    def _analyze_athlete_profile(self, training_load_history: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze athlete's training history to understand their patterns.

        Args:
            training_load_history: Historical CTL/ATL/TSB data

        Returns:
            Athlete profile dictionary
        """
        profile = {}

        if 'daily_tss' in training_load_history.columns:
            profile['avg_weekly_tss'] = training_load_history['daily_tss'].sum() / (len(training_load_history) / 7)
        else:
            profile['avg_weekly_tss'] = 0

        if 'ctl' in training_load_history.columns:
            profile['current_ctl'] = training_load_history['ctl'].iloc[-1] if len(training_load_history) > 0 else 0
            profile['max_ctl'] = training_load_history['ctl'].max()
            profile['avg_ctl'] = training_load_history['ctl'].mean()
        else:
            profile['current_ctl'] = 0
            profile['max_ctl'] = 0
            profile['avg_ctl'] = 0

        if 'atl' in training_load_history.columns:
            profile['current_atl'] = training_load_history['atl'].iloc[-1] if len(training_load_history) > 0 else 0
        else:
            profile['current_atl'] = 0

        if 'tsb' in training_load_history.columns:
            profile['current_tsb'] = training_load_history['tsb'].iloc[-1] if len(training_load_history) > 0 else 0
        else:
            profile['current_tsb'] = 0

        return profile

    def optimize_weekly_plan(self,
                            current_ctl: float,
                            current_atl: float,
                            target_ctl: float,
                            weeks_to_target: int,
                            constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate optimal weekly training plan to reach target CTL.

        Args:
            current_ctl: Current Chronic Training Load
            current_atl: Current Acute Training Load
            target_ctl: Target CTL to achieve
            weeks_to_target: Number of weeks to reach target
            constraints: Optional custom constraints

        Returns:
            Dictionary with recommended weekly TSS distribution
        """
        logger.info(f"Optimizing plan: Current CTL={current_ctl:.1f}, Target CTL={target_ctl:.1f}, Weeks={weeks_to_target}")

        # Use custom constraints or defaults
        config = self.constraints_config.copy()
        if constraints:
            config.update(constraints)

        # Calculate required CTL growth rate
        required_ctl_growth = (target_ctl - current_ctl) / weeks_to_target
        logger.info(f"Required CTL growth: {required_ctl_growth:.1f} per week")

        # Generate weekly recommendations
        weekly_plan = []
        ctl = current_ctl
        atl = current_atl

        for week in range(1, weeks_to_target + 1):
            # Calculate target CTL for this week
            week_target_ctl = current_ctl + (required_ctl_growth * week)

            # Optimize weekly TSS
            optimal_tss = self._optimize_week(
                current_ctl=ctl,
                current_atl=atl,
                target_ctl=week_target_ctl,
                config=config
            )

            # Simulate training load progression
            new_ctl = ctl * 0.86 + (optimal_tss * 7) * 0.14  # CTL = exponential moving average (42 days)
            new_atl = atl * 0.55 + (optimal_tss * 7) * 0.45  # ATL = exponential moving average (7 days)
            new_tsb = new_ctl - new_atl

            weekly_plan.append({
                'week': week,
                'recommended_weekly_tss': optimal_tss * 7,
                'daily_avg_tss': optimal_tss,
                'projected_ctl': new_ctl,
                'projected_atl': new_atl,
                'projected_tsb': new_tsb,
                'status': self._get_week_status(new_tsb, required_ctl_growth)
            })

            # Update for next week
            ctl = new_ctl
            atl = new_atl

        result = {
            'weekly_plan': weekly_plan,
            'summary': {
                'current_ctl': current_ctl,
                'target_ctl': target_ctl,
                'final_projected_ctl': ctl,
                'target_achieved': abs(ctl - target_ctl) < 5,
                'total_weeks': weeks_to_target,
                'avg_weekly_tss': np.mean([w['recommended_weekly_tss'] for w in weekly_plan]),
            }
        }

        return result

    def _optimize_week(self,
                      current_ctl: float,
                      current_atl: float,
                      target_ctl: float,
                      config: Dict[str, Any]) -> float:
        """
        Optimize TSS for a single week.

        Args:
            current_ctl: Current CTL
            current_atl: Current ATL
            target_ctl: Target CTL for this week
            config: Constraints configuration

        Returns:
            Optimal daily TSS
        """
        # Calculate TSS needed to reach target CTL
        # CTL_new = CTL_old * 0.86 + TSS_week * 0.14
        # Solving for TSS_week:
        tss_needed = (target_ctl - current_ctl * 0.86) / 0.14

        # Daily TSS
        daily_tss = tss_needed / 7

        # Apply constraints
        baseline_tss = config.get('baseline_weekly_tss', current_ctl)
        max_increase = config.get('max_weekly_tss_increase', 50)

        # Don't increase too quickly
        max_weekly_tss = baseline_tss + max_increase
        daily_tss = min(daily_tss, max_weekly_tss / 7)

        # Don't go negative
        daily_tss = max(daily_tss, 0)

        # Check TSB constraint
        projected_atl = current_atl * 0.55 + daily_tss * 7 * 0.45
        projected_ctl = current_ctl * 0.86 + daily_tss * 7 * 0.14
        projected_tsb = projected_ctl - projected_atl

        # If TSB too low, reduce load
        if projected_tsb < config['min_tsb']:
            # Reduce TSS to keep TSB above minimum
            daily_tss *= 0.8

        return daily_tss

    def _get_week_status(self, tsb: float, ctl_growth: float) -> str:
        """
        Get status message for a week based on TSB and CTL growth.

        Args:
            tsb: Training Stress Balance
            ctl_growth: CTL growth rate

        Returns:
            Status string
        """
        if tsb < -25:
            return "⚠️ Haute fatigue - Repos recommandé"
        elif tsb < -10:
            return "💪 Charge productive"
        elif tsb < 10:
            return "✅ Équilibre optimal"
        else:
            return "🔋 Frais - Augmenter charge possible"

    def suggest_recovery_week(self, current_ctl: float, current_atl: float) -> Dict[str, Any]:
        """
        Suggest a recovery week plan.

        Args:
            current_ctl: Current CTL
            current_atl: Current ATL

        Returns:
            Recovery week recommendations
        """
        # Recovery week: reduce load by 40-50%
        normal_weekly_tss = current_ctl * 7
        recovery_weekly_tss = normal_weekly_tss * 0.5

        # Simulate recovery week
        new_atl = current_atl * 0.55 + recovery_weekly_tss * 0.45
        new_ctl = current_ctl * 0.86 + recovery_weekly_tss * 0.14
        new_tsb = new_ctl - new_atl

        return {
            'recommended_weekly_tss': recovery_weekly_tss,
            'daily_avg_tss': recovery_weekly_tss / 7,
            'projected_ctl': new_ctl,
            'projected_atl': new_atl,
            'projected_tsb': new_tsb,
            'recommendation': '🔋 Semaine de récupération - Réduire le volume de 50%'
        }

    def check_overtraining_risk(self, training_load_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Check for overtraining risk based on recent training load.

        Args:
            training_load_df: Recent training load data (last 4 weeks)

        Returns:
            Risk assessment dictionary
        """
        if len(training_load_df) < 7:
            return {'risk_level': 'unknown', 'message': 'Données insuffisantes'}

        recent_data = training_load_df.tail(14)  # Last 2 weeks

        avg_tsb = recent_data['tsb'].mean() if 'tsb' in recent_data else 0
        ctl_trend = recent_data['ctl'].iloc[-1] - recent_data['ctl'].iloc[0] if 'ctl' in recent_data and len(recent_data) > 0 else 0

        # Risk assessment
        if avg_tsb < -30:
            risk_level = 'high'
            message = '🚨 Risque élevé de surentraînement - Repos urgent recommandé'
            recommendation = 'Prendre 3-5 jours de repos complet ou activités très légères'

        elif avg_tsb < -20:
            risk_level = 'moderate'
            message = '⚠️ Fatigue significative - Réduire la charge'
            recommendation = 'Semaine de récupération avec réduction de 40-50% du volume'

        elif avg_tsb < -10 and ctl_trend > 10:
            risk_level = 'moderate'
            message = '⚠️ Progression rapide - Surveiller les signes de fatigue'
            recommendation = 'Maintenir la charge actuelle, ne pas augmenter cette semaine'

        else:
            risk_level = 'low'
            message = '✅ Charge bien gérée'
            recommendation = 'Continuer l\'entraînement normalement'

        return {
            'risk_level': risk_level,
            'avg_tsb_2_weeks': avg_tsb,
            'ctl_trend': ctl_trend,
            'message': message,
            'recommendation': recommendation
        }
