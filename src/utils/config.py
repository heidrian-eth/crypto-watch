import os
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

class Config:
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY', '')
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    
    CACHE_DURATION_MINUTES = int(os.getenv('CACHE_DURATION_MINUTES', '5'))
    
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
    # Keep it to 5 or fewer keywords
    TREND_KEYWORDS = [
        'Bitcoin',
        'Ethereum',
        'Cryptocurrency',
        'Solana',
        'Cardano'
    ]
    
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