import requests
import json
import os
import time
from pathlib import Path

TCGCSV_BASE_URL = "https://tcgcsv.com/tcgplayer"
POKEMON_CATEGORY_ID = 3
CACHE_DIR = Path("cache")
CACHE_EXPIRY_SECONDS = 7 * 24 * 60 * 60  # 1 week


class TCGCSVService:
    """Service for handling TCGPlayer CSV API calls with caching"""
    
    def __init__(self):
        # Create cache directory if it doesn't exist
        CACHE_DIR.mkdir(exist_ok=True)
        self.groups_cache = None
        self.products_cache = {}
    
    def _get_cache_path(self, cache_key):
        """Get the cache file path for a given key"""
        safe_key = cache_key.replace("/", "_").replace(":", "_")
        return CACHE_DIR / f"{safe_key}.json"
    
    def _is_cache_valid(self, cache_path):
        """Check if cache file exists and is not expired"""
        if not cache_path.exists():
            return False
        
        # Check if cache is older than 1 week
        cache_age = time.time() - cache_path.stat().st_mtime
        return cache_age < CACHE_EXPIRY_SECONDS
    
    def _read_cache(self, cache_key):
        """Read data from cache if valid"""
        cache_path = self._get_cache_path(cache_key)
        
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading cache: {e}")
                return None
        
        return None
    
    def _write_cache(self, cache_key, data):
        """Write data to cache"""
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error writing cache: {e}")
    
    def get_groups(self):
        """Fetch all Pokemon TCG groups from TCGPlayer CSV API with caching"""
        cache_key = "groups"
        
        # Check cache first
        cached_data = self._read_cache(cache_key)
        if cached_data:
            print(f"Using cached groups data ({len(cached_data)} groups)")
            return cached_data
        
        # Fetch from API
        try:
            url = f"{TCGCSV_BASE_URL}/{POKEMON_CATEGORY_ID}/groups"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("success") and "results" in data:
                groups = {group["name"]: group["groupId"] for group in data["results"]}
                
                # Cache the result
                self._write_cache(cache_key, groups)
                
                return groups
            return {}
        except Exception as e:
            print(f"Error fetching groups: {e}")
            return {}
    
    def get_products(self, group_id):
        """Fetch all products for a specific group from TCGPlayer CSV API with caching"""
        cache_key = f"products_{group_id}"
        
        # Check cache first
        cached_data = self._read_cache(cache_key)
        if cached_data:
            print(f"Using cached products for group {group_id}")
            return cached_data
        
        # Fetch from API
        try:
            url = f"{TCGCSV_BASE_URL}/{POKEMON_CATEGORY_ID}/{group_id}/products"
            print(f"Fetching products for group {group_id}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("success") and "results" in data:
                products = data["results"]
                
                # Cache the result
                self._write_cache(cache_key, products)
                
                return products
            return []
        except Exception as e:
            print(f"Error fetching products for group {group_id}: {e}")
            return []
    
    def clear_cache(self):
        """Clear all cached data"""
        try:
            for cache_file in CACHE_DIR.glob("*.json"):
                cache_file.unlink()
            print("Cache cleared successfully")
        except Exception as e:
            print(f"Error clearing cache: {e}")
    
    def clear_expired_cache(self):
        """Clear only expired cache files"""
        try:
            for cache_file in CACHE_DIR.glob("*.json"):
                if not self._is_cache_valid(cache_file):
                    cache_file.unlink()
            print("Expired cache cleared successfully")
        except Exception as e:
            print(f"Error clearing expired cache: {e}")
