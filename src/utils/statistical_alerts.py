import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from datetime import datetime
import warnings

warnings.filterwarnings('ignore', category=RuntimeWarning)


@dataclass
class BreakoutEvent:
    """Represents a statistical breakout event"""
    series_name: str
    chart_type: str
    timestamp: datetime
    current_value: float
    expected_value: float
    sigma_level: float
    direction: str  # 'above' or 'below'
    confidence: float


@dataclass
class RegressionStats:
    """Statistics from linear regression analysis"""
    slope: float
    intercept: float
    r_value: float
    p_value: float
    std_err: float
    rmse: float
    normalized_rmse: float
    residuals: np.ndarray
    sigma_boundaries: Tuple[np.ndarray, np.ndarray]  # (lower, upper)


class StatisticalAlertAnalyzer:
    """
    Analyzes time series data for statistical breakouts using LMS regression
    and 2-sigma boundary detection
    """
    
    def __init__(self, sigma_threshold: float = 2.0, min_data_points: int = 48):
        self.sigma_threshold = sigma_threshold
        self.min_data_points = min_data_points
        self.previous_states: Dict[str, Dict] = {}
        self.enabled = True
        
    def perform_lms_regression(self, data: pd.Series) -> Optional[RegressionStats]:
        """
        Perform Least Mean Squares linear regression on time series data
        
        Args:
            data: Time series data with datetime index
            
        Returns:
            RegressionStats object with regression analysis results
        """
        if len(data) < self.min_data_points:
            return None
            
        # Remove NaN values
        data_clean = data.dropna()
        if len(data_clean) < self.min_data_points:
            return None
            
        # Create numeric time index (hours since start)
        time_numeric = np.arange(len(data_clean))
        values = data_clean.values
        
        try:
            # Perform linear regression
            slope, intercept, r_value, p_value, std_err = stats.linregress(time_numeric, values)
            
            # Calculate predicted values
            predicted = slope * time_numeric + intercept
            
            # Calculate residuals
            residuals = values - predicted
            
            # Calculate RMSE
            rmse = np.sqrt(np.mean(residuals**2))
            
            # Calculate normalized RMSE (RMSE / mean of data)
            data_mean = np.mean(values)
            normalized_rmse = rmse / abs(data_mean) if abs(data_mean) > 1e-10 else rmse
            
            # Calculate sigma boundaries
            residual_std = np.std(residuals)
            upper_boundary = predicted + (self.sigma_threshold * residual_std)
            lower_boundary = predicted - (self.sigma_threshold * residual_std)
            
            return RegressionStats(
                slope=slope,
                intercept=intercept,
                r_value=r_value,
                p_value=p_value,
                std_err=std_err,
                rmse=rmse,
                normalized_rmse=normalized_rmse,
                residuals=residuals,
                sigma_boundaries=(lower_boundary, upper_boundary)
            )
            
        except Exception as e:
            print(f"Error in regression analysis: {e}")
            return None
    
    def calculate_sigma_level(self, value: float, expected: float, residual_std: float) -> float:
        """Calculate how many sigmas away a value is from the expected value"""
        if residual_std <= 1e-10:
            return 0.0
        return abs(value - expected) / residual_std
    
    def detect_sigma_breakouts(self, 
                             data: pd.Series, 
                             series_name: str, 
                             chart_type: str) -> List[BreakoutEvent]:
        """
        Detect statistical breakouts where data crosses 2-sigma boundaries
        
        Args:
            data: Time series data
            series_name: Name of the data series (e.g., 'BTC-USD', 'bitcoin')
            chart_type: Type of chart (e.g., 'prices', 'trends', 'volume')
            
        Returns:
            List of BreakoutEvent objects
        """
        breakouts = []
        
        # Perform regression analysis
        regression_stats = self.perform_lms_regression(data)
        if regression_stats is None:
            return breakouts
        
        data_clean = data.dropna()
        if len(data_clean) < 2:
            return breakouts
        
        # Get the last two data points for comparison
        current_value = data_clean.iloc[-1]
        previous_value = data_clean.iloc[-2] if len(data_clean) > 1 else current_value
        
        # Calculate expected values for last two points
        time_numeric = np.arange(len(data_clean))
        current_expected = regression_stats.slope * time_numeric[-1] + regression_stats.intercept
        previous_expected = regression_stats.slope * time_numeric[-2] + regression_stats.intercept if len(data_clean) > 1 else current_expected
        
        # Get sigma boundaries for current point
        residual_std = np.std(regression_stats.residuals)
        current_upper = current_expected + (self.sigma_threshold * residual_std)
        current_lower = current_expected - (self.sigma_threshold * residual_std)
        previous_upper = previous_expected + (self.sigma_threshold * residual_std)
        previous_lower = previous_expected - (self.sigma_threshold * residual_std)
        
        # Check if previous point was within boundaries
        previous_within = previous_lower <= previous_value <= previous_upper
        
        # Check if current point is outside boundaries
        current_outside_upper = current_value > current_upper
        current_outside_lower = current_value < current_lower
        
        # Generate breakout event if previous was within and current is outside
        if previous_within and (current_outside_upper or current_outside_lower):
            direction = 'above' if current_outside_upper else 'below'
            sigma_level = self.calculate_sigma_level(current_value, current_expected, residual_std)
            
            # Calculate confidence based on R-squared and significance
            confidence = min(100.0, abs(regression_stats.r_value) * 100 * (1 - regression_stats.p_value))
            
            breakout = BreakoutEvent(
                series_name=series_name,
                chart_type=chart_type,
                timestamp=data_clean.index[-1],
                current_value=current_value,
                expected_value=current_expected,
                sigma_level=sigma_level,
                direction=direction,
                confidence=confidence
            )
            
            breakouts.append(breakout)
        
        # Store current state for next iteration
        state_key = f"{chart_type}_{series_name}"
        self.previous_states[state_key] = {
            'timestamp': data_clean.index[-1],
            'value': current_value,
            'expected': current_expected,
            'within_boundaries': current_lower <= current_value <= current_upper,
            'regression_stats': regression_stats
        }
        
        return breakouts
    
    def analyze_all_series(self, 
                          trends_df: pd.DataFrame,
                          price_history: Dict[str, pd.DataFrame],
                          alt_index: pd.DataFrame,
                          trends_alt_index: pd.Series,
                          futures_premiums: pd.DataFrame,
                          volume_data: pd.DataFrame,
                          hf_volatility: pd.DataFrame) -> List[BreakoutEvent]:
        """
        Analyze all data series for statistical breakouts
        
        Returns:
            List of all detected breakout events
        """
        all_breakouts = []
        
        if not self.enabled:
            return all_breakouts
        
        # Analyze trends data
        if not trends_df.empty:
            for column in trends_df.columns:
                try:
                    breakouts = self.detect_sigma_breakouts(
                        trends_df[column], 
                        column, 
                        'trends'
                    )
                    all_breakouts.extend(breakouts)
                except Exception as e:
                    print(f"Error analyzing trends for {column}: {e}")
        
        # Analyze price data
        for symbol, data in price_history.items():
            if not data.empty and 'price' in data.columns:
                try:
                    breakouts = self.detect_sigma_breakouts(
                        data['price'], 
                        symbol, 
                        'prices'
                    )
                    all_breakouts.extend(breakouts)
                except Exception as e:
                    print(f"Error analyzing prices for {symbol}: {e}")
        
        # Analyze alt index (price-based)
        if not alt_index.empty and 'price' in alt_index.columns:
            try:
                breakouts = self.detect_sigma_breakouts(
                    alt_index['price'], 
                    'Price Alt Index', 
                    'prices'
                )
                all_breakouts.extend(breakouts)
            except Exception as e:
                print(f"Error analyzing price alt index: {e}")
        
        # Analyze trends alt index
        if trends_alt_index is not None and not trends_alt_index.empty:
            try:
                breakouts = self.detect_sigma_breakouts(
                    trends_alt_index, 
                    'Trends Alt Index', 
                    'trends'
                )
                all_breakouts.extend(breakouts)
            except Exception as e:
                print(f"Error analyzing trends alt index: {e}")
        
        # Analyze futures premiums
        if not futures_premiums.empty:
            for column in futures_premiums.columns:
                try:
                    breakouts = self.detect_sigma_breakouts(
                        futures_premiums[column], 
                        column, 
                        'futures_premiums'
                    )
                    all_breakouts.extend(breakouts)
                except Exception as e:
                    print(f"Error analyzing futures premiums for {column}: {e}")
        
        # Analyze volume data
        if not volume_data.empty:
            for column in volume_data.columns:
                try:
                    breakouts = self.detect_sigma_breakouts(
                        volume_data[column], 
                        column, 
                        'volume'
                    )
                    all_breakouts.extend(breakouts)
                except Exception as e:
                    print(f"Error analyzing volume for {column}: {e}")
        
        # Analyze high-frequency volatility
        if not hf_volatility.empty:
            for column in hf_volatility.columns:
                try:
                    breakouts = self.detect_sigma_breakouts(
                        hf_volatility[column], 
                        column, 
                        'hf_volatility'
                    )
                    all_breakouts.extend(breakouts)
                except Exception as e:
                    print(f"Error analyzing HF volatility for {column}: {e}")
        
        return all_breakouts
    
    def get_regression_diagnostics(self, data: pd.Series) -> Optional[Dict]:
        """Get detailed regression diagnostics for a data series"""
        regression_stats = self.perform_lms_regression(data)
        if regression_stats is None:
            return None
        
        return {
            'slope': regression_stats.slope,
            'intercept': regression_stats.intercept,
            'r_squared': regression_stats.r_value ** 2,
            'p_value': regression_stats.p_value,
            'rmse': regression_stats.rmse,
            'normalized_rmse': regression_stats.normalized_rmse,
            'sigma_threshold': self.sigma_threshold,
            'data_points': len(data.dropna())
        }
    
    def enable(self):
        """Enable statistical analysis"""
        self.enabled = True
    
    def disable(self):
        """Disable statistical analysis"""
        self.enabled = False
    
    def set_sigma_threshold(self, threshold: float):
        """Set the sigma threshold for breakout detection"""
        self.sigma_threshold = max(1.0, min(5.0, threshold))  # Clamp between 1 and 5
    
    def clear_state(self):
        """Clear all previous states (useful for testing)"""
        self.previous_states.clear()


# Global statistical analyzer instance
statistical_analyzer = StatisticalAlertAnalyzer()