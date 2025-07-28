import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
import warnings
import os
from src.data.trends_fetcher import TrendsDataFetcher
from src.data.binance_fetcher import BinanceFetcher
from src.utils.config import Config
from src.utils.notifications import notification_service
from src.utils.statistical_alerts import statistical_analyzer

# Suppress FutureWarning from pytrends
warnings.filterwarnings('ignore', category=FutureWarning, module='pytrends')
pd.set_option('future.no_silent_downcasting', True)

st.set_page_config(
    page_title="Crypto Trends Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Create global cached instances for cache sharing across users
@st.cache_resource
def get_trends_fetcher():
    return TrendsDataFetcher()

@st.cache_resource  
def get_binance_fetcher():
    return BinanceFetcher()

def init_fetchers_v2():
    return get_trends_fetcher(), get_binance_fetcher()

def get_responsive_legend_config():
    """Get legend configuration for better mobile display"""
    # This config works well for both mobile and desktop
    # On mobile, the horizontal orientation prevents legend cutoff
    return {
        'orientation': 'h',  # horizontal orientation
        'yanchor': 'top',
        'y': -0.2,  # position below chart
        'xanchor': 'center',
        'x': 0.5,
        'bgcolor': 'rgba(0,0,0,0)',  # fully transparent background
        'bordercolor': 'rgba(0,0,0,0.2)',  # keep subtle border
        'borderwidth': 1
    }

def create_trends_chart(trends_df: pd.DataFrame, trends_alt_index: pd.Series = None, normalize=False):
    fig = go.Figure()
    
    # Only plot Bitcoin, Ethereum, and Cryptocurrency from the trends data
    key_trends = ['Bitcoin', 'Ethereum', 'Cryptocurrency']
    filtered_df = trends_df[[col for col in key_trends if col in trends_df.columns]]
    
    # Normalize each trend to its maximum value if requested
    if normalize:
        normalized_df = filtered_df.copy()
        for column in normalized_df.columns:
            max_val = normalized_df[column].max()
            if max_val > 0:
                normalized_df[column] = (normalized_df[column] / max_val) * 100
        data_to_plot = normalized_df
        y_title = "Normalized Interest (% of Peak)"
    else:
        data_to_plot = filtered_df
        y_title = "Search Interest (0-100)"
    
    # Plot the key trends
    for column in data_to_plot.columns:
        fig.add_trace(go.Scatter(
            x=data_to_plot.index,
            y=data_to_plot[column],
            mode='lines+markers',
            name=column,
            line=dict(width=2)
        ))
    
    # Add the Trends Alt Index if provided
    if trends_alt_index is not None and not trends_alt_index.empty:
        alt_data = trends_alt_index
        if normalize:
            max_val = alt_data.max()
            if max_val > 0:
                alt_data = (alt_data / max_val) * 100
        
        fig.add_trace(go.Scatter(
            x=alt_data.index,
            y=alt_data,
            mode='lines+markers',
            name='Trends Alt Index',
            line=dict(width=3, color='purple', dash='dash')
        ))
    
    fig.update_layout(
        title="Google Trends: Key Cryptos + Alt Index (7 Days, Hourly, Normalized)",
        xaxis_title="Date",
        yaxis_title=y_title,
        height=600,
        hovermode='x unified',
        legend=get_responsive_legend_config()
    )
    
    return fig

def create_price_chart(price_data: dict, alt_index: pd.DataFrame = None):
    """Create normalized price chart for BTC, ETH and Alt Index from Binance data"""
    fig = go.Figure()
    
    # Process BTC and ETH first
    main_symbols = ['BTC-USD', 'ETH-USD']
    for symbol in main_symbols:
        if symbol in price_data and not price_data[symbol].empty and 'price' in price_data[symbol].columns:
            df = price_data[symbol]
            # Normalize to percentage of first value
            normalized = (df['price'] / df['price'].iloc[0]) * 100
            
            fig.add_trace(go.Scatter(
                x=df.index,
                y=normalized,
                mode='lines',
                name=symbol.replace('-USD', ''),
                line=dict(width=2)
            ))
    
    # Add Alt Index if available
    if alt_index is not None and not alt_index.empty and 'price' in alt_index.columns:
        # Normalize to percentage of first value
        normalized_index = (alt_index['price'] / alt_index['price'].iloc[0]) * 100
        
        fig.add_trace(go.Scatter(
            x=alt_index.index,
            y=normalized_index,
            mode='lines',
            name='Alt Index (Next 8 Cryptos)',
            line=dict(width=3, dash='dash', color='purple')
        ))
    
    fig.update_layout(
        title="BTC, ETH & Alt Index Price Trends (7 Days, Hourly, Normalized to 100)",
        xaxis_title="Date",
        yaxis_title="Normalized Price (Base 100 = 7 days ago)",
        height=500,
        hovermode='x unified',
        legend=get_responsive_legend_config()
    )
    
    return fig

def create_futures_premium_chart(premiums_df: pd.DataFrame):
    """Create futures premium chart for BTC and ETH quarterly contracts"""
    fig = go.Figure()
    
    if premiums_df.empty:
        fig.add_annotation(
            text="No futures premium data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
    else:
        # Add premium lines for each contract
        btc_colors = ['orange', 'red']
        eth_colors = ['blue', 'purple']
        btc_count = 0
        eth_count = 0
        
        for column in premiums_df.columns:
            # Determine color based on contract type and order
            if 'BTC' in column:
                color = btc_colors[btc_count % len(btc_colors)]
                btc_count += 1
            else:  # ETH
                color = eth_colors[eth_count % len(eth_colors)]
                eth_count += 1
            
            fig.add_trace(go.Scatter(
                x=premiums_df.index,
                y=premiums_df[column],
                mode='lines',
                name=column,  # Use the clean display name from config
                line=dict(width=2, color=color)
            ))
    
    fig.update_layout(
        title="COIN-M Futures Premium (7 Days, Hourly)",
        xaxis_title="Date",
        yaxis_title="Premium (%)",
        height=500,
        hovermode='x unified',
        yaxis=dict(tickformat='.2f'),
        legend=get_responsive_legend_config()
    )
    
    return fig

def create_volume_chart(volume_df: pd.DataFrame):
    """Create normalized volume chart for BTC, ETH, Alt Index, and COIN-M futures"""
    fig = go.Figure()
    
    if volume_df.empty:
        fig.add_annotation(
            text="No volume data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
    else:
        # Define colors for different asset types
        colors = {
            'BTC-USD': 'orange',
            'ETH-USD': 'blue', 
            'Alt Index': 'purple',
            'BTC Sep 2025': 'coral',
            'BTC Dec 2025': 'red',
            'ETH Sep 2025': 'lightblue',
            'ETH Dec 2025': 'navy'
        }
        
        # Add normalized volume lines for each asset
        for column in volume_df.columns:
            if column in volume_df.columns and not volume_df[column].empty:
                # Normalize to percentage of first value (base 100)
                first_value = volume_df[column].iloc[0]
                if first_value > 0:
                    normalized_volume = (volume_df[column] / first_value) * 100
                else:
                    normalized_volume = volume_df[column]
                
                color = colors.get(column, 'gray')
                
                # Determine line style
                line_style = dict(width=3, color=color)
                if 'Sep' in column or 'Dec' in column:  # Futures contracts
                    line_style['dash'] = 'dash'
                
                fig.add_trace(go.Scatter(
                    x=volume_df.index,
                    y=normalized_volume,
                    mode='lines',
                    name=column,
                    line=line_style
                ))
    
    fig.update_layout(
        title="Trading Volume (7 Days, Hourly, Normalized to 100)",
        xaxis_title="Date",
        yaxis_title="Normalized Volume (Base 100 = 7 days ago)",
        height=500,
        hovermode='x unified',
        yaxis=dict(tickformat='.1f'),  # One decimal place for normalized values
        legend=get_responsive_legend_config()
    )
    
    return fig

def create_hf_volatility_chart(hf_vol_df: pd.DataFrame):
    """Create normalized high-frequency volatility chart for BTC and ETH"""
    fig = go.Figure()
    
    if hf_vol_df.empty:
        fig.add_annotation(
            text="No high-frequency volatility data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
    else:
        # Define colors for BTC and ETH
        colors = {'BTC': 'orange', 'ETH': 'blue'}
        
        # Add normalized volatility lines for each asset
        for column in hf_vol_df.columns:
            if column in hf_vol_df.columns and not hf_vol_df[column].empty:
                # Normalize to percentage of first value (base 100)
                first_value = hf_vol_df[column].iloc[0]
                if first_value > 0:
                    normalized_volatility = (hf_vol_df[column] / first_value) * 100
                else:
                    normalized_volatility = hf_vol_df[column]
                
                color = colors.get(column, 'gray')
                
                fig.add_trace(go.Scatter(
                    x=hf_vol_df.index,
                    y=normalized_volatility,
                    mode='lines',
                    name=f'{column} HF Volatility',
                    line=dict(width=2, color=color)
                ))
    
    fig.update_layout(
        title="High-Frequency Volatility (7 Days, Hourly, Normalized to 100)",
        xaxis_title="Date",
        yaxis_title="Normalized Volatility (Base 100 = 7 days ago)",
        height=500,
        hovermode='x unified',
        yaxis=dict(tickformat='.1f'),  # One decimal place for normalized values
        legend=get_responsive_legend_config()
    )
    
    return fig

def main():
    st.title("🔍 Crypto Trends Dashboard")
    st.markdown("Monitor Google search trends for cryptocurrency keywords to spot volatility patterns")
    
    # Initialize fetchers with environment-configured URLs
    trends_fetcher, binance_fetcher = init_fetchers_v2()
    
    with st.sidebar:
        st.header("⚙️ Settings")
        
        
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        refresh_interval = st.slider("Refresh interval (minutes)", 5, 30, 5, step=5) * 60  # Convert to seconds
        
        st.markdown("---")
        st.markdown("### 🔔 Notifications")
        
        notifications_enabled = st.checkbox("Enable Push Notifications", value=True)
        if notifications_enabled:
            notification_service.enable()
            
            # Request notification permission on first enable
            if st.button("🔐 Request Browser Permission"):
                notification_service.request_permission()
                st.info("Check your browser for notification permission request")
            
            # Statistical alerts configuration
            st.markdown("**📊 Statistical Alerts**")
            statistical_alerts_enabled = st.checkbox("Enable Statistical Breakout Alerts", value=True)
            
            if statistical_alerts_enabled:
                statistical_analyzer.enable()
                
                # Sigma threshold configuration
                sigma_threshold = st.slider(
                    "Sigma Threshold", 
                    min_value=1.0, 
                    max_value=4.0, 
                    value=2.0, 
                    step=0.1,
                    help="Number of standard deviations for breakout detection"
                )
                statistical_analyzer.set_sigma_threshold(sigma_threshold)
                
                # Display current settings
                st.caption(f"🎯 Alert when data crosses {sigma_threshold}σ boundary")
                
            else:
                statistical_analyzer.disable()
            
            # Test notification button
            if st.button("🧪 Test Notification"):
                notification_service.send_test_notification()
                st.success("Test notification sent!")
        else:
            notification_service.disable()
            statistical_analyzer.disable()
        
        st.markdown("---")
        st.markdown("### 📊 Tracked Keywords")
        for keyword in Config.TREND_KEYWORDS:
            st.markdown(f"- {keyword}")
        
        st.markdown("---")
        st.markdown("### 🔄 Last Update")
        last_update = st.empty()
    
    # Create tabs
    tab1, tab2 = st.tabs(["📈 Trends", "📊 KPIs"])
    
    with tab1:
        st.subheader("Cryptocurrency Search Interest (Normalized for Volatility Analysis)")
        st.markdown("Each keyword is normalized to its own peak value (100%) to compare relative volatility patterns.")
        trends_chart_placeholder = st.empty()
        
        st.markdown("---")
        
        st.subheader("Price Trends (Normalized)")
        st.markdown("BTC, ETH, and Alt Index (next 8 cryptos after BTC/ETH) normalized to 100 from 7 days ago to compare relative performance.")
        price_chart_placeholder = st.empty()
        
        st.markdown("---")
        
        st.subheader("COIN-M Futures Premium")
        st.markdown("Premium percentage for BTC and ETH quarterly futures contracts compared to spot prices.")
        futures_premium_placeholder = st.empty()
        
        st.markdown("---")
        
        st.subheader("Trading Volume (Normalized)")
        st.markdown("7-day hourly trading volume normalized to 100 from 7 days ago to compare relative volume changes across BTC, ETH, Alt Index, and COIN-M futures contracts.")
        volume_chart_placeholder = st.empty()
        
        st.markdown("---")
        
        st.subheader("High-Frequency Volatility (Normalized)")
        st.markdown("Intra-hour volatility calculated from 5-minute data using LMS regression detrending, normalized to 100 from 7 days ago to compare relative volatility changes.")
        hf_volatility_placeholder = st.empty()
    
    with tab2:
        st.subheader("Trend Momentum Analysis")
        st.markdown("Key performance indicators for each tracked cryptocurrency keyword.")
        momentum_placeholder = st.empty()
        
        st.markdown("---")
        
        st.subheader("Crypto Price Metrics")
        st.markdown("Current BTC, ETH, and Alt Index price metrics and performance indicators.")
        price_metrics_placeholder = st.empty()
        
        st.markdown("---")
        
        st.subheader("Futures Premium Metrics")
        st.markdown("Current premium metrics for BTC and ETH quarterly futures contracts.")
        premium_metrics_placeholder = st.empty()
        
        st.markdown("---")
        
        st.subheader("Volume Metrics")
        st.markdown("Current trading volume metrics for BTC, ETH, Alt Index, and COIN-M futures contracts.")
        volume_metrics_placeholder = st.empty()
    
    # Load historical price data from Binance
    @st.cache_data(ttl=Config.CACHE_TTL_SECONDS)
    def get_price_history():
        if Config.BINANCE_API_KEY:
            # Get BTC and ETH for main display
            main_symbols = ['BTC-USD', 'ETH-USD']
            # Alt coins for the index (next 8 after BTC/ETH by market cap)
            alt_symbols = ['BNB-USD', 'SOL-USD', 'XRP-USD', 'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'AVAX-USD', 'DOT-USD']
            all_symbols = main_symbols + alt_symbols
            return binance_fetcher.get_multiple_symbols_historical(all_symbols, days=7)
        else:
            st.warning("No Binance API key found. Please add BINANCE_API_KEY to your .env file")
            return {}
    
    # Calculate Alt Index (excluding BTC and ETH)
    @st.cache_data(ttl=Config.CACHE_TTL_SECONDS)
    def get_alt_index(price_history):
        if price_history:
            # Filter out BTC and ETH for Alt Index
            alt_data = {k: v for k, v in price_history.items() if k not in ['BTC-USD', 'ETH-USD']}
            return binance_fetcher.calculate_weighted_index(alt_data)
        return pd.DataFrame()
    
    # Get futures premiums
    @st.cache_data(ttl=Config.CACHE_TTL_SECONDS)
    def get_futures_premiums():
        if Config.BINANCE_API_KEY:
            return binance_fetcher.calculate_futures_premiums(days=7)
        else:
            return pd.DataFrame()
    
    # Get volume data
    @st.cache_data(ttl=Config.CACHE_TTL_SECONDS)
    def get_volume_data():
        if Config.BINANCE_API_KEY:
            return binance_fetcher.calculate_volume_data(days=7)
        else:
            return pd.DataFrame()
    
    # Get high-frequency volatility data
    @st.cache_data(ttl=Config.CACHE_TTL_SECONDS)
    def get_hf_volatility():
        if Config.BINANCE_API_KEY:
            return binance_fetcher.calculate_high_freq_volatility(days=7)
        else:
            return pd.DataFrame()
    
    while True:
        try:
            # Fetch trends data
            # Fetch Google Trends data with multiple batches to get all cryptos
            @st.cache_data(ttl=Config.CACHE_TTL_SECONDS)
            def get_trends_data():
                return trends_fetcher.get_multiple_trends_data([
                    Config.TREND_KEYWORDS_BATCH_1,
                    Config.TREND_KEYWORDS_BATCH_2
                ])
            
            trends_df = get_trends_data()
            
            # Calculate Trends Alt Index
            trends_alt_index = pd.Series()
            if not trends_df.empty:
                trends_alt_index = trends_fetcher.calculate_trends_alt_index(trends_df)
            
            # Get price data
            price_history = get_price_history()
            alt_index = get_alt_index(price_history)
            
            # Get futures premiums
            futures_premiums = get_futures_premiums()
            
            # Get volume data
            volume_data = get_volume_data()
            
            # Get high-frequency volatility data
            hf_volatility = get_hf_volatility()
            
            # Perform statistical analysis for breakout detection
            if notification_service.is_notification_enabled():
                try:
                    breakouts = statistical_analyzer.analyze_all_series(
                        trends_df=trends_df,
                        price_history=price_history,
                        alt_index=alt_index,
                        trends_alt_index=trends_alt_index,
                        futures_premiums=futures_premiums,
                        volume_data=volume_data,
                        hf_volatility=hf_volatility
                    )
                    
                    # Send individual breakout alerts
                    for breakout in breakouts:
                        notification_service.send_statistical_breakout_alert(breakout)
                    
                    # Send multiple breakout alert if many occurred simultaneously
                    if len(breakouts) >= 3:  # Alert if 3+ breakouts occur together
                        notification_service.send_multiple_breakouts_alert(breakouts)
                        
                except Exception as e:
                    print(f"Error in statistical analysis: {e}")
            
            if not trends_df.empty:
                # Main trends chart
                with trends_chart_placeholder.container():
                    fig = create_trends_chart(trends_df, trends_alt_index, normalize=True)
                    st.plotly_chart(fig, use_container_width=True, key=f"trends_chart_{int(time.time())}")
                
                # Price chart
                if price_history:
                    with price_chart_placeholder.container():
                        fig = create_price_chart(price_history, alt_index)
                        st.plotly_chart(fig, use_container_width=True, key=f"price_chart_{int(time.time())}")
                
                # Futures premium chart
                with futures_premium_placeholder.container():
                    fig = create_futures_premium_chart(futures_premiums)
                    st.plotly_chart(fig, use_container_width=True, key=f"futures_premium_chart_{int(time.time())}")
                
                # Volume chart
                with volume_chart_placeholder.container():
                    fig = create_volume_chart(volume_data)
                    st.plotly_chart(fig, use_container_width=True, key=f"volume_chart_{int(time.time())}")
                
                # High-frequency volatility chart
                with hf_volatility_placeholder.container():
                    fig = create_hf_volatility_chart(hf_volatility)
                    st.plotly_chart(fig, use_container_width=True, key=f"hf_volatility_chart_{int(time.time())}")
                
                # Momentum analysis for KPIs tab
                @st.cache_data(ttl=Config.CACHE_TTL_SECONDS)
                def get_momentum_data(df):
                    return trends_fetcher.calculate_trend_momentum(df)
                
                momentum_data = get_momentum_data(trends_df)
                
                # Check for significant trend changes and send alerts
                for keyword, data in momentum_data.items():
                    if abs(data['change_24h']) > 50:  # Alert on >50% change
                        notification_service.send_trend_alert(
                            keyword=keyword,
                            current_value=data['current'],
                            change_pct=data['change_24h']
                        )
                
                with momentum_placeholder.container():
                    momentum_df = pd.DataFrame(momentum_data).T
                    
                    # Add additional metrics
                    momentum_df['change_24h_pct'] = momentum_df['change_24h'].apply(lambda x: f"{x:.1f}%")
                    momentum_df['current_interest'] = momentum_df['current'].apply(lambda x: f"{x:.0f}")
                    momentum_df['avg_7d'] = momentum_df['average'].apply(lambda x: f"{x:.0f}")
                    momentum_df['peak_7d'] = momentum_df['max_7d'].apply(lambda x: f"{x:.0f}")
                    momentum_df['volatility'] = ((momentum_df['max_7d'] - momentum_df['min_7d']) / momentum_df['average'] * 100).apply(lambda x: f"{x:.1f}%")
                    momentum_df['trend'] = momentum_df['direction'].apply(lambda x: f"📈 {x}" if x == "up" else f"📉 {x}" if x == "down" else "➡️ neutral")
                    
                    # Create metrics columns
                    cols = st.columns(len(momentum_df))
                    for idx, (keyword, data) in enumerate(momentum_df.iterrows()):
                        with cols[idx]:
                            st.metric(
                                label=keyword,
                                value=data['current_interest'],
                                delta=data['change_24h_pct']
                            )
                    
                    # Show detailed table
                    st.dataframe(
                        momentum_df[['current_interest', 'change_24h_pct', 'avg_7d', 'peak_7d', 'volatility', 'trend']], 
                        use_container_width=True,
                        column_config={
                            "current_interest": "Current",
                            "change_24h_pct": "24h Change",
                            "avg_7d": "7d Average",
                            "peak_7d": "7d Peak",
                            "volatility": "Volatility",
                            "trend": "Direction"
                        }
                    )
                
                # Price metrics table
                if price_history:
                    with price_metrics_placeholder.container():
                        price_metrics_data = []
                        
                        # Process BTC and ETH first
                        main_symbols = ['BTC-USD', 'ETH-USD']
                        for symbol in main_symbols:
                            if symbol in price_history and not price_history[symbol].empty and 'price' in price_history[symbol].columns:
                                df = price_history[symbol]
                                current_price = df['price'].iloc[-1]
                                start_price = df['price'].iloc[0]
                                max_price = df['price'].max()
                                min_price = df['price'].min()
                                avg_price = df['price'].mean()
                                
                                # Calculate metrics
                                change_7d = ((current_price - start_price) / start_price) * 100
                                volatility = ((max_price - min_price) / avg_price) * 100
                                
                                # Send price alert for significant changes
                                if abs(change_7d) > 5:  # Alert on >5% 7-day change
                                    notification_service.send_price_alert(
                                        symbol=symbol.replace('-USD', ''),
                                        current_price=current_price,
                                        change_pct=change_7d
                                    )
                                
                                # Determine trend direction
                                recent_trend = df['price'].tail(24)  # Last 24 hours
                                if len(recent_trend) > 1:
                                    trend_change = recent_trend.iloc[-1] - recent_trend.iloc[0]
                                    trend_direction = "up" if trend_change > 0 else "down" if trend_change < 0 else "neutral"
                                else:
                                    trend_direction = "neutral"
                                
                                price_metrics_data.append({
                                    'Symbol': symbol.replace('-USD', ''),
                                    'Current Price': f"${current_price:,.2f}",
                                    '7d Change': f"{change_7d:+.1f}%",
                                    '7d High': f"${max_price:,.2f}",
                                    '7d Low': f"${min_price:,.2f}",
                                    '7d Average': f"${avg_price:,.2f}",
                                    'Volatility': f"{volatility:.1f}%",
                                    'Trend': f"📈 {trend_direction}" if trend_direction == "up" else f"📉 {trend_direction}" if trend_direction == "down" else "➡️ neutral"
                                })
                        
                        # Add Alt Index metrics
                        if not alt_index.empty and 'price' in alt_index.columns:
                            df = alt_index
                            current_price = df['price'].iloc[-1]
                            start_price = df['price'].iloc[0]
                            max_price = df['price'].max()
                            min_price = df['price'].min()
                            avg_price = df['price'].mean()
                            
                            # Calculate metrics
                            change_7d = ((current_price - start_price) / start_price) * 100
                            volatility = ((max_price - min_price) / avg_price) * 100
                            
                            # Determine trend direction
                            recent_trend = df['price'].tail(24)  # Last 24 hours
                            if len(recent_trend) > 1:
                                trend_change = recent_trend.iloc[-1] - recent_trend.iloc[0]
                                trend_direction = "up" if trend_change > 0 else "down" if trend_change < 0 else "neutral"
                            else:
                                trend_direction = "neutral"
                            
                            price_metrics_data.append({
                                'Symbol': 'ALT-INDEX',
                                'Current Price': f"${current_price:,.2f}",
                                '7d Change': f"{change_7d:+.1f}%",
                                '7d High': f"${max_price:,.2f}",
                                '7d Low': f"${min_price:,.2f}",
                                '7d Average': f"${avg_price:,.2f}",
                                'Volatility': f"{volatility:.1f}%",
                                'Trend': f"📈 {trend_direction}" if trend_direction == "up" else f"📉 {trend_direction}" if trend_direction == "down" else "➡️ neutral"
                            })
                        
                        if price_metrics_data:
                            # Create metrics columns
                            price_cols = st.columns(len(price_metrics_data))
                            for idx, data in enumerate(price_metrics_data):
                                with price_cols[idx]:
                                    label = data['Symbol'] if data['Symbol'] != 'ALT-INDEX' else 'Alt Index'
                                    st.metric(
                                        label=label,
                                        value=data['Current Price'],
                                        delta=data['7d Change']
                                    )
                            
                            # Show detailed table
                            price_df = pd.DataFrame(price_metrics_data)
                            st.dataframe(
                                price_df,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "Symbol": "Symbol",
                                    "Current Price": "Current",
                                    "7d Change": "7d Change",
                                    "7d High": "7d High",
                                    "7d Low": "7d Low",
                                    "7d Average": "7d Average",
                                    "Volatility": "Volatility",
                                    "Trend": "Direction"
                                }
                            )
                
                # Futures premium metrics table
                if not futures_premiums.empty:
                    with premium_metrics_placeholder.container():
                        premium_metrics_data = []
                        
                        for column in futures_premiums.columns:
                            premium_series = futures_premiums[column].dropna()
                            if not premium_series.empty:
                                current_premium = premium_series.iloc[-1]
                                start_premium = premium_series.iloc[0]
                                max_premium = premium_series.max()
                                min_premium = premium_series.min()
                                avg_premium = premium_series.mean()
                                
                                # Calculate metrics
                                change_7d = current_premium - start_premium
                                volatility = premium_series.std()
                                
                                # Determine trend direction
                                recent_trend = premium_series.tail(24)  # Last 24 hours
                                if len(recent_trend) > 1:
                                    trend_change = recent_trend.iloc[-1] - recent_trend.iloc[0]
                                    trend_direction = "up" if trend_change > 0.1 else "down" if trend_change < -0.1 else "neutral"
                                else:
                                    trend_direction = "neutral"
                                
                                premium_metrics_data.append({
                                    'Contract': column,
                                    'Current Premium': f"{current_premium:+.2f}%",
                                    '7d Change': f"{change_7d:+.2f}pp",
                                    '7d High': f"{max_premium:+.2f}%",
                                    '7d Low': f"{min_premium:+.2f}%",
                                    '7d Average': f"{avg_premium:+.2f}%",
                                    'Volatility': f"{volatility:.2f}pp",
                                    'Trend': f"📈 {trend_direction}" if trend_direction == "up" else f"📉 {trend_direction}" if trend_direction == "down" else "➡️ neutral"
                                })
                        
                        if premium_metrics_data:
                            # Create metrics columns
                            premium_cols = st.columns(len(premium_metrics_data))
                            for idx, data in enumerate(premium_metrics_data):
                                with premium_cols[idx]:
                                    contract_name = data['Contract'].replace(' 2025', '')
                                    st.metric(
                                        label=contract_name,
                                        value=data['Current Premium'],
                                        delta=data['7d Change']
                                    )
                            
                            # Show detailed table
                            premium_df = pd.DataFrame(premium_metrics_data)
                            st.dataframe(
                                premium_df,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "Contract": "Contract",
                                    "Current Premium": "Current",
                                    "7d Change": "7d Change",
                                    "7d High": "7d High",
                                    "7d Low": "7d Low",
                                    "7d Average": "7d Average",
                                    "Volatility": "Volatility",
                                    "Trend": "Direction"
                                }
                            )
                
                # Volume metrics table
                if not volume_data.empty:
                    with volume_metrics_placeholder.container():
                        volume_metrics_data = []
                        
                        for column in volume_data.columns:
                            volume_series = volume_data[column].dropna()
                            if not volume_series.empty:
                                current_volume = volume_series.iloc[-1]
                                start_volume = volume_series.iloc[0]
                                max_volume = volume_series.max()
                                min_volume = volume_series.min()
                                avg_volume = volume_series.mean()
                                
                                # Calculate metrics
                                if start_volume > 0:
                                    change_7d = ((current_volume - start_volume) / start_volume) * 100
                                else:
                                    change_7d = 0
                                
                                volatility = (volume_series.std() / avg_volume) * 100 if avg_volume > 0 else 0
                                
                                # Determine trend direction based on last 24 hours
                                recent_trend = volume_series.tail(24)  # Last 24 hours
                                if len(recent_trend) > 1:
                                    recent_start = recent_trend.iloc[0]
                                    recent_end = recent_trend.iloc[-1]
                                    if recent_start > 0:
                                        trend_change = ((recent_end - recent_start) / recent_start) * 100
                                        trend_direction = "up" if trend_change > 10 else "down" if trend_change < -10 else "neutral"
                                    else:
                                        trend_direction = "neutral"
                                else:
                                    trend_direction = "neutral"
                                
                                # Format volume numbers
                                def format_volume(vol):
                                    if vol >= 1_000_000:
                                        return f"{vol/1_000_000:.1f}M"
                                    elif vol >= 1_000:
                                        return f"{vol/1_000:.1f}K"
                                    else:
                                        return f"{vol:.1f}"
                                
                                volume_metrics_data.append({
                                    'Asset': column,
                                    'Current Volume': format_volume(current_volume),
                                    '7d Change': f"{change_7d:+.1f}%",
                                    '7d High': format_volume(max_volume),
                                    '7d Low': format_volume(min_volume),
                                    '7d Average': format_volume(avg_volume),
                                    'Volatility': f"{volatility:.1f}%",
                                    'Trend': f"📈 {trend_direction}" if trend_direction == "up" else f"📉 {trend_direction}" if trend_direction == "down" else "➡️ neutral"
                                })
                        
                        if volume_metrics_data:
                            # Create metrics columns
                            volume_cols = st.columns(min(len(volume_metrics_data), 4))  # Limit to 4 columns for readability
                            for idx, data in enumerate(volume_metrics_data[:4]):  # Show first 4 as metric cards
                                with volume_cols[idx]:
                                    asset_name = data['Asset'].replace(' 2025', '')
                                    st.metric(
                                        label=asset_name,
                                        value=data['Current Volume'],
                                        delta=data['7d Change']
                                    )
                            
                            # Show detailed table
                            volume_df = pd.DataFrame(volume_metrics_data)
                            st.dataframe(
                                volume_df,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "Asset": "Asset",
                                    "Current Volume": "Current",
                                    "7d Change": "7d Change",
                                    "7d High": "7d High",
                                    "7d Low": "7d Low",
                                    "7d Average": "7d Average",
                                    "Volatility": "Volatility",
                                    "Trend": "Direction"
                                }
                            )
            else:
                st.warning("⚠️ Unable to fetch Google Trends data. This may be due to rate limits. Please wait a few minutes and refresh.")
            
            # Update timestamp
            last_update.text(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            if not auto_refresh:
                break
            
            time.sleep(refresh_interval)
            
        except Exception as e:
            st.error(f"Error updating dashboard: {str(e)}")
            st.info("Retrying in 30 seconds...")
            time.sleep(30)

if __name__ == "__main__":
    main()