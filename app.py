import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import warnings
from src.data.crypto_fetcher import CryptoDataFetcher
from src.data.trends_fetcher import TrendsDataFetcher
from src.data.simple_crypto_fetcher import SimpleCryptoFetcher
from src.data.binance_fetcher import BinanceFetcher
from src.utils.config import Config

# Suppress FutureWarning from pytrends
warnings.filterwarnings('ignore', category=FutureWarning, module='pytrends')
pd.set_option('future.no_silent_downcasting', True)

st.set_page_config(
    page_title="Crypto Watch Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_fetchers():
    return CryptoDataFetcher(), TrendsDataFetcher(), SimpleCryptoFetcher(), BinanceFetcher()

def create_price_chart(df: pd.DataFrame, title: str):
    fig = go.Figure()
    
    for _, row in df.iterrows():
        fig.add_trace(go.Bar(
            x=[row['symbol']],
            y=[row['price']],
            text=[f"${row['price']:.2f}"],
            textposition='auto',
            name=row['symbol'],
            marker_color='green' if row['change_24h'] > 0 else 'red'
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Symbol",
        yaxis_title="Price (USD)",
        showlegend=False,
        height=400
    )
    
    return fig

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
        title="Google Trends Interest Over Time (7 Days, Hourly)",
        xaxis_title="Date",
        yaxis_title=y_title,
        height=500,
        hovermode='x unified'
    )
    
    return fig

def create_weighted_index_chart(historical_data: list):
    if not historical_data:
        return go.Figure()
    
    df = pd.DataFrame(historical_data)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['weighted_avg_price'],
        mode='lines',
        name='Alt Index',
        line=dict(color='blue', width=3)
    ))
    
    fig.update_layout(
        title="Top 8 Crypto Alt Index",
        xaxis_title="Time",
        yaxis_title="Weighted Average Price (USD)",
        height=400
    )
    
    return fig

