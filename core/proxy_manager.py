#!/usr/bin/env python3
"""
Proxy Manager - Sistema unificado de gestión de proxies para BOT-VCSGO-BETA-V2

Este módulo proporciona un sistema robusto y reutilizable para la gestión de proxies
que implementa el sistema de rotación desarrollado en steam_listing_scraper.py

Características principales:
- Proxy rotation inteligente (primera solicitud directa, siguientes con proxies)
- Pool de proxies optimizado con regiones confiables
- Manejo automático de errores y rotación de regiones
- Performance tracking por pool
- Integración simple con cualquier scraper

Uso básico:
    proxy_manager = ProxyManager()
    proxies_dict = proxy_manager.get_proxy_for_request()
    proxy_manager.record_request_result(success=True, response_time=1.2)

Autor: Claude Code
Versión: 1.0.0
"""

import requests
import json
import time
import random
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from threading import Lock
import threading


@dataclass
class PoolPerformance:
    """Métricas de rendimiento de un pool de proxies"""
    success_count: int = 0
    error_count: int = 0
    consecutive_errors: int = 0
    last_error_time: float = 0
    response_times: List[float] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calcula la tasa de éxito del pool"""
        total = self.success_count + self.error_count
        return (self.success_count / total) * 100 if total > 0 else 0
    
    @property
    def avg_response_time(self) -> float:
        """Calcula el tiempo promedio de respuesta"""
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0
    
    @property
    def performance_score(self) -> float:
        """Calcula un score de rendimiento (0-100)"""
        return self.success_rate - (self.avg_response_time * 3) - (self.consecutive_errors * 15)


@dataclass
class ProxyPool:
    """Representa un pool de proxies de una región específica"""
    region: str
    proxies: List[str] = field(default_factory=list)
    performance: PoolPerformance = field(default_factory=PoolPerformance)
    active: bool = True
    last_refresh: float = 0


class ProxyManager:
    """
    Gestor unificado de proxies con rotación inteligente
    
    Implementa el sistema desarrollado en steam_listing_scraper.py de forma
    reutilizable para cualquier scraper del proyecto.
    """
    
    # Regiones optimizadas (Tier 1 + Tier 2 = las más confiables)
    RELIABLE_REGIONS = [
        'us', 'gb', 'de', 'ca', 'au', 'fr', 'nl', 'jp', 'sg', 'br', 
        'mx', 'in', 'kr', 'hk', 'tw', 'pl', 'it', 'es', 'ch', 'se', 
        'no', 'dk', 'fi', 'at', 'be', 'ie', 'pt', 'ru', 'tr', 'za', 
        'eg', 'ae', 'sa', 'th', 'my', 'id', 'ph', 'vn', 'nz'
    ]
    
    def __init__(self, 
                 oculus_auth_token: str = '05bd54d2-e21c-41db-bf74-d12e460210a9',
                 oculus_order_token: str = 'oc_21790259',
                 whitelist_ip: List[str] = None,
                 num_pools: int = 5,
                 proxies_per_pool: int = 10000,
                 rotation_pool_size: int = 100,
                 logger: Optional[logging.Logger] = None):
        """
        Inicializa el gestor de proxies
        
        Args:
            oculus_auth_token: Token de autenticación de Oculus Proxies
            oculus_order_token: Token de orden de Oculus Proxies
            whitelist_ip: Lista de IPs en whitelist
            num_pools: Número de pools de proxies (default: 5)
            proxies_per_pool: Proxies por pool (default: 10000)
            rotation_pool_size: Tamaño del pool de rotación (default: 100)
            logger: Logger personalizado
        """
        self.oculus_config = {
            'auth_token': oculus_auth_token,
            'order_token': oculus_order_token,
            'whitelist_ip': whitelist_ip or ['181.127.133.115'],
            'api_url': 'https://api.oculusproxies.com/v1/configure/proxy/getProxies'
        }
        
        self.num_pools = num_pools
        self.proxies_per_pool = proxies_per_pool
        self.rotation_pool_size = rotation_pool_size
        
        # Configurar logging
        self.logger = logger or logging.getLogger(f'ProxyManager')
        
        # Pools de proxies por región
        self.region_pools: Dict[str, ProxyPool] = {}
        
        # Sistema de rotación
        self.proxy_pool: List[str] = []  # Pool de proxies para rotación
        self.proxy_rotation_enabled = False  # Se activa después de la primera carga
        
        # Tracking de performance
        self.pool_error_threshold = 4  # Cambiar región después de N errores consecutivos
        self.current_request_count = 0
        self.last_used_pool = None
        
        # Thread safety
        self._lock = Lock()
        
        # Inicializar pools
        self._initialize_pools()
    
    def _initialize_pools(self):
        """Inicializa los pools de proxies con regiones aleatorias"""
        self.logger.info(f"🔄 Inicializando {self.num_pools} pools de proxies...")
        
        # Seleccionar regiones aleatorias de las confiables
        selected_regions = random.sample(self.RELIABLE_REGIONS, self.num_pools)
        
        for i, region in enumerate(selected_regions, 1):
            pool_name = f'pool_{i}'
            self.region_pools[pool_name] = ProxyPool(region=region)
            
            self.logger.info(f"Cargando {region.upper()} pool ({pool_name})...")
            proxies = self._load_fresh_proxies_for_region(region, self.proxies_per_pool)
            
            if proxies:
                self.region_pools[pool_name].proxies = proxies
                self.region_pools[pool_name].last_refresh = time.time()
                self.logger.info(f"✅ {pool_name.upper()}: {len(proxies)} proxies cargados para {region.upper()}")
            else:
                self.logger.warning(f"❌ {pool_name.upper()}: Falló la carga de proxies para {region.upper()}")
                self.region_pools[pool_name].active = False
        
        total_proxies = sum(len(pool.proxies) for pool in self.region_pools.values())
        active_regions = [pool.region.upper() for pool in self.region_pools.values() if pool.active]
        
        self.logger.info(f"🌍 PROXY MANAGER INICIALIZADO: {total_proxies} proxies totales")
        self.logger.info(f"🚀 Regiones activas: {', '.join(active_regions)}")
        self.logger.info(f"🎯 Pool de rotación: {len(self.RELIABLE_REGIONS)} regiones disponibles")
    
    def _load_fresh_proxies_for_region(self, region: str, count: int) -> List[str]:
        """
        Carga proxies frescos de la API de Oculus para una región específica
        Implementa rotación de proxies para evitar bloqueos
        """
        try:
            url = self.oculus_config['api_url']
            
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
            
            # Implementar rotación de proxies
            proxy_to_use = None
            if self.proxy_rotation_enabled and self.proxy_pool:
                proxy_to_use = random.choice(self.proxy_pool)
                proxies_dict = {"http": proxy_to_use, "https": proxy_to_use}
                self.logger.debug(f"Usando proxy para región {region}: {proxy_to_use[:50]}...")
            else:
                proxies_dict = None
                self.logger.debug(f"Conexión directa para región {region} (primera carga)")
            
            response = requests.post(url, headers=headers, data=payload, 
                                   timeout=30, proxies=proxies_dict)
            response.raise_for_status()
            
            # Procesar respuesta
            proxy_data = response.json()
            proxies = []
            
            if isinstance(proxy_data, dict) and 'proxies' in proxy_data:
                for proxy_info in proxy_data['proxies']:
                    if isinstance(proxy_info, str):
                        parsed_proxy = self._parse_oculus_proxy(proxy_info)
                        if parsed_proxy:
                            proxies.append(parsed_proxy)
            elif isinstance(proxy_data, list):
                for raw_proxy in proxy_data:
                    if isinstance(raw_proxy, str):
                        parsed_proxy = self._parse_oculus_proxy(raw_proxy)
                        if parsed_proxy:
                            proxies.append(parsed_proxy)
            elif isinstance(proxy_data, str):
                parsed_proxy = self._parse_oculus_proxy(proxy_data)
                if parsed_proxy:
                    proxies = [parsed_proxy]
            
            # Actualizar pool de rotación
            self._update_rotation_pool(proxies)
            
            return proxies
            
        except Exception as e:
            self.logger.error(f"Error cargando {count} proxies para región {region}: {e}")
            return []
    
    def _parse_oculus_proxy(self, raw_proxy: str) -> Optional[str]:
        """
        Parsea formato de proxy de Oculus a formato estándar
        
        Convierte: proxy.oculus-proxy.com:31114:username:password
        A: http://username:password@proxy.oculus-proxy.com:31114
        """
        try:
            parts = raw_proxy.split(':')
            if len(parts) == 4:
                host, port, username, password = parts
                return f"http://{username}:{password}@{host}:{port}"
            else:
                self.logger.warning(f"Formato de proxy inesperado: {raw_proxy}")
                return None
        except Exception as e:
            self.logger.error(f"Error parseando proxy {raw_proxy}: {e}")
            return None
    
    def _update_rotation_pool(self, new_proxies: List[str]):
        """Actualiza el pool de rotación con nuevos proxies"""
        with self._lock:
            if new_proxies and not self.proxy_rotation_enabled:
                # Primera carga exitosa - activar rotación
                self.proxy_pool.extend(new_proxies[:self.rotation_pool_size])
                self.proxy_rotation_enabled = True
                self.logger.info(f"🔄 ROTACIÓN DE PROXIES ACTIVADA: {len(self.proxy_pool)} proxies disponibles")
            elif new_proxies and self.proxy_rotation_enabled:
                # Agregar nuevos proxies al pool
                new_unique_proxies = [p for p in new_proxies[:50] if p not in self.proxy_pool]
                self.proxy_pool.extend(new_unique_proxies)
                
                # Limitar tamaño del pool
                if len(self.proxy_pool) > 500:
                    self.proxy_pool = self.proxy_pool[-500:]
                
                self.logger.debug(f"Pool de rotación actualizado: {len(self.proxy_pool)} proxies")
    
    def get_proxy_for_request(self) -> Optional[Dict[str, str]]:
        """
        Obtiene un proxy para usar en la siguiente solicitud
        
        Returns:
            Dict con formato {"http": proxy_url, "https": proxy_url} o None para conexión directa
        """
        with self._lock:
            # Seleccionar el mejor pool
            best_pool_name = self._get_best_performing_pool()
            if not best_pool_name:
                return None
            
            pool = self.region_pools[best_pool_name]
            if not pool.proxies:
                return None
            
            # Seleccionar proxy aleatorio del mejor pool
            proxy = random.choice(pool.proxies)
            self.last_used_pool = best_pool_name
            self.current_request_count += 1
            
            return {"http": proxy, "https": proxy}
    
    def _get_best_performing_pool(self) -> Optional[str]:
        """Obtiene el pool con mejor rendimiento"""
        active_pools = [(name, pool) for name, pool in self.region_pools.items() 
                       if pool.active and pool.proxies]
        
        if not active_pools:
            return None
        
        # Calcular scores y seleccionar el mejor
        pool_scores = []
        for pool_name, pool in active_pools:
            score = pool.performance.performance_score
            # Dar ventaja a pools no usados recientemente
            if pool.performance.success_count + pool.performance.error_count == 0:
                score = 50.0  # Score neutral para pools nuevos
            
            pool_scores.append((pool_name, score))
        
        # Ordenar por score y retornar el mejor
        pool_scores.sort(key=lambda x: x[1], reverse=True)
        return pool_scores[0][0]
    
    def record_request_result(self, success: bool, response_time: float = 0):
        """
        Registra el resultado de una solicitud para tracking de performance
        
        Args:
            success: Si la solicitud fue exitosa
            response_time: Tiempo de respuesta en segundos
        """
        if not self.last_used_pool:
            return
        
        with self._lock:
            pool = self.region_pools[self.last_used_pool]
            performance = pool.performance
            
            if success:
                performance.success_count += 1
                performance.response_times.append(response_time)
                performance.consecutive_errors = 0
                
                # Mantener solo los últimos 50 tiempos de respuesta
                if len(performance.response_times) > 50:
                    performance.response_times = performance.response_times[-50:]
            else:
                performance.error_count += 1
                performance.consecutive_errors += 1
                performance.last_error_time = time.time()
                
                # Verificar si necesita rotación de región
                if performance.consecutive_errors >= self.pool_error_threshold:
                    self.logger.warning(f"🚨 {self.last_used_pool.upper()}: {performance.consecutive_errors} errores consecutivos")
                    self._rotate_pool_region(self.last_used_pool)
    
    def _rotate_pool_region(self, pool_name: str):
        """Rota la región de un pool que tiene muchos errores"""
        pool = self.region_pools[pool_name]
        current_region = pool.region
        
        # Obtener regiones no utilizadas
        used_regions = [p.region for p in self.region_pools.values()]
        available_regions = [r for r in self.RELIABLE_REGIONS if r not in used_regions]
        
        if available_regions:
            new_region = random.choice(available_regions)
            self.logger.warning(f"🔄 ROTACIÓN DE REGIÓN: {pool_name.upper()} {current_region.upper()} → {new_region.upper()}")
            
            # Actualizar pool
            pool.region = new_region
            pool.performance = PoolPerformance()  # Reset performance
            
            # Cargar nuevos proxies
            fresh_proxies = self._load_fresh_proxies_for_region(new_region, self.proxies_per_pool)
            if fresh_proxies:
                pool.proxies = fresh_proxies
                pool.active = True
                pool.last_refresh = time.time()
                self.logger.info(f"✅ {pool_name.upper()}: {len(fresh_proxies)} proxies cargados para {new_region.upper()}")
            else:
                self.logger.warning(f"❌ {pool_name.upper()}: Falló la carga para {new_region.upper()}")
                pool.active = False
        else:
            self.logger.warning(f"⚠️ {pool_name.upper()}: No hay regiones disponibles para rotación")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del gestor de proxies"""
        with self._lock:
            total_proxies = sum(len(pool.proxies) for pool in self.region_pools.values())
            active_pools = sum(1 for pool in self.region_pools.values() if pool.active)
            
            pool_stats = {}
            for name, pool in self.region_pools.items():
                pool_stats[name] = {
                    'region': pool.region.upper(),
                    'proxies_count': len(pool.proxies),
                    'active': pool.active,
                    'success_rate': round(pool.performance.success_rate, 1),
                    'avg_response_time': round(pool.performance.avg_response_time, 2),
                    'consecutive_errors': pool.performance.consecutive_errors,
                    'performance_score': round(pool.performance.performance_score, 1)
                }
            
            return {
                'total_proxies': total_proxies,
                'active_pools': active_pools,
                'rotation_enabled': self.proxy_rotation_enabled,
                'rotation_pool_size': len(self.proxy_pool),
                'total_requests': self.current_request_count,
                'pools': pool_stats
            }
    
    def refresh_all_pools(self):
        """Refresca todos los pools con proxies nuevos"""
        self.logger.info("🔄 Refrescando todos los pools de proxies...")
        
        for pool_name, pool in self.region_pools.items():
            if pool.active:
                fresh_proxies = self._load_fresh_proxies_for_region(pool.region, self.proxies_per_pool)
                if fresh_proxies:
                    pool.proxies = fresh_proxies
                    pool.last_refresh = time.time()
                    self.logger.info(f"✅ {pool_name.upper()}: {len(fresh_proxies)} proxies refrescados")
                else:
                    self.logger.warning(f"❌ {pool_name.upper()}: Falló el refrescado")
    
    def close(self):
        """Limpieza del gestor de proxies"""
        self.logger.info("Cerrando ProxyManager...")
        with self._lock:
            # Generar reporte final
            stats = self.get_stats()
            self.logger.info(f"📊 ESTADÍSTICAS FINALES:")
            self.logger.info(f"   Total de proxies: {stats['total_proxies']}")
            self.logger.info(f"   Pools activos: {stats['active_pools']}/{len(self.region_pools)}")
            self.logger.info(f"   Total solicitudes: {stats['total_requests']}")
            
            # Limpiar datos
            self.region_pools.clear()
            self.proxy_pool.clear()


