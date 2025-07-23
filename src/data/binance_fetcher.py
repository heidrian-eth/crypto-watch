import pandas as pd
import requests
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional
import hmac
import hashlib
from src.utils.config import Config

class BinanceFetcher:
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.dapi_url = "https://dapi.binance.com/dapi/v1"  # COIN-M futures API
        self.api_key = Config.BINANCE_API_KEY
        self.api_secret = Config.BINANCE_API_SECRET
        self._cache = {}
        self._cache_timestamps = {}
    
    def _get_from_cache(self, key: str, ttl_minutes: int = 5) -> Optional[any]:
        if key not in self._cache_timestamps:
            return None
        cache_age = time.time() - self._cache_timestamps[key]
        if cache_age < (ttl_minutes * 60):
            return self._cache[key]
        return None
    
    def _save_to_cache(self, key: str, data: any):
        self._cache[key] = data
        self._cache_timestamps[key] = time.time()
    
    def get_klines(self, symbol: str, interval: str = '1h', days: int = 7) -> pd.DataFrame:
        """Get historical kline/candlestick data from Binance"""
        cache_key = f"klines_{symbol}_{interval}_{days}"
        cached_data = self._get_from_cache(cache_key, ttl_minutes=15)  # Cache for 15 minutes
        if cached_data is not None:
            return cached_data
        
        try:
            # Calculate start time (7 days ago)
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = end_time - (days * 24 * 60 * 60 * 1000)  # 7 days in milliseconds
            
            url = f"{self.base_url}/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': start_time,
                'endTime': end_time,
                'limit': days * 24  # 7 days * 24 hours
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Convert to DataFrame
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_asset_volume', 'number_of_trades',
                    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                ])
                
                # Convert timestamp and prices
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['price'] = df['close'].astype(float)
                df['open'] = df['open'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['volume'] = df['volume'].astype(float)
                
                # Set timestamp as index
                df.set_index('timestamp', inplace=True)
                
                # Keep only the columns we need
                df = df[['price', 'open', 'high', 'low', 'volume']]
                
                self._save_to_cache(cache_key, df)
                return df
            else:
                print(f"Error fetching {symbol}: {response.status_code} - {response.text}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error fetching klines for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_multiple_symbols_historical(self, symbols: List[str], days: int = 7) -> Dict[str, pd.DataFrame]:
        """Get historical data for multiple symbols"""
        result = {}
        
        # Map our symbols to Binance format
        binance_symbols = {
            'BTC-USD': 'BTCUSDT',
            'ETH-USD': 'ETHUSDT',
            'BNB-USD': 'BNBUSDT',
            'SOL-USD': 'SOLUSDT',
            'XRP-USD': 'XRPUSDT',
            'ADA-USD': 'ADAUSDT',
            'DOGE-USD': 'DOGEUSDT',
            'MATIC-USD': 'MATICUSDT',
            'AVAX-USD': 'AVAXUSDT',
            'DOT-USD': 'DOTUSDT'
        }
        
        for symbol in symbols:
            binance_symbol = binance_symbols.get(symbol, symbol.replace('-USD', 'USDT'))
            df = self.get_klines(binance_symbol, interval='1h', days=days)
            if not df.empty:
                result[symbol] = df
            # Small delay to respect rate limits
            time.sleep(0.1)
        
        return result
    
    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for symbols"""
        cache_key = f"current_prices_{'_'.join(symbols)}"
        cached_data = self._get_from_cache(cache_key, ttl_minutes=1)  # Cache for 1 minute
        if cached_data is not None:
            return cached_data
        
        try:
            url = f"{self.base_url}/ticker/price"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                all_prices = response.json()
                
                # Create a lookup dict
                price_lookup = {item['symbol']: float(item['price']) for item in all_prices}
                
                # Map our symbols to Binance format and get prices
                binance_symbols = {
                    'BTC-USD': 'BTCUSDT',
                    'ETH-USD': 'ETHUSDT',
                    'BNB-USD': 'BNBUSDT',
                    'SOL-USD': 'SOLUSDT',
                    'XRP-USD': 'XRPUSDT',
                    'ADA-USD': 'ADAUSDT',
                    'DOGE-USD': 'DOGEUSDT',
                    'MATIC-USD': 'MATICUSDT',
                    'AVAX-USD': 'AVAXUSDT',
                    'DOT-USD': 'DOTUSDT'
                }
                
                result = {}
                for symbol in symbols:
                    binance_symbol = binance_symbols.get(symbol, symbol.replace('-USD', 'USDT'))
                    if binance_symbol in price_lookup:
                        result[symbol] = price_lookup[binance_symbol]
                
                self._save_to_cache(cache_key, result)
                return result
            else:
                print(f"Error fetching current prices: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"Error fetching current prices: {e}")
            return {}
    
    def calculate_weighted_index(self, historical_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Calculate weighted index from historical data"""
        if not historical_data:
            return pd.DataFrame()
        
        # Market cap weights for Alt Index (excluding BTC/ETH)
        weights = {
            'BNB-USD': 0.20,   # ~20% weight
            'SOL-USD': 0.18,   # ~18% weight
            'XRP-USD': 0.15,   # ~15% weight
            'ADA-USD': 0.12,   # ~12% weight
            'DOGE-USD': 0.12,  # ~12% weight
            'MATIC-USD': 0.10, # ~10% weight
            'AVAX-USD': 0.08,  # ~8% weight
            'DOT-USD': 0.05    # ~5% weight
        }
        
        # Find common timestamps
        all_timestamps = None
        for symbol, df in historical_data.items():
            if all_timestamps is None:
                all_timestamps = df.index
            else:
                all_timestamps = all_timestamps.intersection(df.index)
        
        if all_timestamps.empty:
            return pd.DataFrame()
        
        # Calculate weighted average
        weighted_prices = pd.Series(0.0, index=all_timestamps)
        
        for symbol, df in historical_data.items():
            weight = weights.get(symbol, 0.01)  # Default small weight
            # Align data to common timestamps
            aligned_prices = df.loc[all_timestamps, 'price']
            weighted_prices += aligned_prices * weight
        
        return pd.DataFrame({'price': weighted_prices}, index=all_timestamps)
    
    def get_coinm_exchange_info(self) -> Dict:
        """Get COIN-M futures exchange info to find available contracts"""
        cache_key = "coinm_exchange_info"
        cached_data = self._get_from_cache(cache_key, ttl_minutes=60)  # Cache for 1 hour
        if cached_data is not None:
            return cached_data
        
        try:
            url = f"{self.dapi_url}/exchangeInfo"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self._save_to_cache(cache_key, data)
                return data
            else:
                print(f"Error fetching COIN-M exchange info: {response.status_code}")
                return {}
        except Exception as e:
            print(f"Error fetching COIN-M exchange info: {e}")
            return {}
    
    def get_coinm_futures_symbols(self) -> Dict[str, List[str]]:
        """Get current COIN-M futures symbols for BTC and ETH quarterly contracts"""
        exchange_info = self.get_coinm_exchange_info()
        if not exchange_info or 'symbols' not in exchange_info:
            return {'BTC': [], 'ETH': []}
        
        btc_quarterly = []
        eth_quarterly = []
        
        for symbol_info in exchange_info['symbols']:
            symbol = symbol_info['symbol']
            contract_type = symbol_info.get('contractType', '')
            
            # Look for quarterly contracts (not perpetual)
            if contract_type == 'CURRENT_QUARTER' or contract_type == 'NEXT_QUARTER':
                if symbol.startswith('BTCUSD_') and symbol != 'BTCUSD_PERP':
                    btc_quarterly.append(symbol)
                elif symbol.startswith('ETHUSD_') and symbol != 'ETHUSD_PERP':
                    eth_quarterly.append(symbol)
        
        return {'BTC': btc_quarterly, 'ETH': eth_quarterly}
    
    def get_coinm_klines(self, symbol: str, interval: str = '1h', days: int = 7) -> pd.DataFrame:
        """Get historical kline/candlestick data from COIN-M futures"""
        cache_key = f"coinm_klines_{symbol}_{interval}_{days}"
        cached_data = self._get_from_cache(cache_key, ttl_minutes=15)
        if cached_data is not None:
            return cached_data
        
        try:
            # Calculate start time (7 days ago)
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = end_time - (days * 24 * 60 * 60 * 1000)
            
            url = f"{self.dapi_url}/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': start_time,
                'endTime': end_time,
                'limit': days * 24
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Convert to DataFrame
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'base_asset_volume', 'number_of_trades',
                    'taker_buy_volume', 'taker_buy_base_asset_volume', 'ignore'
                ])
                
                # Convert timestamp and prices
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['price'] = df['close'].astype(float)
                df['open'] = df['open'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['volume'] = df['volume'].astype(float)
                
                # Set timestamp as index
                df.set_index('timestamp', inplace=True)
                
                # Keep only the columns we need
                df = df[['price', 'open', 'high', 'low', 'volume']]
                
                self._save_to_cache(cache_key, df)
                return df
            else:
                print(f"Error fetching COIN-M klines for {symbol}: {response.status_code}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error fetching COIN-M klines for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_futures_premiums(self, days: int = 7) -> pd.DataFrame:
        """Calculate futures premiums for BTC and ETH quarterly contracts"""
        try:
            # Get spot prices
            spot_data = self.get_multiple_symbols_historical(['BTC-USD', 'ETH-USD'], days=days)
            if not spot_data or 'BTC-USD' not in spot_data or 'ETH-USD' not in spot_data:
                print("Failed to get spot data for premium calculation")
                return pd.DataFrame()
            
            btc_spot = spot_data['BTC-USD']
            eth_spot = spot_data['ETH-USD']
            
            premiums_data = {}
            
            # Process BTC futures from config
            for btc_symbol in Config.COINM_FUTURES_SYMBOLS['BTC']:
                futures_df = self.get_coinm_klines(btc_symbol, interval='1h', days=days)
                if not futures_df.empty:
                    # Align timestamps
                    common_times = btc_spot.index.intersection(futures_df.index)
                    if not common_times.empty:
                        spot_aligned = btc_spot.loc[common_times, 'price']
                        futures_aligned = futures_df.loc[common_times, 'price']
                        
                        # Calculate premium: (futures_price / spot_price) - 1
                        premium = (futures_aligned / spot_aligned) - 1
                        display_name = Config.FUTURES_DISPLAY_NAMES.get(btc_symbol, btc_symbol)
                        premiums_data[display_name] = premium * 100  # Convert to percentage
            
            # Process ETH futures from config
            for eth_symbol in Config.COINM_FUTURES_SYMBOLS['ETH']:
                futures_df = self.get_coinm_klines(eth_symbol, interval='1h', days=days)
                if not futures_df.empty:
                    # Align timestamps
                    common_times = eth_spot.index.intersection(futures_df.index)
                    if not common_times.empty:
                        spot_aligned = eth_spot.loc[common_times, 'price']
                        futures_aligned = futures_df.loc[common_times, 'price']
                        
                        # Calculate premium: (futures_price / spot_price) - 1
                        premium = (futures_aligned / spot_aligned) - 1
                        display_name = Config.FUTURES_DISPLAY_NAMES.get(eth_symbol, eth_symbol)
                        premiums_data[display_name] = premium * 100  # Convert to percentage
            
            if premiums_data:
                premiums_df = pd.DataFrame(premiums_data)
                return premiums_df
            else:
                print("No futures premium data available")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error calculating futures premiums: {e}")
            return pd.DataFrame()