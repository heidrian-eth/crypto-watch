import pandas as pd
from pycoingecko import CoinGeckoAPI
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional, Any
import requests
from src.utils.config import Config

class CryptoDataFetcher:
    def __init__(self):
        self.cg = CoinGeckoAPI()
        if Config.COINGECKO_API_KEY:
            self.cg.api_key = Config.COINGECKO_API_KEY
        self._cache = {}
        self._cache_timestamps = {}
    
    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache_timestamps:
            return False
        cache_age = time.time() - self._cache_timestamps[key]
        return cache_age < (Config.CACHE_DURATION_MINUTES * 60)
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        if self._is_cache_valid(key):
            return self._cache[key]
        return None
    
    def _save_to_cache(self, key: str, data: Any):
        self._cache[key] = data
        self._cache_timestamps[key] = time.time()
    
    def get_price_data(self, symbols: List[str]) -> pd.DataFrame:
        cache_key = f"prices_{'_'.join(symbols)}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        data = []
        
        # Map trading pairs to CoinGecko IDs
        symbol_map = {
            'BTC-USD': 'bitcoin',
            'ETH-USD': 'ethereum'
        }
        
        ids = [symbol_map.get(s, s.lower().replace('-usd', '')) for s in symbols]
        
        try:
            # Get price data from CoinGecko
            price_data = self.cg.get_price(
                ids=','.join(ids),
                vs_currencies='usd',
                include_24hr_vol=True,
                include_24hr_change=True,
                include_last_updated_at=True
            )
            
            for symbol, coin_id in zip(symbols, ids):
                if coin_id in price_data:
                    coin_data = price_data[coin_id]
                    data.append({
                        'symbol': symbol,
                        'price': coin_data['usd'],
                        'change_24h': coin_data.get('usd_24h_change', 0),
                        'volume_24h': coin_data.get('usd_24h_vol', 0),
                        'timestamp': datetime.now()
                    })
        except Exception as e:
            print(f"Error fetching prices: {e}")
        
        df = pd.DataFrame(data)
        self._save_to_cache(cache_key, df)
        return df
    
    def get_top_cryptos_by_market_cap(self, count: int = 8) -> pd.DataFrame:
        cache_key = f"top_cryptos_{count}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        try:
            coins = self.cg.get_coins_markets(
                vs_currency='usd',
                order='market_cap_desc',
                per_page=count,
                page=1,
                sparkline=False,
                price_change_percentage='24h'
            )
            
            df = pd.DataFrame(coins)
            df = df[['id', 'symbol', 'name', 'current_price', 'market_cap', 
                    'market_cap_rank', 'price_change_percentage_24h', 'total_volume']]
            df.columns = ['id', 'symbol', 'name', 'price', 'market_cap', 
                         'rank', 'change_24h', 'volume_24h']
            df['timestamp'] = datetime.now()
            
            self._save_to_cache(cache_key, df)
            return df
        except Exception as e:
            print(f"Error fetching top cryptos: {e}")
            return pd.DataFrame()
    
    def calculate_weighted_average(self, df: pd.DataFrame) -> Dict:
        if df.empty:
            return {'weighted_avg_price': 0, 'total_market_cap': 0, 'weighted_avg_change_24h': 0}
        
        total_market_cap = df['market_cap'].sum()
        df['weight'] = df['market_cap'] / total_market_cap
        weighted_avg_price = (df['price'] * df['weight']).sum()
        weighted_avg_change = (df['change_24h'] * df['weight']).sum()
        
        return {
            'weighted_avg_price': weighted_avg_price,
            'weighted_avg_change_24h': weighted_avg_change,
            'total_market_cap': total_market_cap,
            'timestamp': datetime.now()
        }
    
    def get_historical_data(self, symbol: str, days: int = 7) -> pd.DataFrame:
        cache_key = f"history_{symbol}_{days}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Map trading pairs to CoinGecko IDs
        symbol_map = {
            'BTC-USD': 'bitcoin',
            'ETH-USD': 'ethereum'
        }
        
        coin_id = symbol_map.get(symbol, symbol.lower().replace('-usd', ''))
        
        try:
            # Get historical data from CoinGecko
            data = self.cg.get_coin_market_chart_by_id(
                id=coin_id,
                vs_currency='usd',
                days=days
            )
            
            # Convert to DataFrame
            prices = data['prices']
            df = pd.DataFrame(prices, columns=['timestamp', 'price'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.rename(columns={'timestamp': 'Date', 'price': 'Close'}, inplace=True)
            
            # Add dummy columns for compatibility
            df['Open'] = df['Close']
            df['High'] = df['Close']
            df['Low'] = df['Close']
            df['Volume'] = 0
            
            self._save_to_cache(cache_key, df)
            return df
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_historical_hourly_data(self, symbols: List[str], days: int = 7) -> Dict[str, pd.DataFrame]:
        """Get historical hourly data for multiple symbols"""
        result = {}
        
        # Map trading pairs to CoinGecko IDs
        symbol_map = {
            'BTC-USD': 'bitcoin',
            'ETH-USD': 'ethereum'
        }
        
        for symbol in symbols:
            coin_id = symbol_map.get(symbol, symbol.lower().replace('-usd', ''))
            cache_key = f"hourly_{coin_id}_{days}"
            cached_data = self._get_from_cache(cache_key)
            
            if cached_data is not None:
                result[symbol] = cached_data
                continue
                
            try:
                # Get historical data from CoinGecko (hourly for 7 days)
                data = self.cg.get_coin_market_chart_by_id(
                    id=coin_id,
                    vs_currency='usd',
                    days=days
                )
                
                # Convert to DataFrame
                prices = data['prices']
                df = pd.DataFrame(prices, columns=['timestamp', 'price'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Resample to hourly to ensure consistent intervals
                df = df.resample('1h').mean()
                df = df.dropna()
                
                self._save_to_cache(cache_key, df)
                result[symbol] = df
                
            except Exception as e:
                print(f"Error fetching hourly data for {symbol}: {e}")
                result[symbol] = pd.DataFrame()
                
        return result
    
    def get_weighted_index_history(self, days: int = 7) -> pd.DataFrame:
        """Get historical weighted index data"""
        cache_key = f"weighted_index_{days}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
            
        try:
            # Get current top 8 cryptos for market cap weights
            coins = self.cg.get_coins_markets(
                vs_currency='usd',
                order='market_cap_desc',
                per_page=8,
                page=1,
                sparkline=False
            )
            
            if not coins:
                return pd.DataFrame()
            
            # Get historical data for top 4 coins only (faster loading)
            all_data = {}
            top_coins = coins[:4]  # Just use top 4 for faster loading
            total_market_cap = sum(coin['market_cap'] for coin in top_coins if coin['market_cap'])
            
            for coin in top_coins:
                coin_id = coin['id']
                mcap = coin.get('market_cap', 0)
                
                if mcap == 0:
                    continue
                    
                try:
                    # Get historical price data
                    data = self.cg.get_coin_market_chart_by_id(
                        id=coin_id,
                        vs_currency='usd',
                        days=days
                    )
                    
                    if 'prices' in data:
                        prices = data['prices']
                        df = pd.DataFrame(prices, columns=['timestamp', 'price'])
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        df.set_index('timestamp', inplace=True)
                        
                        # Resample to hourly
                        df = df.resample('1h').mean()
                        
                        # Calculate weight
                        weight = mcap / total_market_cap
                        df['weighted_price'] = df['price'] * weight
                        
                        all_data[coin_id] = df['weighted_price']
                        
                except Exception as e:
                    print(f"Error fetching data for {coin_id}: {e}")
                    continue
            
            if not all_data:
                return pd.DataFrame()
            
            # Combine all weighted prices
            combined_df = pd.DataFrame(all_data)
            
            # Sum weighted prices to get the index
            index_df = pd.DataFrame()
            index_df['price'] = combined_df.sum(axis=1, skipna=True)
            
            # Remove any rows with NaN or 0 values
            index_df = index_df.dropna()
            index_df = index_df[index_df['price'] > 0]
            
            self._save_to_cache(cache_key, index_df)
            return index_df
            
        except Exception as e:
            print(f"Error fetching weighted index history: {e}")
            return pd.DataFrame()