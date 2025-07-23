import pandas as pd
from pytrends.request import TrendReq
from datetime import datetime, timedelta
import time
from typing import List, Dict, Optional
from src.utils.config import Config

class TrendsDataFetcher:
    def __init__(self):
        self.pytrends = TrendReq(hl='en-US', tz=360)
        self._cache = {}
        self._cache_timestamps = {}
    
    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache_timestamps:
            return False
        cache_age = time.time() - self._cache_timestamps[key]
        return cache_age < (Config.CACHE_DURATION_MINUTES * 60)
    
    def _get_from_cache(self, key: str) -> Optional[any]:
        if self._is_cache_valid(key):
            return self._cache[key]
        return None
    
    def _save_to_cache(self, key: str, data: any):
        self._cache[key] = data
        self._cache_timestamps[key] = time.time()
    
    def get_trends_data(self, keywords: List[str], timeframe: str = 'now 7-d') -> pd.DataFrame:
        cache_key = f"trends_{'_'.join(keywords)}_{timeframe}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        try:
            self.pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo='', gprop='')
            
            interest_over_time = self.pytrends.interest_over_time()
            
            if not interest_over_time.empty:
                interest_over_time = interest_over_time.drop('isPartial', axis=1, errors='ignore')
                
                self._save_to_cache(cache_key, interest_over_time)
                return interest_over_time
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error fetching trends data: {e}")
            return pd.DataFrame()
    
    def get_regional_interest(self, keywords: List[str]) -> Dict[str, pd.DataFrame]:
        cache_key = f"regional_{'_'.join(keywords)}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        try:
            self.pytrends.build_payload(keywords, cat=0, timeframe='now 7-d', geo='', gprop='')
            
            regional_data = {}
            regional_data['by_region'] = self.pytrends.interest_by_region(resolution='COUNTRY', inc_low_vol=True, inc_geo_code=False)
            
            self._save_to_cache(cache_key, regional_data)
            return regional_data
            
        except Exception as e:
            print(f"Error fetching regional interest: {e}")
            return {}
    
    def get_related_queries(self, keywords: List[str]) -> Dict[str, Dict]:
        cache_key = f"queries_{'_'.join(keywords)}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        try:
            self.pytrends.build_payload(keywords, cat=0, timeframe='now 7-d', geo='', gprop='')
            
            related_queries = self.pytrends.related_queries()
            
            self._save_to_cache(cache_key, related_queries)
            return related_queries
            
        except Exception as e:
            print(f"Error fetching related queries: {e}")
            return {}
    
    def calculate_trend_momentum(self, trends_df: pd.DataFrame) -> Dict[str, Dict]:
        if trends_df.empty:
            return {}
        
        momentum_data = {}
        
        for column in trends_df.columns:
            values = trends_df[column].values
            
            current_value = values[-1] if len(values) > 0 else 0
            avg_value = values.mean() if len(values) > 0 else 0
            
            if len(values) >= 24:
                change_24h = ((values[-1] - values[-24]) / values[-24] * 100) if values[-24] != 0 else 0
            else:
                change_24h = 0
            
            if len(values) >= 2:
                trend_direction = 'up' if values[-1] > values[-2] else 'down'
            else:
                trend_direction = 'neutral'
            
            momentum_data[column] = {
                'current': current_value,
                'average': avg_value,
                'change_24h': change_24h,
                'direction': trend_direction,
                'max_7d': values.max() if len(values) > 0 else 0,
                'min_7d': values.min() if len(values) > 0 else 0
            }
        
        return momentum_data