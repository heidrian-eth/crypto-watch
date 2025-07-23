import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
import warnings
from src.data.trends_fetcher import TrendsDataFetcher
from src.data.binance_fetcher import BinanceFetcher
from src.utils.config import Config

# Suppress FutureWarning from pytrends
warnings.filterwarnings('ignore', category=FutureWarning, module='pytrends')
pd.set_option('future.no_silent_downcasting', True)

st.set_page_config(
    page_title="Crypto Trends Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_fetchers_v2():
    return TrendsDataFetcher(), BinanceFetcher()

def create_trends_chart(trends_df: pd.DataFrame, normalize=False):
    fig = go.Figure()
    
    # Normalize each trend to its maximum value if requested
    if normalize:
        normalized_df = trends_df.copy()
        for column in normalized_df.columns:
            max_val = normalized_df[column].max()
            if max_val > 0:
                normalized_df[column] = (normalized_df[column] / max_val) * 100
        data_to_plot = normalized_df
        y_title = "Normalized Interest (% of Peak)"
    else:
        data_to_plot = trends_df
        y_title = "Search Interest (0-100)"
    
    for column in data_to_plot.columns:
        fig.add_trace(go.Scatter(
            x=data_to_plot.index,
            y=data_to_plot[column],
            mode='lines+markers',
            name=column,
            line=dict(width=2)
        ))
    
    fig.update_layout(
        title="Google Trends Interest Over Time (7 Days, Hourly, Normalized)",
        xaxis_title="Date",
        yaxis_title=y_title,
        height=600,
        hovermode='x unified'
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
        hovermode='x unified'
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
        for column in premiums_df.columns:
            # Determine color based on contract
            if 'BTC' in column:
                color = 'orange' if 'Sep' in column else 'red'
            else:  # ETH
                color = 'blue' if 'Sep' in column else 'purple'
            
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
        yaxis=dict(tickformat='.2f')
    )
    
    return fig

def main():
    st.title("🔍 Crypto Trends Dashboard")
    st.markdown("Monitor Google search trends for cryptocurrency keywords to spot volatility patterns")
    
    trends_fetcher, binance_fetcher = init_fetchers_v2()
    
    with st.sidebar:
        st.header("⚙️ Settings")
        
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        refresh_interval = st.slider("Refresh interval (seconds)", 30, 300, 300)
        
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
    
    with tab2:
        st.subheader("Trend Momentum Analysis")
        st.markdown("Key performance indicators for each tracked cryptocurrency keyword.")
        momentum_placeholder = st.empty()
        
        st.markdown("---")
        
        st.subheader("Crypto Price Metrics")
        st.markdown("Current BTC, ETH, and Alt Index price metrics and performance indicators.")
        price_metrics_placeholder = st.empty()
    
    # Load historical price data from Binance
    @st.cache_data(ttl=300)  # Cache for 5 minutes
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
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_alt_index(price_history):
        if price_history:
            # Filter out BTC and ETH for Alt Index
            alt_data = {k: v for k, v in price_history.items() if k not in ['BTC-USD', 'ETH-USD']}
            return binance_fetcher.calculate_weighted_index(alt_data)
        return pd.DataFrame()
    
    # Get futures premiums
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_futures_premiums():
        if Config.BINANCE_API_KEY:
            return binance_fetcher.calculate_futures_premiums(days=7)
        else:
            return pd.DataFrame()
    
    while True:
        try:
            # Fetch trends data
            trends_df = trends_fetcher.get_trends_data(Config.TREND_KEYWORDS)
            
            # Get price data
            price_history = get_price_history()
            alt_index = get_alt_index(price_history)
            
            # Get futures premiums
            futures_premiums = get_futures_premiums()
            
            if not trends_df.empty:
                # Main trends chart
                with trends_chart_placeholder.container():
                    fig = create_trends_chart(trends_df, normalize=True)
                    st.plotly_chart(fig, use_container_width=True, key="main_trends_chart")
                
                # Price chart
                if price_history:
                    with price_chart_placeholder.container():
                        fig = create_price_chart(price_history, alt_index)
                        st.plotly_chart(fig, use_container_width=True, key="price_chart")
                
                # Futures premium chart
                with futures_premium_placeholder.container():
                    fig = create_futures_premium_chart(futures_premiums)
                    st.plotly_chart(fig, use_container_width=True, key="futures_premium_chart")
                
                # Momentum analysis for KPIs tab
                momentum_data = trends_fetcher.calculate_trend_momentum(trends_df)
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