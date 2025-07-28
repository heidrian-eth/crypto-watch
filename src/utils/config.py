import os
from typing import Dict, List
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

class Config:
    # Try Streamlit secrets first, then fall back to environment variables
    try:
        BINANCE_API_KEY = st.secrets.get('BINANCE_API_KEY', os.getenv('BINANCE_API_KEY', ''))
        BINANCE_API_SECRET = st.secrets.get('BINANCE_API_SECRET', os.getenv('BINANCE_API_SECRET', ''))
    except:
        # If st.secrets is not available (e.g., running outside Streamlit)
        BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
        BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    
    # Binance API URLs
    BINANCE_BASE_URL = os.getenv('BINANCE_BASE_URL', 'https://api.binance.com/api/v3')
    BINANCE_FUTURES_URL = os.getenv('BINANCE_FUTURES_URL', 'https://dapi.binance.com/dapi/v1')
    
    CACHE_DURATION_MINUTES = int(os.getenv('CACHE_DURATION_MINUTES', '5'))  # Changed default to 5 minutes
    CACHE_TTL_SECONDS = CACHE_DURATION_MINUTES * 60  # Cache TTL in seconds for Streamlit
    
    CRYPTO_SYMBOLS = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'BNB': 'binancecoin',
        'SOL': 'solana',
        'XRP': 'ripple',
        'USDC': 'usd-coin',
        'ADA': 'cardano',
        'DOGE': 'dogecoin'
    }
    
    # Google Trends API has limits on keywords per request
    # Keep it to 5 or fewer keywords per batch
    TREND_KEYWORDS_BATCH_1 = [
        'Bitcoin',
        'Ethereum',
        'Cryptocurrency',
        'BNB',
        'Solana'
    ]
    
    TREND_KEYWORDS_BATCH_2 = [
        'XRP',
        'Cardano',
        'Dogecoin',
        'Polygon',
        'Chainlink'
    ]
    
    # Legacy support
    TREND_KEYWORDS = TREND_KEYWORDS_BATCH_1
    
    # COIN-M Futures symbols for premium calculation
    COINM_FUTURES_SYMBOLS = {
        'BTC': ['BTCUSD_250926', 'BTCUSD_251226'],  # Sep 2025, Dec 2025
        'ETH': ['ETHUSD_250926', 'ETHUSD_251226']   # Sep 2025, Dec 2025
    }
    
    # Display names for futures contracts
    FUTURES_DISPLAY_NAMES = {
        'BTCUSD_250926': 'BTC Sep 2025',
        'BTCUSD_251226': 'BTC Dec 2025',
        'ETHUSD_250926': 'ETH Sep 2025',
        'ETHUSD_251226': 'ETH Dec 2025'
    }
    
    PRICE_PAIRS = ['BTCUSD', 'ETHUSD']
    
    TOP_CRYPTOS_COUNT = 8
    
    UPDATE_INTERVAL_SECONDS = 60