def main():
    st.title("🚀 Crypto Watch Dashboard")
    st.markdown("Monitor cryptocurrency prices and trends for optimal trading decisions")
    
    crypto_fetcher, trends_fetcher, simple_fetcher, binance_fetcher = init_fetchers()
    
    with st.sidebar:
        st.header("⚙️ Settings")
        
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        refresh_interval = st.slider("Refresh interval (seconds)", 30, 300, 60)
        
        st.markdown("---")
        st.markdown("### 📊 Data Sources")
        st.markdown("- **Prices**: Yahoo Finance & CoinGecko")
        st.markdown("- **Trends**: Google Trends")
        
        st.markdown("---")
        st.markdown("### 🔄 Last Update")
        last_update = st.empty()
    
    tab_summary, tab1, tab2, tab3, tab4 = st.tabs(["📊 Summary", "📈 Price Overview", "🔍 Google Trends", "💹 Market Analysis", "📊 Historical Data"])
    
    with tab_summary:
        st.subheader("7-Day Hourly Trends Summary")
        
        st.markdown("### Price Trends")
        price_summary_placeholder = st.empty()
        
        st.markdown("### Google Trends (Normalized)")
        trends_summary_placeholder = st.empty()
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Bitcoin & Ethereum Prices")
            price_placeholder = st.empty()
        
        with col2:
            st.subheader("Top 8 Crypto Alt Index")
            weighted_placeholder = st.empty()
        
        st.subheader("Top 8 Cryptocurrencies by Market Cap")
        top_cryptos_placeholder = st.empty()
    
    with tab2:
        st.subheader("Cryptocurrency Search Trends (7 Days)")
        trends_chart_placeholder = st.empty()
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Trend Momentum Analysis")
            momentum_placeholder = st.empty()
        
        with col2:
            st.subheader("Regional Interest")
            regional_placeholder = st.empty()
    
    with tab3:
        st.subheader("Market Metrics")
        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
        
        metric_placeholders = {
            'total_mcap': metrics_col1.empty(),
            'avg_change': metrics_col2.empty(),
            'top_gainer': metrics_col3.empty(),
            'top_loser': metrics_col4.empty()
        }
    
    with tab4:
        st.subheader("Historical Price Data")
        historical_symbol = st.selectbox("Select Symbol", ["BTC-USD", "ETH-USD"])
        historical_chart_placeholder = st.empty()
    
    weighted_history = []
    price_history_btc = []
    price_history_eth = []
    
    # Load real historical data from Binance
    st.info("📊 Loading 7 days of real hourly crypto data from Binance...")
    
    try:
        # Check if we have Binance API key
        if Config.BINANCE_API_KEY:
            symbols = ['BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD', 'XRP-USD', 'ADA-USD', 'DOGE-USD', 'MATIC-USD']
            historical_data = binance_fetcher.get_multiple_symbols_historical(symbols, days=7)
            weighted_index_history = binance_fetcher.calculate_weighted_index(historical_data)
            
            st.success(f"✅ Loaded 7 days of real hourly data from Binance for {len(historical_data)} cryptocurrencies!")
        else:
            # Fallback to simple data if no API key
            st.warning("⚠️ No Binance API key found, using simulated data")
            historical_df = simple_fetcher.get_historical_hourly_simple(hours=168)  # 7 days
            weighted_index_series = simple_fetcher.calculate_simple_weighted_index(historical_df)
            
            historical_data = {
                'BTC-USD': pd.DataFrame({'price': historical_df['BTC']}, index=historical_df.index),
                'ETH-USD': pd.DataFrame({'price': historical_df['ETH']}, index=historical_df.index)
            }
            weighted_index_history = pd.DataFrame({'price': weighted_index_series}, index=historical_df.index)
            st.success(f"✅ Loaded 7 days of simulated hourly data!")
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        # Final fallback
        historical_data = {}
        weighted_index_history = pd.DataFrame()
    
    while True:
        try:
            prices_df = crypto_fetcher.get_price_data(['BTC-USD', 'ETH-USD'])
            if not prices_df.empty:
                # Store price history for summary
                btc_row = prices_df[prices_df['symbol'] == 'BTC-USD']
                eth_row = prices_df[prices_df['symbol'] == 'ETH-USD']
                if not btc_row.empty:
                    price_history_btc.append({'timestamp': datetime.now(), 'price': btc_row['price'].iloc[0]})
                if not eth_row.empty:
                    price_history_eth.append({'timestamp': datetime.now(), 'price': eth_row['price'].iloc[0]})
                    
                # Keep last 168 data points (7 days * 24 hours)
                if len(price_history_btc) > 168:
                    price_history_btc = price_history_btc[-168:]
                if len(price_history_eth) > 168:
                    price_history_eth = price_history_eth[-168:]
                
                with price_placeholder.container():
                    fig = create_price_chart(prices_df, "Current Prices")
                    st.plotly_chart(fig, use_container_width=True, key="price_chart")
            
            top_cryptos_df = crypto_fetcher.get_top_cryptos_by_market_cap(Config.TOP_CRYPTOS_COUNT)
            if not top_cryptos_df.empty:
                weighted_avg = crypto_fetcher.calculate_weighted_average(top_cryptos_df)
                # Only add to history if the price is valid (greater than 0)
                try:
                    price_value = float(weighted_avg['weighted_avg_price'])
                    if price_value > 0:
                        weighted_history.append(weighted_avg)
                except (ValueError, TypeError):
                    # Skip if can't convert to float
                    pass
                
                if len(weighted_history) > 168:
                    weighted_history = weighted_history[-168:]
                
                with weighted_placeholder.container():
                    st.metric(
                        "Alt Index Price",
                        f"${weighted_avg['weighted_avg_price']:.2f}",
                        f"{weighted_avg['weighted_avg_change_24h']:.2f}%"
                    )
                    fig = create_weighted_index_chart(weighted_history)
                    st.plotly_chart(fig, use_container_width=True, key="weighted_chart")
                
                with top_cryptos_placeholder.container():
                    display_df = top_cryptos_df[['rank', 'symbol', 'name', 'price', 'market_cap', 'change_24h', 'volume_24h']].copy()
                    display_df['price'] = display_df['price'].apply(lambda x: f"${x:,.2f}")
                    display_df['market_cap'] = display_df['market_cap'].apply(lambda x: f"${x:,.0f}")
                    display_df['volume_24h'] = display_df['volume_24h'].apply(lambda x: f"${x:,.0f}")
                    display_df['change_24h'] = display_df['change_24h'].apply(lambda x: f"{x:.2f}%")
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                with metric_placeholders['total_mcap'].container():
                    st.metric("Total Market Cap", f"${weighted_avg['total_market_cap']:,.0f}")
                
                with metric_placeholders['avg_change'].container():
                    st.metric("Alt Index Change", f"{weighted_avg['weighted_avg_change_24h']:.2f}%")
                
                top_gainer = top_cryptos_df.loc[top_cryptos_df['change_24h'].idxmax()]
                with metric_placeholders['top_gainer'].container():
                    st.metric(f"Top Gainer ({top_gainer['symbol'].upper()})", f"{top_gainer['change_24h']:.2f}%")
                
                top_loser = top_cryptos_df.loc[top_cryptos_df['change_24h'].idxmin()]
                with metric_placeholders['top_loser'].container():
                    st.metric(f"Top Loser ({top_loser['symbol'].upper()})", f"{top_loser['change_24h']:.2f}%")
            
            # Fetch trends data with fewer keywords to avoid 400 error
            trends_df = trends_fetcher.get_trends_data(Config.TREND_KEYWORDS[:5])
            if not trends_df.empty:
                # Update summary dashboard
                with price_summary_placeholder.container():
                    fig = go.Figure()
                    chart_has_data = False
                    
                    # Normalize prices to percentage of their maximum
                    # Use historical data if available
                    if 'BTC-USD' in historical_data and not historical_data['BTC-USD'].empty:
                        btc_hist = historical_data['BTC-USD'].copy()
                        btc_max = btc_hist['price'].max()
                        if btc_max > 0:
                            btc_normalized = (btc_hist['price'] / btc_max) * 100
                        else:
                            btc_normalized = btc_hist['price']
                        fig.add_trace(go.Scatter(
                            x=btc_hist.index,
                            y=btc_normalized,
                            mode='lines',
                            name='BTC-USD',
                            line=dict(color='orange', width=2)
                        ))
                        chart_has_data = True
                    elif len(price_history_btc) > 1:
                        btc_df = pd.DataFrame(price_history_btc)
                        btc_max = btc_df['price'].max()
                        if btc_max > 0:
                            btc_df['normalized'] = (btc_df['price'] / btc_max) * 100
                        else:
                            btc_df['normalized'] = btc_df['price']
                        fig.add_trace(go.Scatter(
                            x=btc_df['timestamp'],
                            y=btc_df['normalized'],
                            mode='lines',
                            name='BTC-USD',
                            line=dict(color='orange', width=2)
                        ))
                        chart_has_data = True
                    
                    if 'ETH-USD' in historical_data and not historical_data['ETH-USD'].empty:
                        eth_hist = historical_data['ETH-USD'].copy()
                        eth_max = eth_hist['price'].max()
                        if eth_max > 0:
                            eth_normalized = (eth_hist['price'] / eth_max) * 100
                        else:
                            eth_normalized = eth_hist['price']
                        fig.add_trace(go.Scatter(
                            x=eth_hist.index,
                            y=eth_normalized,
                            mode='lines',
                            name='ETH-USD',
                            line=dict(color='blue', width=2)
                        ))
                    elif len(price_history_eth) > 1:
                        eth_df = pd.DataFrame(price_history_eth)
                        eth_max = eth_df['price'].max()
                        if eth_max > 0:
                            eth_df['normalized'] = (eth_df['price'] / eth_max) * 100
                        else:
                            eth_df['normalized'] = eth_df['price']
                        fig.add_trace(go.Scatter(
                            x=eth_df['timestamp'],
                            y=eth_df['normalized'],
                            mode='lines',
                            name='ETH-USD',
                            line=dict(color='blue', width=2)
                        ))
                    
                    if not weighted_index_history.empty:
                        weighted_max = weighted_index_history['price'].max()
                        if weighted_max > 0:
                            weighted_normalized = (weighted_index_history['price'] / weighted_max) * 100
                        else:
                            weighted_normalized = weighted_index_history['price']
                        fig.add_trace(go.Scatter(
                            x=weighted_index_history.index,
                            y=weighted_normalized,
                            mode='lines',
                            name='Alt Index',
                            line=dict(color='green', width=2, dash='dash')
                        ))
                    elif len(weighted_history) > 1:
                        weighted_df = pd.DataFrame(weighted_history)
                        # Filter out zero values which can occur during initialization
                        try:
                            weighted_df['weighted_avg_price'] = pd.to_numeric(weighted_df['weighted_avg_price'], errors='coerce')
                            weighted_df = weighted_df[weighted_df['weighted_avg_price'] > 0]
                        except:
                            # If conversion fails, skip filtering
                            pass
                        
                        if not weighted_df.empty:
                            weighted_max = weighted_df['weighted_avg_price'].max()
                            if weighted_max > 0:
                                weighted_df['normalized'] = (weighted_df['weighted_avg_price'] / weighted_max) * 100
                            else:
                                weighted_df['normalized'] = weighted_df['weighted_avg_price']
                            fig.add_trace(go.Scatter(
                                x=weighted_df['timestamp'],
                                y=weighted_df['normalized'],
                                mode='lines',
                                name='Alt Index',
                                line=dict(color='green', width=2, dash='dash')
                            ))
                            chart_has_data = True
                    
                    fig.update_layout(
                        title="Price Trends (7 Days, Hourly, Normalized)",
                        xaxis_title="Time",
                        yaxis=dict(title="Normalized Price (% of Peak)", side="left"),
                        height=400,
                        hovermode='x unified'
                    )
                    
                    if chart_has_data:
                        st.plotly_chart(fig, use_container_width=True, key="summary_price_chart")
                    else:
                        st.info("📈 Price charts will appear here as data accumulates. Check back in a few minutes!")
                
                with trends_summary_placeholder.container():
                    # Show full 7 days of normalized trends
                    fig = create_trends_chart(trends_df, normalize=True)
                    fig.update_layout(title="Google Trends (7 Days, Hourly, Normalized)", height=400)
                    st.plotly_chart(fig, use_container_width=True, key="summary_trends_chart")
                
                with trends_chart_placeholder.container():
                    # Show normalized trends for volatility analysis
                    fig = create_trends_chart(trends_df, normalize=True)
                    st.plotly_chart(fig, use_container_width=True, key="trends_chart")
                
                momentum_data = trends_fetcher.calculate_trend_momentum(trends_df)
                with momentum_placeholder.container():
                    momentum_df = pd.DataFrame(momentum_data).T
                    momentum_df['change_24h'] = momentum_df['change_24h'].apply(lambda x: f"{x:.1f}%")
                    momentum_df['current'] = momentum_df['current'].apply(lambda x: f"{x:.0f}")
                    st.dataframe(momentum_df[['current', 'change_24h', 'direction']], use_container_width=True)
                
                regional_data = trends_fetcher.get_regional_interest(Config.TREND_KEYWORDS[:2])
                if regional_data and 'by_region' in regional_data:
                    with regional_placeholder.container():
                        top_regions = regional_data['by_region'].sum(axis=1).nlargest(10)
                        fig = px.bar(
                            x=top_regions.values,
                            y=top_regions.index,
                            orientation='h',
                            title="Top 10 Regions by Interest"
                        )
                        st.plotly_chart(fig, use_container_width=True, key="regional_chart")
            
            historical_df = crypto_fetcher.get_historical_data(historical_symbol, days=7)
            if not historical_df.empty:
                with historical_chart_placeholder.container():
                    fig = go.Figure()
                    # Use line chart for historical data
                    fig.add_trace(go.Scatter(
                        x=historical_df['Date'],
                        y=historical_df['Close'],
                        mode='lines',
                        name=historical_symbol,
                        line=dict(color='blue', width=2)
                    ))
                    fig.update_layout(
                        title=f"{historical_symbol} Price History (7 Days)",
                        xaxis_title="Date",
                        yaxis_title="Price (USD)",
                        height=500
                    )
                    st.plotly_chart(fig, use_container_width=True, key="historical_chart")
            
            last_update.text(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            if not auto_refresh:
                break
            
            time.sleep(refresh_interval)
            
        except Exception as e:
            st.error(f"Error updating dashboard: {str(e)}")
            time.sleep(10)

if __name__ == "__main__":
    main()