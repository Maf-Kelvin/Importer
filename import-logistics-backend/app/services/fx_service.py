# app/services/fx_service.py
import requests
from typing import Dict, Optional
from datetime import datetime
from app.core.config import settings
import redis
import json

redis_client = redis.Redis.from_url(settings.REDIS_URL)


class FXService:
    def __init__(self):
        self.api_key = settings.EXCHANGERATE_API_KEY
        self.api_url = settings.EXCHANGERATE_API_URL
        self.base_currency = "USD"
    
    def get_fx_rate(self, from_currency: str, to_currency: str = "USD") -> float:
        """Get current FX rate with caching."""
        if from_currency == to_currency:
            return 1.0
        
        cache_key = f"fx_rate:{from_currency}:{to_currency}"
        
        # Try to get from cache first
        cached_rate = redis_client.get(cache_key)
        if cached_rate:
            return float(cached_rate)
        
        # Fetch from API
        try:
            response = requests.get(f"{self.api_url}{from_currency}")
            response.raise_for_status()
            data = response.json()
            
            rate = data['rates'].get(to_currency)
            if rate:
                # Cache for 1 hour
                redis_client.setex(cache_key, 3600, str(rate))
                return float(rate)
                
        except Exception as e:
            print(f"Error fetching FX rate: {e}")
        
        # Fallback to stored rates or default
        return self._get_fallback_rate(from_currency, to_currency)
    
    def _get_fallback_rate(self, from_currency: str, to_currency: str) -> float:
        """Get fallback FX rate from stored data."""
        fallback_rates = {
            ("EUR", "USD"): 1.08,
            ("CZK", "USD"): 0.044,
            ("NGN", "USD"): 0.0024,
            ("USD", "EUR"): 0.93,
            ("USD", "CZK"): 22.5,
            ("USD", "NGN"): 410.0,
        }
        
        return fallback_rates.get((from_currency, to_currency), 1.0)
    
    def convert_amount(self, amount: float, from_currency: str, to_currency: str = "USD") -> float:
        """Convert amount from one currency to another."""
        rate = self.get_fx_rate(from_currency, to_currency)
        return amount * rate
