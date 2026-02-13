"""Training metrics calculations (TSS, CTL, ATL, TSB, Normalized Power, etc.)."""

import numpy as np
from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from utils.logger import get_logger

logger = get_logger(__name__)


class TrainingMetrics:
    """Calculator for training load and performance metrics."""

    # Exponential moving average time constants
    CTL_TIME_CONSTANT = 42  # Days for Chronic Training Load (fitness)
    ATL_TIME_CONSTANT = 7   # Days for Acute Training Load (fatigue)

    @staticmethod
    def calculate_tss_from_hr(
        duration_seconds: int,
        average_hr: float,
        threshold_hr: float,
        normalized: bool = False
    ) -> float:
        """
        Calculate Training Stress Score from heart rate data.

        TSS (HR) = (duration_hours * avg_hr * intensity_factor) / (threshold_hr * 3600) * 100

        Args:
            duration_seconds: Activity duration in seconds
            average_hr: Average heart rate
            threshold_hr: Lactate threshold heart rate
            normalized: If True, apply normalization factor

        Returns:
            Training Stress Score
        """
        if not threshold_hr or threshold_hr == 0:
            logger.warning("Threshold HR is 0, cannot calculate TSS")
            return 0.0

        duration_hours = duration_seconds / 3600.0
        intensity_factor = average_hr / threshold_hr

        # Heart rate based TSS formula
        tss = duration_hours * intensity_factor * intensity_factor * 100

        logger.debug(f"TSS from HR: duration={duration_hours:.2f}h, IF={intensity_factor:.2f}, TSS={tss:.1f}")
        return round(tss, 1)

    @staticmethod
    def calculate_tss_from_power(
        duration_seconds: int,
        normalized_power: float,
        ftp: int
    ) -> float:
        """
        Calculate Training Stress Score from power data.

        TSS = (duration_seconds * NP * IF) / (FTP * 3600) * 100
        where IF (Intensity Factor) = NP / FTP

        Args:
            duration_seconds: Activity duration in seconds
            normalized_power: Normalized Power (NP)
            ftp: Functional Threshold Power

        Returns:
            Training Stress Score
        """
        if not ftp or ftp == 0:
            logger.warning("FTP is 0, cannot calculate TSS")
            return 0.0

        duration_hours = duration_seconds / 3600.0
        intensity_factor = normalized_power / ftp

        tss = duration_hours * normalized_power * intensity_factor / ftp * 100

        logger.debug(f"TSS from power: duration={duration_hours:.2f}h, NP={normalized_power}, IF={intensity_factor:.2f}, TSS={tss:.1f}")
        return round(tss, 1)

    @staticmethod
    def calculate_normalized_power(power_data: List[float], sampling_interval: int = 1) -> float:
        """
        Calculate Normalized Power (NP) from power stream data.

        NP is a weighted average power that accounts for variability.
        Algorithm:
        1. Calculate 30-second rolling average
        2. Raise each value to 4th power
        3. Average these values
        4. Take 4th root

        Args:
            power_data: List of power values (watts)
            sampling_interval: Seconds between samples

        Returns:
            Normalized Power
        """
        if not power_data or len(power_data) < 30:
            return 0.0

        power_array = np.array(power_data)

        # Calculate 30-second rolling average
        window_size = 30 // sampling_interval
        if window_size < 1:
            window_size = 1

        rolling_avg = np.convolve(
            power_array,
            np.ones(window_size) / window_size,
            mode='valid'
        )

        # Raise to 4th power, average, and take 4th root
        np_value = np.power(np.mean(np.power(rolling_avg, 4)), 0.25)

        logger.debug(f"Normalized Power: {np_value:.1f}W from {len(power_data)} samples")
        return round(np_value, 1)

    @staticmethod
    def calculate_intensity_factor(normalized_power: float, ftp: int) -> float:
        """
        Calculate Intensity Factor (IF).

        IF = NP / FTP

        Args:
            normalized_power: Normalized Power
            ftp: Functional Threshold Power

        Returns:
            Intensity Factor
        """
        if not ftp or ftp == 0:
            return 0.0

        intensity_factor = normalized_power / ftp
        return round(intensity_factor, 3)

    @staticmethod
    def calculate_variability_index(normalized_power: float, average_power: float) -> float:
        """
        Calculate Variability Index (VI).

        VI = NP / Average Power

        A higher VI indicates more variable pacing.

        Args:
            normalized_power: Normalized Power
            average_power: Average power

        Returns:
            Variability Index
        """
        if not average_power or average_power == 0:
            return 0.0

        vi = normalized_power / average_power
        return round(vi, 3)

    @staticmethod
    def calculate_ctl(
        daily_tss_values: List[float],
        previous_ctl: float = 0.0
    ) -> float:
        """
        Calculate Chronic Training Load (CTL) - fitness.

        CTL is an exponential moving average with 42-day time constant.
        CTL_today = CTL_yesterday + (TSS_today - CTL_yesterday) / 42

        Args:
            daily_tss_values: List of daily TSS values (oldest to newest)
            previous_ctl: Previous CTL value to start from

        Returns:
            Current CTL value
        """
        ctl = previous_ctl

        for daily_tss in daily_tss_values:
            ctl = ctl + (daily_tss - ctl) / TrainingMetrics.CTL_TIME_CONSTANT

        return round(ctl, 2)

    @staticmethod
    def calculate_atl(
        daily_tss_values: List[float],
        previous_atl: float = 0.0
    ) -> float:
        """
        Calculate Acute Training Load (ATL) - fatigue.

        ATL is an exponential moving average with 7-day time constant.
        ATL_today = ATL_yesterday + (TSS_today - ATL_yesterday) / 7

        Args:
            daily_tss_values: List of daily TSS values (oldest to newest)
            previous_atl: Previous ATL value to start from

        Returns:
            Current ATL value
        """
        atl = previous_atl

        for daily_tss in daily_tss_values:
            atl = atl + (daily_tss - atl) / TrainingMetrics.ATL_TIME_CONSTANT

        return round(atl, 2)

    @staticmethod
    def calculate_tsb(ctl: float, atl: float) -> float:
        """
        Calculate Training Stress Balance (TSB) - form/freshness.

        TSB = CTL - ATL

        Interpretation:
        - TSB < -30: Very fatigued (overreaching)
        - TSB -20 to -10: Optimal training zone
        - TSB > 5: Fresh/rested (may lose fitness if prolonged)

        Args:
            ctl: Chronic Training Load
            atl: Acute Training Load

        Returns:
            Training Stress Balance
        """
        tsb = ctl - atl
        return round(tsb, 2)

    @staticmethod
    def calculate_ctl_ramp_rate(current_ctl: float, previous_ctl: float, days: int = 7) -> float:
        """
        Calculate CTL ramp rate (rate of fitness increase).

        Ramp rate = (Current_CTL - Previous_CTL) / days * 7

        Safe ramp rate is typically 5-8 CTL points per week.

        Args:
            current_ctl: Current CTL value
            previous_ctl: CTL value from 'days' ago
            days: Number of days between measurements

        Returns:
            CTL ramp rate per week
        """
        if days == 0:
            return 0.0

        ramp_rate = (current_ctl - previous_ctl) / days * 7
        return round(ramp_rate, 2)

    @staticmethod
    def calculate_time_in_zones(
        hr_data: List[float],
        zones: List[Dict[str, float]],
        sampling_interval: int = 1
    ) -> Dict[int, float]:
        """
        Calculate time spent in each training zone.

        Args:
            hr_data: List of heart rate values
            zones: List of zone definitions with 'min_value' and 'max_value'
            sampling_interval: Seconds between samples

        Returns:
            Dictionary mapping zone number to time in seconds
        """
        if not hr_data or not zones:
            return {}

        hr_array = np.array(hr_data)
        zone_times = {}

        for i, zone in enumerate(zones, start=1):
            # Count samples in this zone
            in_zone = (hr_array >= zone['min_value']) & (hr_array < zone['max_value'])
            time_in_zone = np.sum(in_zone) * sampling_interval
            zone_times[i] = time_in_zone

        logger.debug(f"Time in zones calculated: {zone_times}")
        return zone_times

    @staticmethod
    def estimate_vo2max_from_running(
        distance_meters: float,
        duration_seconds: int,
        age: int,
        weight_kg: float,
        sex: str = "M"
    ) -> float:
        """
        Estimate VO2max from running performance.

        Uses the Daniels' Running Formula approximation.

        Args:
            distance_meters: Distance covered
            duration_seconds: Time taken
            age: Athlete age
            weight_kg: Athlete weight in kg
            sex: "M" or "F"

        Returns:
            Estimated VO2max (ml/kg/min)
        """
        if duration_seconds == 0 or distance_meters == 0:
            return 0.0

        # Calculate velocity in meters/minute
        velocity = distance_meters / (duration_seconds / 60.0)

        # Simplified VO2max estimation
        # VO2 = -4.60 + 0.182258 * velocity + 0.000104 * velocity^2
        vo2 = -4.60 + 0.182258 * velocity + 0.000104 * (velocity ** 2)

        # Adjust for age (declines ~0.5% per year after 25)
        age_factor = 1.0 - max(0, (age - 25) * 0.005)
        vo2 = vo2 * age_factor

        # Gender adjustment (women typically 10% lower)
        if sex.upper() == "F":
            vo2 = vo2 * 0.9

        return round(vo2, 1)

    @staticmethod
    def calculate_running_effectiveness(
        distance_km: float,
        elevation_gain_m: float,
        duration_hours: float
    ) -> float:
        """
        Calculate running effectiveness score.

        Combines pace with elevation gain to assess performance.

        Args:
            distance_km: Distance in kilometers
            elevation_gain_m: Elevation gain in meters
            duration_hours: Duration in hours

        Returns:
            Effectiveness score (higher is better)
        """
        if duration_hours == 0:
            return 0.0

        # Adjusted distance accounting for elevation
        adjusted_distance = distance_km + (elevation_gain_m / 100.0)

        # Effectiveness = adjusted distance per hour
        effectiveness = adjusted_distance / duration_hours

        return round(effectiveness, 2)

    @staticmethod
    def estimate_ftp_from_activity(
        duration_seconds: int,
        average_power: float,
        normalized_power: float
    ) -> Optional[int]:
        """
        Estimate FTP from a maximal effort activity.

        Uses different estimation methods based on duration:
        - 5 min: FTP ≈ 0.93 * avg_power
        - 20 min: FTP ≈ 0.95 * avg_power
        - 60 min: FTP ≈ avg_power

        Args:
            duration_seconds: Activity duration
            average_power: Average power
            normalized_power: Normalized power

        Returns:
            Estimated FTP or None if duration not suitable
        """
        duration_minutes = duration_seconds / 60.0

        # Use normalized power if available, otherwise average
        power = normalized_power if normalized_power > 0 else average_power

        if not power or power == 0:
            return None

        # Estimation based on duration
        if 4 * 60 <= duration_minutes <= 6 * 60:
            # 5-minute test
            ftp = power * 0.93
        elif 18 * 60 <= duration_minutes <= 22 * 60:
            # 20-minute test (most common)
            ftp = power * 0.95
        elif 50 * 60 <= duration_minutes <= 70 * 60:
            # 1-hour test
            ftp = power * 1.0
        else:
            # Duration not suitable for FTP estimation
            return None

        return int(round(ftp))

    @staticmethod
    def calculate_efficiency_factor(
        normalized_power: float,
        average_hr: float
    ) -> float:
        """
        Calculate Efficiency Factor (EF).

        EF = NP / Average HR

        Higher EF indicates better aerobic efficiency.

        Args:
            normalized_power: Normalized Power
            average_hr: Average heart rate

        Returns:
            Efficiency Factor
        """
        if not average_hr or average_hr == 0:
            return 0.0

        ef = normalized_power / average_hr
        return round(ef, 3)


