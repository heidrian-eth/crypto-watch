import pandas as pd
from pytrends.request import TrendReq
from datetime import datetime, timedelta
import time
from typing import List, Dict, Optional
from src.utils.config import Config
import streamlit as st

class TrendsDataFetcher:
    def __init__(self):
        self.pytrends = TrendReq(hl='en-US', tz=360)
    
    @st.cache_data(ttl=Config.CACHE_TTL_SECONDS)
    def get_trends_data(_self, keywords: List[str], timeframe: str = 'now 7-d') -> pd.DataFrame:
        try:
            _self.pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo='', gprop='')
            
            interest_over_time = _self.pytrends.interest_over_time()
            
            if not interest_over_time.empty:
                interest_over_time = interest_over_time.drop('isPartial', axis=1, errors='ignore')
                return interest_over_time
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error fetching trends data: {e}")
            return pd.DataFrame()
    
    @st.cache_data(ttl=Config.CACHE_TTL_SECONDS)
    def get_regional_interest(_self, keywords: List[str]) -> Dict[str, pd.DataFrame]:
        try:
            _self.pytrends.build_payload(keywords, cat=0, timeframe='now 7-d', geo='', gprop='')
            
            regional_data = {}
            regional_data['by_region'] = _self.pytrends.interest_by_region(resolution='COUNTRY', inc_low_vol=True, inc_geo_code=False)
            
            return regional_data
            
        except Exception as e:
            print(f"Error fetching regional interest: {e}")
            return {}
    
    @st.cache_data(ttl=Config.CACHE_TTL_SECONDS)
    def get_related_queries(_self, keywords: List[str]) -> Dict[str, Dict]:
        try:
            _self.pytrends.build_payload(keywords, cat=0, timeframe='now 7-d', geo='', gprop='')
            
            related_queries = _self.pytrends.related_queries()
            
            return related_queries
            
        except Exception as e:
            print(f"Error fetching related queries: {e}")
            return {}
    
    @st.cache_data(ttl=Config.CACHE_TTL_SECONDS)
    def get_multiple_trends_data(_self, keyword_batches: List[List[str]], timeframe: str = 'now 7-d') -> pd.DataFrame:
        """Fetch trends data for multiple batches of keywords and combine them"""
        combined_df = pd.DataFrame()
        
        for i, keywords in enumerate(keyword_batches):
            if not keywords:
                continue
                
            batch_df = _self.get_trends_data(keywords, timeframe)
            if not batch_df.empty:
                if combined_df.empty:
                    combined_df = batch_df
                else:
                    # Merge on datetime index
                    combined_df = combined_df.join(batch_df, how='outer')
                
                # Add small delay between requests to avoid rate limiting
                if i < len(keyword_batches) - 1:
                    time.sleep(2)
        
        return combined_df.fillna(0)
    
    def calculate_trends_alt_index(self, trends_df: pd.DataFrame, exclude_columns: List[str] = None) -> pd.Series:
        """Calculate an Alt Index from Google Trends data, similar to price Alt Index"""
        if trends_df.empty:
            return pd.Series()
        
        # Exclude non-crypto columns (like 'Cryptocurrency' which is too general)
        exclude_columns = exclude_columns or ['Cryptocurrency']
        crypto_columns = [col for col in trends_df.columns if col not in exclude_columns]
        
        if not crypto_columns:
            return pd.Series()
        
        # Create equal-weighted index (could be enhanced with market cap weighting)
        alt_index = trends_df[crypto_columns].mean(axis=1)
        
        return alt_index
    
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