# Función de conveniencia para uso simple
def create_proxy_manager(**kwargs) -> ProxyManager:
    """
    Crea una instancia de ProxyManager con configuración por defecto
    
    Args:
        **kwargs: Argumentos para personalizar el ProxyManager
    
    Returns:
        Instancia configurada de ProxyManager
    """
    return ProxyManager(**kwargs)


# Context manager para uso automático
class ProxyManagerContext:
    """Context manager para uso automático del ProxyManager"""
    
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.proxy_manager = None
    
    def __enter__(self) -> ProxyManager:
        self.proxy_manager = ProxyManager(**self.kwargs)
        return self.proxy_manager
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.proxy_manager:
            self.proxy_manager.close()


if __name__ == "__main__":
    # Ejemplo de uso básico
    logging.basicConfig(level=logging.INFO)
    
    # Crear gestor de proxies
    proxy_manager = ProxyManager(num_pools=3, proxies_per_pool=100)
    
    try:
        # Simular algunas solicitudes
        for i in range(10):
            proxy_dict = proxy_manager.get_proxy_for_request()
            if proxy_dict:
                print(f"Solicitud {i+1}: Usando proxy")
                # Simular éxito/fallo aleatorio
                success = random.choice([True, True, True, False])  # 75% éxito
                response_time = random.uniform(0.5, 2.0)
                proxy_manager.record_request_result(success, response_time)
            else:
                print(f"Solicitud {i+1}: Conexión directa")
        
        # Mostrar estadísticas
        stats = proxy_manager.get_stats()
        print(f"\n📊 Estadísticas: {stats}")
        
    finally:
        proxy_manager.close()