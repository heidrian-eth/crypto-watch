# Crypto Watch Dashboard

A Streamlit-based dashboard for monitoring cryptocurrency prices and Google Trends data to help identify optimal trading opportunities.

## Features

- **Real-time Price Monitoring**: Track BTC and ETH prices with live updates
- **Top 8 Crypto Index**: Weighted average of top 8 cryptocurrencies by market cap
- **Google Trends Analysis**: Monitor search interest for key crypto terms with hourly granularity
- **Market Metrics**: View market cap, 24h changes, top gainers/losers
- **Historical Data**: 7-day price charts with candlestick visualization
- **Auto-refresh**: Configurable automatic data updates

## Setup

1. Clone the repository and navigate to the project directory

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. (Optional) Set up API keys:
   - Copy `.env.example` to `.env`
   - Add your CoinGecko API key for higher rate limits

## Running the Dashboard

```bash
streamlit run app.py
```

The dashboard will open in your default browser at `http://localhost:8501`

## Dashboard Sections

1. **Price Overview**: Current prices for BTC/ETH and top 8 cryptocurrencies
2. **Google Trends**: Search interest trends and momentum analysis
3. **Market Analysis**: Key market metrics and performance indicators
4. **Historical Data**: 7-day price history with candlestick charts

## Configuration

Edit `src/utils/config.py` to customize:
- Tracked cryptocurrencies
- Google Trends keywords
- Update intervals
- Cache duration

## Data Sources

- **Price Data**: Yahoo Finance (yfinance) and CoinGecko API
- **Trends Data**: Google Trends (pytrends)
- **Market Data**: Real-time aggregation from multiple sources