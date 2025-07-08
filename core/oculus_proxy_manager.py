"""
Oculus Proxy Manager - BOT-vCSGO-Beta V2
Universal proxy management system for both batch and non-batch operations

Features:
- Automatic IP detection and whitelist updates
- Support for both single pool (non-batch) and multi-pool (batch) operations
- Intelligent region rotation and proxy refresh
- Performance tracking and optimization
- Thread-safe operations
"""

import json
import time
import random
import logging
import requests
from typing import List, Dict, Optional, Union
from threading import Lock
from collections import defaultdict


class OculusProxyManager:
    """
    Universal proxy manager for Oculus Proxies API
    
    Supports two modes:
    - Single Pool Mode: For individual requests (like steamid_scraper)
    - Multi Pool Mode: For batch operations (like steam_listing_scraper)
    """
    
    def __init__(self, mode: str = "single", pool_count: int = 1, proxies_per_pool: int = 1000):
        """
        Initialize Oculus Proxy Manager
        
        Args:
            mode: "single" for individual requests, "multi" for batch operations
            pool_count: Number of pools for multi mode (ignored in single mode)
            proxies_per_pool: Number of proxies per pool
        """
        self.logger = logging.getLogger('OculusProxyManager')
        self.mode = mode
        self.pool_count = pool_count if mode == "multi" else 1
        self.proxies_per_pool = proxies_per_pool
        self._lock = Lock()
        
        # Oculus Proxies API configuration
        self.oculus_config = {
            'auth_token': '05bd54d2-e21c-41db-bf74-d12e460210a9',
            'order_token': 'oc_0d0a79f6',
            'whitelist_ip': [],  # Will be auto-detected
            'api_url': 'https://api.oculusproxies.com/v1/configure/proxy/getProxies'
        }
        
        # Available regions (Tier 1 + Tier 2 = most reliable)
        self.available_regions = [
            'us', 'gb', 'de', 'ca', 'au', 'fr', 'nl', 'jp', 'sg', 'br', 
            'mx', 'in', 'kr', 'hk', 'tw', 'pl', 'it', 'es', 'ch', 'se', 
            'no', 'dk', 'fi', 'at', 'be', 'ie', 'pt', 'ru', 'tr', 'za', 
            'eg', 'ae', 'sa', 'th', 'my', 'id', 'ph', 'vn', 'nz'
        ]
        
        # Initialize based on mode
        if mode == "single":
            self._init_single_mode()
        elif mode == "multi":
            self._init_multi_mode()
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'single' or 'multi'")
        
        # Auto-detect and update IP
        self._auto_detect_and_update_ip()
        
        # Initialize pools
        self._initialize_pools()
        
        self.logger.info(f"🚀 Oculus Proxy Manager initialized in {mode.upper()} mode")
        self.logger.info(f"📊 Configuration: {self.pool_count} pools, {self.proxies_per_pool} proxies each")
        
    def _init_single_mode(self):
        """Initialize single pool mode for individual requests"""
        self.current_region = 'us'
        self.proxy_pool = []
        self.refresh_count = 0
        self.refresh_interval = 1000
        self.error_count = 0
        self.consecutive_errors = 0
        
    def _init_multi_mode(self):
        """Initialize multi-pool mode for batch operations"""
        self.region_pools = {}
        for i in range(self.pool_count):
            pool_name = f'pool_{i+1}'
            region = self.available_regions[i % len(self.available_regions)]
            self.region_pools[pool_name] = {
                'region': region,
                'proxies': [],
                'performance': {
                    'success_count': 0, 
                    'error_count': 0, 
                    'consecutive_errors': 0, 
                    'last_error_time': 0, 
                    'response_times': []
                },
                'active': True
            }
        
        self.pool_error_threshold = 5
        self.pool_refresh_interval = 5000
        self.pool_requests = defaultdict(int)
        
    def _auto_detect_and_update_ip(self):
        """Automatically detect current IP and update whitelist"""
        try:
            self.logger.info("🔍 Auto-detecting current IP address...")
            
            # Try multiple IP detection services for reliability
            ip_services = [
                'https://api.ipify.org?format=json',
                'https://httpbin.org/ip',
                'https://api.myip.com',
                'https://ipapi.co/json/'
            ]
            
            detected_ip = None
            for service in ip_services:
                try:
                    response = requests.get(service, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Different services have different response formats
                    if 'ip' in data:
                        detected_ip = data['ip']
                    elif 'origin' in data:
                        detected_ip = data['origin']
                    elif 'query' in data:
                        detected_ip = data['query']
                    
                    if detected_ip:
                        break
                        
                except Exception as e:
                    self.logger.debug(f"IP detection service {service} failed: {e}")
                    continue
            
            if detected_ip:
                self.oculus_config['whitelist_ip'] = [detected_ip]
                self.logger.info(f"✅ IP auto-detected and whitelisted: {detected_ip}")
                return detected_ip
            else:
                # Fallback to manual IP
                fallback_ip = '181.127.133.115'
                self.oculus_config['whitelist_ip'] = [fallback_ip]
                self.logger.warning(f"⚠️ Auto-detection failed, using fallback IP: {fallback_ip}")
                return fallback_ip
                
        except Exception as e:
            fallback_ip = '181.127.133.115'
            self.oculus_config['whitelist_ip'] = [fallback_ip]
            self.logger.error(f"❌ IP auto-detection error: {e}, using fallback: {fallback_ip}")
            return fallback_ip
    
    def _parse_oculus_proxy(self, raw_proxy: str) -> Optional[str]:
        """Parse Oculus proxy format to standard format"""
        try:
            parts = raw_proxy.split(':')
            if len(parts) == 4:
                host, port, username, password = parts
                return f"http://{username}:{password}@{host}:{port}"
            else:
                self.logger.warning(f"Unexpected proxy format: {raw_proxy}")
                return None
        except Exception as e:
            self.logger.error(f"Error parsing proxy {raw_proxy}: {e}")
            return None
    
    def _load_proxies_for_region(self, region: str, count: int) -> List[str]:
        """Load proxies from Oculus API for specific region"""
        try:
            payload = json.dumps({
                "orderToken": self.oculus_config['order_token'],
                "country": region.upper(),
                "numberOfProxies": count,
                "whiteListIP": self.oculus_config['whitelist_ip'],
                "enableSock5": False,
                "planType": "SHARED_DC"
            })
            
            headers = {
                'authToken': self.oculus_config['auth_token'],
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                self.oculus_config['api_url'], 
                headers=headers, 
                data=payload, 
                timeout=30
            )
            response.raise_for_status()
            
            proxy_data = response.json()
            proxies = []
            
            # Handle different response formats
            if isinstance(proxy_data, dict) and 'proxies' in proxy_data:
                for proxy_info in proxy_data['proxies']:
                    if isinstance(proxy_info, str):
                        parsed = self._parse_oculus_proxy(proxy_info)
                        if parsed:
                            proxies.append(parsed)
            elif isinstance(proxy_data, list):
                for raw_proxy in proxy_data:
                    if isinstance(raw_proxy, str):
                        parsed = self._parse_oculus_proxy(raw_proxy)
                        if parsed:
                            proxies.append(parsed)
            elif isinstance(proxy_data, str):
                parsed = self._parse_oculus_proxy(proxy_data)
                if parsed:
                    proxies = [parsed]
            
            return proxies
            
        except Exception as e:
            self.logger.error(f"Error loading {count} proxies for region {region}: {e}")
            return []
    
    def _initialize_pools(self):
        """Initialize all pools based on mode"""
        if self.mode == "single":
            self._initialize_single_pool()
        else:
            self._initialize_multi_pools()
    
    def _initialize_single_pool(self):
        """Initialize single proxy pool"""
        self.logger.info(f"🔄 Initializing single pool for region: {self.current_region.upper()}")
        proxies = self._load_proxies_for_region(self.current_region, self.proxies_per_pool)
        
        with self._lock:
            self.proxy_pool = proxies
        
        if proxies:
            self.logger.info(f"✅ Single pool initialized: {len(proxies)} proxies from {self.current_region.upper()}")
        else:
            self.logger.warning(f"❌ Failed to initialize single pool for {self.current_region.upper()}")
    
    def _initialize_multi_pools(self):
        """Initialize multiple pools for batch operations"""
        self.logger.info(f"🔄 Initializing {self.pool_count} pools with {self.proxies_per_pool} proxies each...")
        
        for pool_name, pool_data in self.region_pools.items():
            region = pool_data['region']
            self.logger.info(f"Loading {region.upper()} pool ({pool_name})...")
            
            proxies = self._load_proxies_for_region(region, self.proxies_per_pool)
            pool_data['proxies'] = proxies
            
            if proxies:
                self.logger.info(f"✅ {pool_name.upper()}: {len(proxies)} proxies loaded for {region.upper()}")
            else:
                self.logger.warning(f"❌ {pool_name.upper()}: Failed to load proxies for {region.upper()}")
                pool_data['active'] = False
    
    def get_proxy(self) -> Optional[str]:
        """Get a proxy based on current mode"""
        if self.mode == "single":
            return self._get_single_proxy()
        else:
            return self._get_multi_proxy()
    
    def _get_single_proxy(self) -> Optional[str]:
        """Get proxy from single pool"""
        with self._lock:
            self.refresh_count += 1
            
            # Refresh pool if needed
            if self.refresh_count >= self.refresh_interval:
                self._refresh_single_pool()
            
            # Rotate region if too many errors
            if self.consecutive_errors >= 5:
                self._rotate_single_region()
            
            if self.proxy_pool:
                return random.choice(self.proxy_pool)
            return None
    
    def _get_multi_proxy(self) -> Optional[str]:
        """Get proxy from best performing pool"""
        best_pool = self._get_best_performing_pool()
        if not best_pool:
            return None
            
        pool_data = self.region_pools[best_pool]
        self.pool_requests[best_pool] += 1
        
        if pool_data['proxies']:
            return random.choice(pool_data['proxies'])
        return None
    
    def _get_best_performing_pool(self) -> Optional[str]:
        """Get the best performing pool for multi mode"""
        active_pools = [
            (name, pool) for name, pool in self.region_pools.items() 
            if pool['active'] and pool['proxies']
        ]
        
        if not active_pools:
            return None
        
        # Score pools based on performance
        pool_scores = []
        for pool_name, pool_data in active_pools:
            performance = pool_data['performance']
            total_requests = performance['success_count'] + performance['error_count']
            
            if total_requests == 0:
                score = 50.0  # Neutral score for unused pools
            else:
                success_rate = performance['success_count'] / total_requests
                avg_response_time = (
                    sum(performance['response_times']) / len(performance['response_times']) 
                    if performance['response_times'] else 5
                )
                score = (success_rate * 100) - (avg_response_time * 3) - (performance['consecutive_errors'] * 15)
            
            pool_scores.append((pool_name, score))
        
        # Return best pool
        pool_scores.sort(key=lambda x: x[1], reverse=True)
        return pool_scores[0][0]
    
    def _refresh_single_pool(self):
        """Refresh single pool"""
        self.logger.info(f"🔄 Refreshing single pool after {self.refresh_count} requests")
        proxies = self._load_proxies_for_region(self.current_region, self.proxies_per_pool)
        
        if proxies:
            self.proxy_pool = proxies
            self.logger.info(f"✅ Single pool refreshed: {len(proxies)} proxies")
        else:
            self.logger.warning("❌ Failed to refresh single pool")
        
        self.refresh_count = 0
    
    def _rotate_single_region(self):
        """Rotate to different region for single mode"""
        current_index = self.available_regions.index(self.current_region)
        next_index = (current_index + 1) % len(self.available_regions)
        new_region = self.available_regions[next_index]
        
        self.logger.warning(f"🔄 Rotating region: {self.current_region.upper()} → {new_region.upper()}")
        self.current_region = new_region
        self.consecutive_errors = 0
        
        proxies = self._load_proxies_for_region(new_region, self.proxies_per_pool)
        if proxies:
            self.proxy_pool = proxies
            self.logger.info(f"✅ Region rotated: {len(proxies)} proxies from {new_region.upper()}")
        else:
            self.logger.warning(f"❌ Failed to load proxies for {new_region.upper()}")
    
    def record_success(self, response_time: float = 0, pool_name: str = None):
        """Record successful request"""
        if self.mode == "single":
            with self._lock:
                self.consecutive_errors = 0
        else:
            if pool_name and pool_name in self.region_pools:
                performance = self.region_pools[pool_name]['performance']
                performance['success_count'] += 1
                performance['response_times'].append(response_time)
                performance['consecutive_errors'] = 0
                
                # Keep only last 50 response times
                if len(performance['response_times']) > 50:
                    performance['response_times'] = performance['response_times'][-50:]
    
    def record_failure(self, pool_name: str = None):
        """Record failed request"""
        if self.mode == "single":
            with self._lock:
                self.error_count += 1
                self.consecutive_errors += 1
        else:
            if pool_name and pool_name in self.region_pools:
                performance = self.region_pools[pool_name]['performance']
                performance['error_count'] += 1
                performance['consecutive_errors'] += 1
                performance['last_error_time'] = time.time()
                
                # Check if pool needs region rotation
                if performance['consecutive_errors'] >= self.pool_error_threshold:
                    self._rotate_pool_region(pool_name)
    
    def _rotate_pool_region(self, pool_name: str):
        """Rotate region for specific pool in multi mode"""
        pool_data = self.region_pools[pool_name]
        current_region = pool_data['region']
        
        # Get unused region
        used_regions = [pool['region'] for pool in self.region_pools.values()]
        available_new_regions = [r for r in self.available_regions if r not in used_regions]
        
        if available_new_regions:
            new_region = random.choice(available_new_regions)
            self.logger.warning(f"🔄 {pool_name.upper()} ROTATION: {current_region.upper()} → {new_region.upper()}")
            
            pool_data['region'] = new_region
            pool_data['performance']['consecutive_errors'] = 0
            
            proxies = self._load_proxies_for_region(new_region, self.proxies_per_pool)
            if proxies:
                pool_data['proxies'] = proxies
                pool_data['active'] = True
                self.logger.info(f"✅ {pool_name.upper()}: {len(proxies)} proxies loaded for {new_region.upper()}")
            else:
                self.logger.warning(f"❌ {pool_name.upper()}: Failed to load proxies for {new_region.upper()}")
                pool_data['active'] = False
    
    def get_stats(self) -> Dict:
        """Get proxy manager statistics"""
        if self.mode == "single":
            return {
                'mode': 'single',
                'current_region': self.current_region,
                'proxy_count': len(self.proxy_pool),
                'refresh_count': self.refresh_count,
                'error_count': self.error_count,
                'consecutive_errors': self.consecutive_errors,
                'whitelist_ip': self.oculus_config['whitelist_ip']
            }
        else:
            stats = {
                'mode': 'multi',
                'pool_count': self.pool_count,
                'whitelist_ip': self.oculus_config['whitelist_ip'],
                'pools': {}
            }
            
            for pool_name, pool_data in self.region_pools.items():
                performance = pool_data['performance']
                stats['pools'][pool_name] = {
                    'region': pool_data['region'],
                    'proxy_count': len(pool_data['proxies']),
                    'active': pool_data['active'],
                    'success_count': performance['success_count'],
                    'error_count': performance['error_count'],
                    'consecutive_errors': performance['consecutive_errors'],
                    'requests_made': self.pool_requests[pool_name]
                }
            
            return stats
    
    def cleanup(self):
        """Cleanup resources"""
        if self.mode == "single":
            with self._lock:
                self.proxy_pool.clear()
        else:
            for pool_data in self.region_pools.values():
                pool_data['proxies'].clear()
        
        self.logger.info("🧹 Proxy manager cleaned up")


def create_proxy_manager(mode: str = "single", **kwargs) -> OculusProxyManager:
    """
    Factory function to create proxy manager
    
    Args:
        mode: "single" or "multi"
        **kwargs: Additional arguments for proxy manager
    
    Returns:
        OculusProxyManager instance
    """
    return OculusProxyManager(mode=mode, **kwargs)