# Convenience functions

def calculate_activity_tss(
    activity: Dict[str, Any],
    athlete_ftp: Optional[int] = None,
    athlete_threshold_hr: Optional[int] = None
) -> float:
    """
    Calculate TSS for an activity using available data.

    Tries power data first, falls back to heart rate.

    Args:
        activity: Activity dictionary with metrics
        athlete_ftp: Athlete's FTP
        athlete_threshold_hr: Athlete's threshold heart rate

    Returns:
        Training Stress Score
    """
    metrics = TrainingMetrics()

    # Try power-based TSS first
    if activity.get("weighted_average_watts") and athlete_ftp:
        return metrics.calculate_tss_from_power(
            duration_seconds=activity.get("moving_time", 0),
            normalized_power=activity["weighted_average_watts"],
            ftp=athlete_ftp
        )

    # Fall back to heart rate-based TSS
    elif activity.get("average_heartrate") and athlete_threshold_hr:
        return metrics.calculate_tss_from_hr(
            duration_seconds=activity.get("moving_time", 0),
            average_hr=activity["average_heartrate"],
            threshold_hr=athlete_threshold_hr
        )

    # If no data available, estimate from duration and type
    else:
        # Simple estimation: 1 hour at moderate intensity ≈ 50-60 TSS
        duration_hours = activity.get("moving_time", 0) / 3600.0
        estimated_tss = duration_hours * 50  # Rough estimate

        logger.warning(f"Insufficient data for TSS calculation, using estimate: {estimated_tss:.1f}")
        return round(estimated_tss, 1)
