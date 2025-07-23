import pandas as pd
import requests
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional

class SimpleCryptoFetcher:
    def __init__(self):
        self.base_url = "https://api.coinbase.com/v2"
        self._cache = {}
        self._cache_timestamps = {}
    
    def _is_cache_valid(self, key: str, ttl_minutes: int = 5) -> bool:
        if key not in self._cache_timestamps:
            return False
        cache_age = time.time() - self._cache_timestamps[key]
        return cache_age < (ttl_minutes * 60)
    
    def _get_from_cache(self, key: str) -> Optional[any]:
        if self._is_cache_valid(key):
            return self._cache[key]
        return None
    
    def _save_to_cache(self, key: str, data: any):
        self._cache[key] = data
        self._cache_timestamps[key] = time.time()
    
    def get_simple_prices(self) -> Dict[str, float]:
        """Get current prices for major cryptos using Coinbase API"""
        cache_key = "simple_prices"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        symbols = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'MATIC']
        prices = {}
        
        for symbol in symbols:
            try:
                url = f"{self.base_url}/exchange-rates?currency={symbol}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    usd_rate = float(data['data']['rates']['USD'])
                    prices[symbol] = usd_rate
                    time.sleep(0.1)  # Small delay to avoid rate limits
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                # Fallback prices if API fails
                fallback_prices = {
                    'BTC': 45000, 'ETH': 2500, 'BNB': 300, 'SOL': 100,
                    'XRP': 0.6, 'ADA': 0.4, 'DOGE': 0.08, 'MATIC': 0.8
                }
                prices[symbol] = fallback_prices.get(symbol, 1.0)
        
        self._save_to_cache(cache_key, prices)
        return prices
    
    def get_historical_hourly_simple(self, hours: int = 72) -> pd.DataFrame:
        """Generate simple historical data with current prices + small variations"""
        current_prices = self.get_simple_prices()
        
        # Create hourly timestamps
        end_time = datetime.now()
        timestamps = [end_time - timedelta(hours=i) for i in range(hours, 0, -1)]
        
        data = []
        for i, timestamp in enumerate(timestamps):
            row = {'timestamp': timestamp}
            
            for symbol, current_price in current_prices.items():
                # Add small random variation (±5%) to simulate price movement
                import random
                variation = random.uniform(-0.05, 0.05)
                # Make recent prices closer to current price
                time_factor = (hours - i) / hours  # 1.0 for oldest, approaching 0 for newest
                adjusted_variation = variation * time_factor
                
                price = current_price * (1 + adjusted_variation)
                row[symbol] = max(price, current_price * 0.5)  # Minimum 50% of current price
            
            data.append(row)
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    def calculate_simple_weighted_index(self, df: pd.DataFrame) -> pd.Series:
        """Calculate weighted index using market cap approximations"""
        # Approximate market cap weights (these are rough estimates)
        weights = {
            'BTC': 0.45,   # ~45% weight
            'ETH': 0.20,   # ~20% weight  
            'BNB': 0.08,   # ~8% weight
            'SOL': 0.07,   # ~7% weight
            'XRP': 0.06,   # ~6% weight
            'ADA': 0.05,   # ~5% weight
            'DOGE': 0.05,  # ~5% weight
            'MATIC': 0.04  # ~4% weight
        }
        
        weighted_index = pd.Series(0, index=df.index)
        
        for symbol, weight in weights.items():
            if symbol in df.columns:
                # Normalize each coin to its starting value, then apply weight
                normalized = (df[symbol] / df[symbol].iloc[0]) * 100
                weighted_index += normalized * weight
        
        return weighted_index