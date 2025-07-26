#!/usr/bin/env python3
"""
Test script for the statistical alerts system
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from src.utils.statistical_alerts import statistical_analyzer, BreakoutEvent
from src.utils.notifications import notification_service

st.set_page_config(
    page_title="Statistical Alerts Test",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Statistical Alerts Test System")
st.markdown("Test and validate the statistical breakout detection system")

# Sidebar controls
with st.sidebar:
    st.header("🧪 Test Controls")
    
    # Data generation parameters
    st.subheader("Synthetic Data Generation")
    data_length = st.slider("Data Points", 50, 200, 168, help="Number of hourly data points (168 = 7 days)")
    noise_level = st.slider("Noise Level", 0.1, 5.0, 1.0, step=0.1, help="Amount of random noise")
    trend_strength = st.slider("Trend Strength", -2.0, 2.0, 0.5, step=0.1, help="Linear trend slope")
    
    # Breakout simulation
    st.subheader("Breakout Simulation")
    simulate_breakout = st.checkbox("Simulate Breakout", value=False)
    breakout_position = st.slider("Breakout Position", 0.5, 0.95, 0.9, help="Position of breakout (fraction of data)")
    breakout_magnitude = st.slider("Breakout Magnitude", 1.0, 10.0, 3.0, help="How many sigmas to break out")
    
    # Analyzer settings
    st.subheader("Analyzer Settings")
    sigma_threshold = st.slider("Sigma Threshold", 1.0, 4.0, 2.0, step=0.1)
    statistical_analyzer.set_sigma_threshold(sigma_threshold)

def generate_synthetic_data(length: int, noise: float, trend: float, 
                          simulate_breakout: bool = False, 
                          breakout_pos: float = 0.9, 
                          breakout_mag: float = 3.0) -> pd.Series:
    """Generate synthetic time series data for testing"""
    
    # Create time index
    start_time = datetime.now() - timedelta(hours=length)
    time_index = pd.date_range(start_time, periods=length, freq='1h')
    
    # Generate base trend
    x = np.arange(length)
    base_trend = trend * x
    
    # Add noise
    noise_component = np.random.normal(0, noise, length)
    
    # Combine base signal
    values = base_trend + noise_component + 50  # Add offset to keep positive
    
    # Simulate breakout if requested
    if simulate_breakout:
        breakout_index = int(length * breakout_pos)
        if breakout_index < length - 1:
            # Calculate what the normal range would be
            pre_breakout_data = values[:breakout_index]
            residuals = pre_breakout_data - np.polyval(np.polyfit(range(len(pre_breakout_data)), pre_breakout_data, 1), range(len(pre_breakout_data)))
            sigma = np.std(residuals)
            
            # Create breakout
            breakout_direction = 1 if np.random.random() > 0.5 else -1
            values[breakout_index:] += breakout_direction * breakout_mag * sigma
    
    return pd.Series(values, index=time_index)

def create_test_chart(data: pd.Series, regression_stats=None, title: str = "Test Data"):
    """Create a test chart with regression line and sigma boundaries"""
    fig = go.Figure()
    
    # Add data points
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data.values,
        mode='lines+markers',
        name='Data',
        line=dict(color='blue', width=2)
    ))
    
    if regression_stats is not None:
        # Add regression line
        time_numeric = np.arange(len(data))
        predicted = regression_stats.slope * time_numeric + regression_stats.intercept
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=predicted,
            mode='lines',
            name='Regression Line',
            line=dict(color='red', width=2, dash='dash')
        ))
        
        # Add sigma boundaries
        upper_bound, lower_bound = regression_stats.sigma_boundaries
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=upper_bound,
            mode='lines',
            name=f'+{statistical_analyzer.sigma_threshold}σ',
            line=dict(color='orange', width=1, dash='dot')
        ))
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=lower_bound,
            mode='lines',
            name=f'-{statistical_analyzer.sigma_threshold}σ',
            line=dict(color='orange', width=1, dash='dot'),
            fill='tonexty',
            fillcolor='rgba(255,165,0,0.1)'
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Value",
        height=400,
        hovermode='x unified'
    )
    
    return fig

# Main test interface
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📈 Synthetic Data Visualization")
    
    # Generate test data
    test_data = generate_synthetic_data(
        length=data_length,
        noise=noise_level,
        trend=trend_strength,
        simulate_breakout=simulate_breakout,
        breakout_pos=breakout_position,
        breakout_mag=breakout_magnitude
    )
    
    # Perform analysis
    regression_stats = statistical_analyzer.perform_lms_regression(test_data)
    
    # Create and display chart
    if regression_stats is not None:
        fig = create_test_chart(test_data, regression_stats, "Test Data with Statistical Analysis")
        st.plotly_chart(fig, use_container_width=True)
        
        # Display regression diagnostics
        st.subheader("📊 Regression Diagnostics")
        diag_cols = st.columns(4)
        
        with diag_cols[0]:
            st.metric("R²", f"{regression_stats.r_value**2:.3f}")
        with diag_cols[1]:
            st.metric("RMSE", f"{regression_stats.rmse:.2f}")
        with diag_cols[2]:
            st.metric("Normalized RMSE", f"{regression_stats.normalized_rmse:.3f}")
        with diag_cols[3]:
            st.metric("P-value", f"{regression_stats.p_value:.4f}")
    else:
        st.error("Failed to perform regression analysis")

with col2:
    st.subheader("🚨 Breakout Detection")
    
    # Test breakout detection
    if st.button("🔍 Test Breakout Detection"):
        statistical_analyzer.clear_state()  # Clear previous state
        
        # Simulate previous run (without breakout)
        if simulate_breakout:
            # Create data without breakout for "previous" state
            prev_data = generate_synthetic_data(
                length=data_length,
                noise=noise_level,
                trend=trend_strength,
                simulate_breakout=False
            )
            
            # Run analysis on previous data to establish baseline
            statistical_analyzer.detect_sigma_breakouts(prev_data, "test_series", "test_chart")
        
        # Now test with current data
        breakouts = statistical_analyzer.detect_sigma_breakouts(test_data, "test_series", "test_chart")
        
        if breakouts:
            st.success(f"🚨 {len(breakouts)} Breakout(s) Detected!")
            
            for i, breakout in enumerate(breakouts):
                st.write(f"**Breakout {i+1}:**")
                st.write(f"- Direction: {breakout.direction}")
                st.write(f"- Sigma Level: {breakout.sigma_level:.2f}σ")
                st.write(f"- Confidence: {breakout.confidence:.1f}%")
                st.write(f"- Current Value: {breakout.current_value:.2f}")
                st.write(f"- Expected Value: {breakout.expected_value:.2f}")
                
                # Send test notification
                if st.button(f"📨 Send Alert {i+1}", key=f"alert_{i}"):
                    notification_service.send_statistical_breakout_alert(breakout)
                    st.success("Test alert sent!")
        else:
            st.info("ℹ️ No breakouts detected")
    
    # Manual test alerts
    st.subheader("📨 Manual Test Alerts")
    
    if st.button("🧪 Test Statistical Alert"):
        # Create a mock breakout event
        mock_breakout = BreakoutEvent(
            series_name="Test Series",
            chart_type="trends",
            timestamp=datetime.now(),
            current_value=75.5,
            expected_value=68.2,
            sigma_level=2.3,
            direction="above",
            confidence=85.0
        )
        notification_service.send_statistical_breakout_alert(mock_breakout)
        st.success("Mock statistical alert sent!")
    
    if st.button("🚨 Test Multiple Breakouts"):
        mock_breakouts = [
            BreakoutEvent("BTC", "prices", datetime.now(), 45000, 43000, 2.1, "above", 90),
            BreakoutEvent("ETH", "prices", datetime.now(), 3200, 3000, 2.5, "above", 85),
            BreakoutEvent("Bitcoin", "trends", datetime.now(), 85, 75, 2.2, "above", 80)
        ]
        notification_service.send_multiple_breakouts_alert(mock_breakouts)
        st.success("Mock multiple breakouts alert sent!")

# Real-time testing section
st.markdown("---")
st.subheader("⏱️ Real-time Testing")

if st.checkbox("Enable Real-time Updates", value=False):
    # Auto-refresh for real-time testing
    placeholder = st.empty()
    
    import time
    for i in range(10):
        with placeholder.container():
            # Generate new data each time
            real_time_data = generate_synthetic_data(
                length=100,
                noise=np.random.uniform(0.5, 2.0),
                trend=np.random.uniform(-1, 1),
                simulate_breakout=np.random.random() > 0.7  # 30% chance of breakout
            )
            
            # Test for breakouts
            breakouts = statistical_analyzer.detect_sigma_breakouts(
                real_time_data, 
                f"realtime_test_{i}", 
                "test_chart"
            )
            
            st.write(f"**Update {i+1}/10** - Breakouts detected: {len(breakouts)}")
            
            if breakouts:
                for breakout in breakouts:
                    st.warning(f"🚨 Breakout: {breakout.sigma_level:.1f}σ {breakout.direction}")
        
        time.sleep(2)
    
    st.success("Real-time testing completed!")

# Statistics display
st.markdown("---")
st.subheader("📈 System Statistics")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Sigma Threshold", f"{statistical_analyzer.sigma_threshold:.1f}σ")

with col2:
    st.metric("Min Data Points", statistical_analyzer.min_data_points)

with col3:
    enabled_status = "✅ Enabled" if statistical_analyzer.enabled else "❌ Disabled"
    st.metric("Status", enabled_status)

st.markdown("---")
st.markdown("**💡 Testing Tips:**")
st.markdown("- Increase breakout magnitude to ensure detection")
st.markdown("- Lower sigma threshold for more sensitive detection")
st.markdown("- Use noise level ~1.0 for realistic market simulation")
st.markdown("- Enable breakout simulation and adjust position to test edge cases")
st.markdown("- Check browser console (F12) for detailed logs")