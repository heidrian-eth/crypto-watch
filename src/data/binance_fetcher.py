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
        self.base_url = "https://data.binance.com/api/v3"
        self.dapi_url = "https://dapi.binance.com/dapi/v1"  # COIN-M futures API
        self.api_key = Config.BINANCE_API_KEY
        self.api_secret = Config.BINANCE_API_SECRET
        self._cache = {}
        self._cache_timestamps = {}
        
        # Debug: Print API key status (masked for security)
        if self.api_key:
            print(f"Binance API Key loaded: {self.api_key[:2]}...{self.api_key[-2:]}")
        else:
            print("WARNING: Binance API Key is empty or not loaded")
        
        if self.api_secret:
            print(f"Binance API Secret loaded: {self.api_secret[:2]}...{self.api_secret[-2:]}")
        else:
            print("WARNING: Binance API Secret is empty or not loaded")
    
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
    
    def get_24hr_ticker_stats(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get 24hr ticker statistics including volume data"""
        cache_key = f"ticker_stats_{'_'.join(symbols)}"
        cached_data = self._get_from_cache(cache_key, ttl_minutes=5)
        if cached_data is not None:
            return cached_data
        
        try:
            # Map our symbols to Binance format
            binance_symbols = []
            for symbol in symbols:
                binance_symbol = symbol.replace('-USD', 'USDT')
                binance_symbols.append(binance_symbol)
            
            url = f"{self.base_url}/ticker/24hr"
            params = {'symbols': str(binance_symbols).replace("'", '"')}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                result = {}
                for item in data:
                    # Convert back to our symbol format
                    our_symbol = item['symbol'].replace('USDT', '-USD')
                    if our_symbol in symbols:
                        result[our_symbol] = {
                            'volume': float(item['volume']),
                            'quoteVolume': float(item['quoteVolume']),
                            'count': int(item['count']),
                            'priceChange': float(item['priceChange']),
                            'priceChangePercent': float(item['priceChangePercent']),
                            'weightedAvgPrice': float(item['weightedAvgPrice']),
                            'highPrice': float(item['highPrice']),
                            'lowPrice': float(item['lowPrice'])
                        }
                
                self._save_to_cache(cache_key, result)
                return result
            else:
                print(f"Error fetching 24hr ticker stats: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"Error fetching 24hr ticker stats: {e}")
            return {}
    
    def calculate_volume_data(self, days: int = 7) -> pd.DataFrame:
        """Calculate volume data for BTC, ETH, Alt Index, and COIN-M futures"""
        try:
            volume_data = {}
            
            # Get spot volume data from historical klines
            main_symbols = ['BTC-USD', 'ETH-USD']
            alt_symbols = ['BNB-USD', 'SOL-USD', 'XRP-USD', 'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'AVAX-USD', 'DOT-USD']
            all_spot_symbols = main_symbols + alt_symbols
            
            spot_data = self.get_multiple_symbols_historical(all_spot_symbols, days=days)
            
            # Process BTC and ETH spot volume
            for symbol in main_symbols:
                if symbol in spot_data and not spot_data[symbol].empty and 'volume' in spot_data[symbol].columns:
                    volume_data[symbol] = spot_data[symbol]['volume']
            
            # Calculate Alt Index weighted volume
            if len([s for s in alt_symbols if s in spot_data]) > 0:
                alt_volume_series = self.calculate_alt_weighted_volume(spot_data, alt_symbols)
                if not alt_volume_series.empty:
                    volume_data['Alt Index'] = alt_volume_series
            
            # Get COIN-M futures volume data
            for asset in ['BTC', 'ETH']:
                for symbol in Config.COINM_FUTURES_SYMBOLS[asset]:
                    futures_df = self.get_coinm_klines(symbol, interval='1h', days=days)
                    if not futures_df.empty and 'volume' in futures_df.columns:
                        display_name = Config.FUTURES_DISPLAY_NAMES.get(symbol, symbol)
                        volume_data[display_name] = futures_df['volume']
            
            if volume_data:
                return pd.DataFrame(volume_data)
            else:
                print("No volume data available")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error calculating volume data: {e}")
            return pd.DataFrame()
    
    def calculate_alt_weighted_volume(self, spot_data: Dict[str, pd.DataFrame], alt_symbols: List[str]) -> pd.Series:
        """Calculate weighted volume for Alt Index using market cap weights"""
        try:
            # Use the same weights as the Alt Index price calculation
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
            for symbol in alt_symbols:
                if symbol in spot_data and not spot_data[symbol].empty:
                    if all_timestamps is None:
                        all_timestamps = spot_data[symbol].index
                    else:
                        all_timestamps = all_timestamps.intersection(spot_data[symbol].index)
            
            if all_timestamps is None or all_timestamps.empty:
                return pd.Series()
            
            # Calculate weighted volume
            weighted_volume = pd.Series(0.0, index=all_timestamps)
            
            for symbol in alt_symbols:
                if symbol in spot_data and not spot_data[symbol].empty and 'volume' in spot_data[symbol].columns:
                    weight = weights.get(symbol, 0.01)  # Default small weight
                    # Align data to common timestamps
                    aligned_volume = spot_data[symbol].loc[all_timestamps, 'volume']
                    weighted_volume += aligned_volume * weight
            
            return weighted_volume
            
        except Exception as e:
            print(f"Error calculating alt weighted volume: {e}")
            return pd.Series()
    
    def get_5min_klines(self, symbol: str, days: int = 7) -> pd.DataFrame:
        """Get 5-minute kline data for high-frequency volatility analysis"""
        cache_key = f"5min_klines_{symbol}_{days}"
        cached_data = self._get_from_cache(cache_key, ttl_minutes=15)
        if cached_data is not None:
            return cached_data
        
        try:
            # Calculate total datapoints needed
            total_points = days * 24 * 12  # 5-min intervals
            limit_per_request = 1000  # Binance API limit
            
            all_data = []
            end_time = int(datetime.now().timestamp() * 1000)
            
            # Make multiple requests if needed
            while len(all_data) < total_points:
                remaining_points = total_points - len(all_data)
                current_limit = min(limit_per_request, remaining_points)
                
                url = f"{self.base_url}/klines"
                params = {
                    'symbol': symbol,
                    'interval': '5m',
                    'endTime': end_time,
                    'limit': current_limit
                }
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if not data:
                        break  # No more data available
                    
                    # Prepend data (since we're going backwards in time)
                    all_data = data + all_data
                    
                    # Update end_time to the timestamp of the earliest data point
                    end_time = int(data[0][0]) - 1  # 1ms before the first timestamp
                    
                    # Small delay to respect rate limits
                    time.sleep(0.1)
                else:
                    print(f"Error fetching 5-min klines for {symbol}: {response.status_code}")
                    break
            
            if all_data:
                # Convert to DataFrame
                df = pd.DataFrame(all_data, columns=[
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
                
                # Set timestamp as index and sort
                df.set_index('timestamp', inplace=True)
                df.sort_index(inplace=True)
                
                # Keep only the columns we need
                df = df[['price', 'open', 'high', 'low', 'volume']]
                
                # Trim to exact number of days requested
                cutoff_time = df.index.max() - pd.Timedelta(days=days)
                df = df[df.index >= cutoff_time]
                
                self._save_to_cache(cache_key, df)
                return df
            else:
                print(f"No 5-min klines data received for {symbol}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error fetching 5-min klines for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_high_freq_volatility(self, days: int = 7) -> pd.DataFrame:
        """Calculate high-frequency volatility using 5-min data and hourly LMS regression"""
        try:
            import numpy as np
            from scipy import stats
            
            volatility_data = {}
            
            # Get 5-minute data for BTC and ETH
            symbols = {'BTCUSDT': 'BTC', 'ETHUSDT': 'ETH'}
            
            for binance_symbol, display_name in symbols.items():
                df_5min = self.get_5min_klines(binance_symbol, days=days)
                
                if df_5min.empty:
                    continue
                
                # Group into 1-hour bins (12 x 5-minute intervals)
                hourly_volatility = []
                hourly_timestamps = []
                
                # Resample to get hour boundaries, then process each hour
                df_5min_copy = df_5min.copy()
                df_5min_copy['hour'] = df_5min_copy.index.floor('h')
                
                for hour_start, hour_group in df_5min_copy.groupby('hour'):
                    if len(hour_group) >= 6:  # Need at least 6 points for meaningful regression
                        prices = hour_group['price'].values
                        
                        # Create time index for regression (0, 1, 2, ..., n-1)
                        time_index = np.arange(len(prices))
                        
                        # Calculate LMS (Least Mean Squares) regression
                        slope, intercept, r_value, p_value, std_err = stats.linregress(time_index, prices)
                        
                        # Calculate regression line
                        regression_line = slope * time_index + intercept
                        
                        # Subtract trend to get detrended residuals
                        residuals = prices - regression_line
                        
                        # Calculate standard deviation of residuals (high-freq volatility)
                        hf_volatility = np.std(residuals, ddof=1)  # Sample standard deviation
                        
                        hourly_volatility.append(hf_volatility)
                        hourly_timestamps.append(hour_start)
                
                if hourly_volatility:
                    # Create series with hourly timestamps
                    volatility_series = pd.Series(
                        hourly_volatility, 
                        index=pd.to_datetime(hourly_timestamps),
                        name=f'{display_name}_HF_Volatility'
                    )
                    volatility_data[display_name] = volatility_series
            
            if volatility_data:
                return pd.DataFrame(volatility_data)
            else:
                print("No high-frequency volatility data available")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error calculating high-frequency volatility: {e}")
            return pd.DataFrame()
    
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