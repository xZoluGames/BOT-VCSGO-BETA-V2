"""
Oculus Proxy Manager - BOT-vCSGO-Beta V2 (VERSIÓN SEGURA)
Sistema universal de gestión de proxies con credenciales desde variables de entorno

Mejoras de seguridad:
- Credenciales cargadas desde variables de entorno
- Sin tokens hardcodeados
- Detección automática de IP con fallback configurable
"""

import json
import time
import random
import logging
import requests
import os
from typing import List, Dict, Optional, Union
from threading import Lock
from collections import defaultdict


class SecureOculusProxyManager:
    """
    Gestor de proxies SEGURO para Oculus Proxies API
    
    Carga credenciales desde variables de entorno:
    - OCULUS_AUTH_TOKEN: Token de autenticación
    - OCULUS_ORDER_TOKEN: Token de orden
    - OCULUS_WHITELIST_IP: IP whitelist (opcional)
    """
    
    def __init__(self, mode: str = "single", pool_count: int = 1, proxies_per_pool: int = 1000):
        """
        Initialize Secure Oculus Proxy Manager
        
        Args:
            mode: "single" for individual requests, "multi" for batch operations
            pool_count: Number of pools for multi mode (ignored in single mode)
            proxies_per_pool: Number of proxies per pool
        """
        self.logger = logging.getLogger('SecureOculusProxyManager')
        self.mode = mode
        self.pool_count = pool_count if mode == "multi" else 1
        self.proxies_per_pool = proxies_per_pool
        self._lock = Lock()
        
        # Cargar configuración desde variables de entorno
        self._load_secure_config()
        
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
        
        # Auto-detect IP if not whitelisted
        if not self.oculus_config['whitelist_ip']:
            self._auto_detect_ip()
        
        # Initialize proxy pools
        self._initialize_pools()
    
    def _load_secure_config(self):
        """Carga configuración de forma segura desde variables de entorno"""
        # Cargar tokens desde variables de entorno
        auth_token = os.getenv('OCULUS_AUTH_TOKEN')
        order_token = os.getenv('OCULUS_ORDER_TOKEN')
        
        if not auth_token or not order_token:
            self.logger.error("❌ OCULUS_AUTH_TOKEN y OCULUS_ORDER_TOKEN son requeridos!")
            self.logger.error("Configura las variables de entorno o archivo .env")
            raise ValueError("Credenciales de Oculus Proxy no configuradas")
        
        # Cargar IP whitelist opcional
        whitelist_ip_str = os.getenv('OCULUS_WHITELIST_IP', '')
        whitelist_ip = [ip.strip() for ip in whitelist_ip_str.split(',') if ip.strip()]
        
        self.oculus_config = {
            'auth_token': auth_token,
            'order_token': order_token,
            'whitelist_ip': whitelist_ip,
            'api_url': 'https://api.oculusproxies.com/v1/configure/proxy/getProxies'
        }
        
        self.logger.info("✅ Configuración de Oculus cargada de forma segura")
        
        # No mostrar tokens en logs
        self.logger.debug(f"Auth token presente: {'Sí' if auth_token else 'No'}")
        self.logger.debug(f"Order token presente: {'Sí' if order_token else 'No'}")
        if whitelist_ip:
            self.logger.debug(f"IP whitelist configurada: {len(whitelist_ip)} IPs")
    
    def _init_single_mode(self):
        """Initialize single pool mode configuration"""
        self.current_region = random.choice(self.available_regions)
        self.proxy_pool = []
        self.refresh_count = 0
        self.error_count = 0
        self.consecutive_errors = 0
        self.logger.info(f"🔧 Single mode initialized with region: {self.current_region}")
    
    def _init_multi_mode(self):
        """Initialize multi pool mode configuration"""
        self.region_pools = {}
        self.pool_requests = defaultdict(int)
        self.consecutive_pool_errors = defaultdict(int)
        self.logger.info(f"🔧 Multi mode initialized with {self.pool_count} pools")
    
    def _auto_detect_ip(self):
        """Auto-detect current IP and add to whitelist"""
        try:
            self.logger.info("🔍 Auto-detecting IP address...")
            
            # Try multiple services for redundancy
            ip_services = [
                'https://api.ipify.org?format=json',
                'https://ipapi.co/json/',
                'http://ip-api.com/json/'
            ]
            
            detected_ip = None
            for service in ip_services:
                try:
                    response = requests.get(service, timeout=5)
                    data = response.json()
                    
                    # Extract IP based on service response format
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
                # Usar fallback desde variable de entorno si está configurado
                fallback_ip = os.getenv('FALLBACK_IP', '127.0.0.1')
                self.oculus_config['whitelist_ip'] = [fallback_ip]
                self.logger.warning(f"⚠️ Auto-detection failed, using fallback IP: {fallback_ip}")
                return fallback_ip
                
        except Exception as e:
            fallback_ip = os.getenv('FALLBACK_IP', '127.0.0.1')
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
        """Initialize multiple proxy pools"""
        self.logger.info(f"🔄 Initializing {self.pool_count} proxy pools...")
        
        # Select random regions
        selected_regions = random.sample(self.available_regions, min(self.pool_count, len(self.available_regions)))
        
        for i, region in enumerate(selected_regions, 1):
            pool_name = f'pool_{i}'
            self.region_pools[pool_name] = {
                'region': region,
                'proxies': [],
                'active': True,
                'last_refresh': 0,
                'performance': {
                    'success_count': 0,
                    'error_count': 0,
                    'consecutive_errors': 0
                }
            }
            
            self.logger.info(f"Loading {region.upper()} pool ({pool_name})...")
            proxies = self._load_proxies_for_region(region, self.proxies_per_pool)
            
            if proxies:
                self.region_pools[pool_name]['proxies'] = proxies
                self.region_pools[pool_name]['last_refresh'] = time.time()
                self.logger.info(f"✅ {pool_name.upper()}: {len(proxies)} proxies loaded for {region.upper()}")
            else:
                self.logger.warning(f"❌ {pool_name.upper()}: Failed to load proxies for {region.upper()}")
                self.region_pools[pool_name]['active'] = False
    
    def get_proxy(self) -> Optional[str]:
        """Get a proxy based on current mode"""
        if self.mode == "single":
            return self._get_single_proxy()
        else:
            return self._get_multi_proxy()
    
    def _get_single_proxy(self) -> Optional[str]:
        """Get proxy in single mode"""
        with self._lock:
            if not self.proxy_pool:
                self.logger.warning("No proxies available, refreshing pool...")
                self._refresh_single_pool()
            
            if self.proxy_pool:
                return random.choice(self.proxy_pool)
            
            return None
    
    def _get_multi_proxy(self) -> Optional[str]:
        """Get proxy from multi-pool with intelligent selection"""
        with self._lock:
            # Get active pools
            active_pools = [(name, data) for name, data in self.region_pools.items() 
                          if data['active'] and data['proxies']]
            
            if not active_pools:
                self.logger.warning("No active pools available")
                return None
            
            # Select pool with best performance
            pool_name, pool_data = min(active_pools, 
                                      key=lambda x: x[1]['performance']['consecutive_errors'])
            
            # Track usage
            self.pool_requests[pool_name] += 1
            
            # Return random proxy from selected pool
            return random.choice(pool_data['proxies'])
    
    def _refresh_single_pool(self):
        """Refresh single proxy pool with new region"""
        # Select new region
        old_region = self.current_region
        self.current_region = random.choice([r for r in self.available_regions if r != old_region])
        
        self.logger.info(f"🔄 Refreshing pool: {old_region.upper()} → {self.current_region.upper()}")
        
        # Load new proxies
        proxies = self._load_proxies_for_region(self.current_region, self.proxies_per_pool)
        
        if proxies:
            self.proxy_pool = proxies
            self.refresh_count += 1
            self.consecutive_errors = 0
            self.logger.info(f"✅ Pool refreshed: {len(proxies)} proxies from {self.current_region.upper()}")
        else:
            self.logger.error(f"❌ Failed to refresh pool for {self.current_region.upper()}")
    
    def report_success(self, proxy: str = None):
        """Report successful proxy usage"""
        if self.mode == "single":
            self.consecutive_errors = 0
        else:
            # Find which pool the proxy belongs to
            for pool_name, pool_data in self.region_pools.items():
                if proxy in pool_data['proxies']:
                    pool_data['performance']['success_count'] += 1
                    pool_data['performance']['consecutive_errors'] = 0
                    break
    
    def report_failure(self, proxy: str = None):
        """Report proxy failure"""
        if self.mode == "single":
            self.error_count += 1
            self.consecutive_errors += 1
            
            # Refresh pool after threshold
            if self.consecutive_errors >= 5:
                self.logger.warning(f"Too many consecutive errors ({self.consecutive_errors}), refreshing pool...")
                self._refresh_single_pool()
        else:
            # Find which pool the proxy belongs to
            for pool_name, pool_data in self.region_pools.items():
                if proxy in pool_data['proxies']:
                    performance = pool_data['performance']
                    performance['error_count'] += 1
                    performance['consecutive_errors'] += 1
                    
                    # Disable pool if too many errors
                    if performance['consecutive_errors'] >= 10:
                        self.logger.warning(f"Disabling {pool_name} due to errors")
                        pool_data['active'] = False
                        self._refresh_pool(pool_name)
                    break
    
    def _refresh_pool(self, pool_name: str):
        """Refresh a specific pool with new region"""
        pool_data = self.region_pools.get(pool_name)
        if not pool_data:
            return
        
        # Select new region
        old_region = pool_data['region']
        used_regions = [p['region'] for p in self.region_pools.values()]
        available = [r for r in self.available_regions if r not in used_regions]
        
        if not available:
            available = self.available_regions
        
        new_region = random.choice(available)
        
        self.logger.info(f"🔄 Refreshing {pool_name}: {old_region.upper()} → {new_region.upper()}")
        
        # Load new proxies
        proxies = self._load_proxies_for_region(new_region, self.proxies_per_pool)
        
        if proxies:
            pool_data['region'] = new_region
            pool_data['proxies'] = proxies
            pool_data['last_refresh'] = time.time()
            pool_data['active'] = True
            pool_data['performance'] = {
                'success_count': 0,
                'error_count': 0,
                'consecutive_errors': 0
            }
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


def create_secure_proxy_manager(mode: str = "single", **kwargs) -> SecureOculusProxyManager:
    """
    Factory function to create secure proxy manager
    
    Args:
        mode: "single" or "multi"
        **kwargs: Additional arguments for proxy manager
    
    Returns:
        SecureOculusProxyManager instance
    """
    return SecureOculusProxyManager(mode=mode, **kwargs)