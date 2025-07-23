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
    
    PRICE_PAIRS = ['BTCUSD', 'ETHUSD']
    
    TOP_CRYPTOS_COUNT = 8
    
    UPDATE_INTERVAL_SECONDS = 60