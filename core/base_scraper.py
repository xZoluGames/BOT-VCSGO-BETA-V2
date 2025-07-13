"""
BaseScraper - Clase base simplificada para BOT-vCSGO-Beta V2

Versión simplificada enfocada en uso personal:
- Mantiene funcionalidades core de scraping
- Elimina dependencias empresariales complejas  
- Usar orjson para performance
- Sistema de proxy simplificado
- Enfoque en simplicidad y mantenibilidad
"""

import os
import requests
import orjson
import time
import random
import socket
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from functools import lru_cache
import threading
import asyncio
import aiofiles

# Importar el config manager y logger
from .config_manager import get_config_manager
from .logger import get_scraper_logger, get_unified_logger

# Importar servicios opcionales de BOT-vCSGO-Beta si están disponibles
try:
    from .cache_service import get_cache_service
except ImportError:
    get_cache_service = None

try:
    from .profitability_engine import ProfitabilityEngine
except ImportError:
    ProfitabilityEngine = None

try:
    from .proxy_manager import ProxyManager
except ImportError:
    ProxyManager = None

class BaseScraper(ABC):
    """
    Clase base mejorada para todos los scrapers de BOT-vCSGO-Beta V2
    
    Funcionalidades mejoradas:
    - Manejo unificado de proxies con rotación inteligente
    - Rate limiting avanzado
    - Retry logic con backoff exponencial
    - Guardado en JSON con orjson (sincrónico y asíncrono)
    - Cache service integrado
    - Estadísticas de ejecución detalladas
    - Headers aleatorios
    - Validación robusta de datos
    - Context manager para limpieza automática
    """
    
    def __init__(self, 
                 platform_name: str,
                 use_proxy: Optional[bool] = None,
                 proxy_list: Optional[List[str]] = None,
                 config: Optional[Dict[str, Any]] = None,
                 use_advanced_proxy_manager: bool = False):
        """
        Inicializa el scraper base mejorado
        
        Args:
            platform_name: Nombre de la plataforma (ej: 'waxpeer', 'csdeals')
            use_proxy: Si usar proxy o no (None = usar configuración por defecto)
            proxy_list: Lista de proxies (formato ip:puerto o protocolo://ip:puerto)
            config: Configuración personalizada (sobrescribe la por defecto)
            use_advanced_proxy_manager: Si usar el ProxyManager avanzado (default: False)
        """
        self.platform_name = platform_name.lower()
        
        # Inicializar config manager
        self.config_manager = get_config_manager()
        
        # Obtener configuración del scraper
        scraper_config = self.config_manager.get_scraper_config(platform_name)
        
        # Determinar configuración de proxy
        if use_proxy is not None:
            self.use_proxy = use_proxy
        else:
            # Usar configuración del scraper o global
            self.use_proxy = scraper_config.get('use_proxy', False)
            if not self.use_proxy:
                # Verificar configuración global de proxy
                proxy_config = self.config_manager.get_proxy_config()
                self.use_proxy = proxy_config.get('enabled', False)
        
        self.proxy_list = proxy_list or self.config_manager.get_proxy_config()
        self.current_proxy_index = 0
        self.proxy_failures = {}  # Track failed proxies
        
        # Inicializar ProxyManager avanzado si está habilitado
        self.use_advanced_proxy_manager = use_advanced_proxy_manager
        self.proxy_manager = None
        if self.use_advanced_proxy_manager and ProxyManager and self.use_proxy:
            try:
                self.proxy_manager = ProxyManager(
                    num_pools=3,  # Menos pools para scrapers normales
                    proxies_per_pool=1000,  # Menos proxies por pool
                    rotation_pool_size=50,  # Pool de rotación más pequeño
                    logger=self.logger
                )
                self.logger.info("ProxyManager avanzado inicializado")
            except Exception as e:
                self.logger.warning(f"Error inicializando ProxyManager: {e}")
                self.proxy_manager = None
        
        # Configuración base desde config manager
        self.config = {
            'timeout': scraper_config.get('timeout_seconds', 30),
            'max_retries': scraper_config.get('max_retries', 5),
            'retry_delay': 2,
            'interval': scraper_config.get('interval_seconds', 60),
            'headers': scraper_config.get('headers', {}),
            'use_cache': True,
            'cache_ttl': 300,  # 5 minutos
            'validate_ssl': True,
            'follow_redirects': True,
            'max_proxy_failures': 3,
            'api_url': scraper_config.get('api_url', ''),
            'enabled': scraper_config.get('enabled', True)
        }
        
        # Aplicar configuración personalizada
        if config:
            self.config.update(config)
        
        # Obtener API key si existe
        self.api_key = self.config_manager.get_api_key(platform_name)
        
        # Configurar logging usando sistema unificado
        self.logger = get_scraper_logger(platform_name)
        self.unified_logger = get_unified_logger()
        
        # Headers por defecto
        self.headers = {
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            **self.config.get('headers', {})
        }
        
        # Estadísticas de ejecución mejoradas
        self.stats = {
            'requests_made': 0,
            'requests_failed': 0,
            'items_fetched': 0,
            'last_run': None,
            'last_error': None,
            'proxy_failures': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_runtime': 0,
            'average_response_time': 0,
            'success_rate': 0.0
        }
        
        # Sesión de requests con connection pooling
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Configurar retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=retry_strategy
        )
        
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Configurar cache service - usar avanzado si está disponible
        if get_cache_service:
            try:
                self.cache_service = get_cache_service()
                self.logger.info("Usando cache service avanzado de BOT-vCSGO-Beta")
            except Exception as e:
                self.logger.warning(f"Cache service avanzado no disponible: {e}")
                self.cache_service = self._setup_cache_service()
        else:
            self.cache_service = self._setup_cache_service()
        
        # Configurar profitability engine si está disponible
        self.profitability_engine = None
        if ProfitabilityEngine:
            try:
                self.profitability_engine = ProfitabilityEngine()
                self.logger.info("Profitability engine disponible")
            except Exception as e:
                self.logger.warning(f"Profitability engine no disponible: {e}")
        
        # Crear directorios necesarios
        self.data_dir = Path(__file__).parent.parent / "data"
        self.logs_dir = Path(__file__).parent.parent / "logs"
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Threading lock para operaciones thread-safe
        self._lock = threading.Lock()
        
        self.logger.info(
            f"Scraper {platform_name} inicializado "
            f"(habilitado: {'Sí' if self.config['enabled'] else 'No'}, "
            f"proxy: {'Sí' if self.use_proxy else 'No'}, "
            f"cache: {'Sí' if self.cache_service else 'No'}, "
            f"API key: {'Sí' if self.api_key else 'No'})"
        )
    
    def get_headers_with_auth(self) -> Dict[str, str]:
        """
        Obtiene headers con autenticación si hay API key disponible
        
        Returns:
            Headers con autenticación configurada
        """
        headers = self.headers.copy()
        
        if self.api_key:
            # Obtener configuración de la API key
            api_keys_config = self.config_manager.get_api_keys()
            platform_config = api_keys_config.get(self.platform_name, {})
            
            auth_type = platform_config.get('type', 'bearer')
            header_name = platform_config.get('header_name', 'Authorization')
            
            if auth_type == 'bearer':
                headers[header_name] = f"Bearer {self.api_key}"
            elif auth_type == 'api_key':
                headers[header_name] = self.api_key
            else:
                headers['Authorization'] = f"Bearer {self.api_key}"
        
        return headers
    
    def _setup_cache_service(self):
        """
        Configura el servicio de cache simple
        
        Returns:
            Cache service o None si no está disponible
        """
        try:
            # Cache simple en memoria usando lru_cache
            from functools import lru_cache
            
            class SimpleCache:
                def __init__(self, maxsize=1000, ttl=300):
                    self.cache = {}
                    self.timestamps = {}
                    self.maxsize = maxsize
                    self.ttl = ttl
                    self._lock = threading.Lock()
                
                def get(self, key):
                    with self._lock:
                        if key in self.cache:
                            # Verificar TTL
                            if time.time() - self.timestamps[key] < self.ttl:
                                return self.cache[key]
                            else:
                                # Expirado, remover
                                del self.cache[key]
                                del self.timestamps[key]
                    return None
                
                def set(self, key, value, ttl=None):
                    with self._lock:
                        # Limpiar cache si está lleno
                        if len(self.cache) >= self.maxsize:
                            oldest_key = min(self.timestamps.keys(), key=lambda k: self.timestamps[k])
                            del self.cache[oldest_key]
                            del self.timestamps[oldest_key]
                        
                        self.cache[key] = value
                        self.timestamps[key] = time.time()
            
            return SimpleCache(ttl=self.config.get('cache_ttl', 300))
        except Exception:
            return None
    
    def _get_random_user_agent(self) -> str:
        """Retorna un User-Agent aleatorio para parecer más humano"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        return random.choice(user_agents)
    
    def _get_next_proxy(self) -> Optional[str]:
        """Obtiene el siguiente proxy de la lista de forma rotatoria con selección inteligente"""
        if not self.use_proxy or not self.proxy_list:
            return None
        
        max_attempts = len(self.proxy_list)
        attempts = 0
        
        while attempts < max_attempts:
            proxy = self.proxy_list[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
            
            # Verificar si el proxy no ha fallado recientemente
            failures = self.proxy_failures.get(proxy, 0)
            if failures < self.config.get('max_proxy_failures', 3):
                # Formatear proxy si no tiene protocolo
                if not proxy.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
                    proxy = f"http://{proxy}"
                return proxy
            
            attempts += 1
        
        # Si todos los proxies han fallado, resetear contadores y usar el primero
        self.logger.warning("Todos los proxies han fallado, reseteando contadores")
        self.proxy_failures.clear()
        return self._get_next_proxy()
    
    def _mark_proxy_failed(self, proxy: str):
        """Marca un proxy como fallido con contador inteligente"""
        with self._lock:
            self.proxy_failures[proxy] = self.proxy_failures.get(proxy, 0) + 1
            self.stats['proxy_failures'] += 1
            
            failure_count = self.proxy_failures[proxy]
            self.logger.warning(
                f"Proxy fallido: {proxy} (fallos: {failure_count}/{self.config.get('max_proxy_failures', 3)})"
            )
            
            # Si el proxy ha fallado muchas veces, considerar removerlo temporalmente
            if failure_count >= self.config.get('max_proxy_failures', 3):
                self.logger.error(f"Proxy {proxy} ha excedido el límite de fallos, será evitado")
    
    def make_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """
        Realiza una petición HTTP con reintentos y manejo de errores
        
        Args:
            url: URL para la petición
            method: Método HTTP (GET, POST)
            **kwargs: Argumentos adicionales para requests
            
        Returns:
            Response object o None si falla
        """
        max_retries = self.config['max_retries']
        retry_delay = self.config['retry_delay']
        
        for attempt in range(max_retries):
            try:
                self.stats['requests_made'] += 1
                
                # Configurar kwargs de la petición
                request_kwargs = {
                    'timeout': self.config['timeout'],
                    'allow_redirects': True,
                    'verify': True,
                    **kwargs
                }
                
                # Configurar proxy si está habilitado
                start_time = time.time()
                if self.use_proxy:
                    if self.proxy_manager:
                        # Usar ProxyManager avanzado
                        proxy_dict = self.proxy_manager.get_proxy_for_request()
                        if proxy_dict:
                            request_kwargs['proxies'] = proxy_dict
                            self.logger.debug(f"Usando ProxyManager avanzado")
                    else:
                        # Usar sistema de proxy tradicional
                        proxy = self._get_next_proxy()
                        if proxy:
                            request_kwargs['proxies'] = {
                                'http': proxy,
                                'https': proxy
                            }
                            self.logger.debug(f"Usando proxy tradicional: {proxy}")
                
                # Realizar petición
                if method.upper() == 'GET':
                    response = self.session.get(url, **request_kwargs)
                elif method.upper() == 'POST':
                    response = self.session.post(url, **request_kwargs)
                else:
                    raise ValueError(f"Método no soportado: {method}")
                
                # Verificar respuesta
                response.raise_for_status()
                
                # Registrar éxito en ProxyManager si está activo
                if self.proxy_manager:
                    response_time = time.time() - start_time
                    self.proxy_manager.record_request_result(success=True, response_time=response_time)
                
                self.logger.debug(f"Petición exitosa a {url} (intento {attempt + 1})")
                return response
                
            except requests.exceptions.RequestException as e:
                self.stats['requests_failed'] += 1
                self.stats['last_error'] = str(e)
                
                # Registrar fallo en ProxyManager si está activo
                if self.proxy_manager:
                    self.proxy_manager.record_request_result(success=False)
                
                self.logger.warning(f"Error en petición (intento {attempt + 1}/{max_retries}): {e}")
                
                # Si estamos usando proxy y falla, marcarlo como fallido y obtener otro
                if self.use_proxy and 'proxies' in request_kwargs:
                    if not self.proxy_manager:
                        # Solo manejar proxy tradicional si no está usando ProxyManager
                        self._mark_proxy_failed(request_kwargs['proxies']['http'])
                        
                        # Obtener nuevo proxy para el siguiente intento
                        new_proxy = self._get_next_proxy()
                        if new_proxy:
                            request_kwargs['proxies'] = {
                                'http': new_proxy,
                                'https': new_proxy
                            }
                            self.logger.debug(f"Cambiando a nuevo proxy: {new_proxy}")
                
                # Si es el último intento, no esperar
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)  # Backoff exponencial
                    self.logger.info(f"Esperando {wait_time} segundos antes de reintentar...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                self.logger.error(f"Error no manejado: {e}")
                self.stats['last_error'] = str(e)
        
        self.logger.error(f"Falló después de {max_retries} intentos: {url}")
        return None
    
    def save_data(self, data: List[Dict]) -> bool:
        """
        Guarda los datos en formato JSON usando orjson
        
        Args:
            data: Lista de items a guardar
            
        Returns:
            bool: True si se guardó correctamente
        """
        try:
            # Crear archivo de salida
            filename = f"{self.platform_name}_data.json"
            filepath = self.data_dir / filename
            
            # Usar orjson para mejor performance
            json_data = orjson.dumps(
                data, 
                option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS
            )
            
            with open(filepath, 'wb') as f:
                f.write(json_data)
            
            self.logger.info(f"Datos guardados en {filepath} ({len(data)} items)")
            
            # Actualizar estadísticas
            self.stats['items_fetched'] = len(data)
            return True
            
        except Exception as e:
            self.logger.error(f"Error guardando datos: {e}")
            return False
    
    def load_existing_data(self) -> List[Dict]:
        """
        Carga datos existentes del archivo JSON
        
        Returns:
            Lista de items existentes o lista vacía
        """
        try:
            filename = f"{self.platform_name}_data.json"
            filepath = self.data_dir / filename
            
            if not filepath.exists():
                return []
            
            with open(filepath, 'rb') as f:
                data = orjson.loads(f.read())
            
            self.logger.debug(f"Cargados {len(data)} items existentes")
            return data
            
        except Exception as e:
            self.logger.error(f"Error cargando datos existentes: {e}")
            return []
    
    async def save_data_async(self, data: List[Dict]) -> bool:
        """
        Versión asíncrona para guardar datos sin bloquear
        
        Args:
            data: Lista de items a guardar
            
        Returns:
            bool: True si se guardó correctamente
        """
        try:
            # Crear archivo de salida
            filename = f"{self.platform_name}_data.json"
            filepath = self.data_dir / filename
            
            # Usar aiofiles para escritura asíncrona
            json_data = orjson.dumps(
                data, 
                option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS
            )
            
            async with aiofiles.open(filepath, 'wb') as f:
                await f.write(json_data)
            
            self.logger.info(f"Datos guardados asíncronamente en {filepath} ({len(data)} items)")
            
            # Actualizar estadísticas
            self.stats['items_fetched'] = len(data)
            return True
            
        except Exception as e:
            self.logger.error(f"Error guardando datos async: {e}")
            return False
    
    def get_cached_data(self, cache_key: str, fetch_func, ttl: int = 300):
        """Obtiene datos del caché o los fetcha si no existen"""
        if self.cache_service:
            cached = self.cache_service.get(cache_key)
            if cached:
                self.stats['cache_hits'] += 1
                self.logger.debug(f"Cache hit para {cache_key}")
                return cached
            else:
                self.stats['cache_misses'] += 1
        
        # Fetch fresh data
        data = fetch_func()
        
        if data and self.cache_service:
            self.cache_service.set(cache_key, data, ttl)
        
        return data
    
    def calculate_profitability(self, items: List[Dict]) -> List[Dict]:
        """
        Calcula la rentabilidad de los items si el engine está disponible
        
        Args:
            items: Lista de items para calcular rentabilidad
            
        Returns:
            Lista de items con información de rentabilidad agregada
        """
        if not self.profitability_engine or not items:
            return items
        
        try:
            # Usar el engine de rentabilidad para procesar los items
            profitable_items = self.profitability_engine.calculate_opportunities(
                platform_data={self.platform_name: items}
            )
            
            # Agregar información de rentabilidad a cada item
            enhanced_items = []
            for item in items:
                enhanced_item = item.copy()
                
                # Buscar si este item tiene oportunidades de rentabilidad
                for opportunity in profitable_items:
                    if (opportunity.get('buy_platform') == self.platform_name and 
                        opportunity.get('item_name') == item.get('Item')):
                        enhanced_item.update({
                            'profit_margin': opportunity.get('profit_margin', 0),
                            'profit_absolute': opportunity.get('profit_absolute', 0),
                            'sell_platform': opportunity.get('sell_platform', ''),
                            'sell_price': opportunity.get('sell_price', 0),
                            'is_profitable': opportunity.get('profit_margin', 0) > 0
                        })
                        break
                
                enhanced_items.append(enhanced_item)
            
            profitable_count = sum(1 for item in enhanced_items if item.get('is_profitable', False))
            if profitable_count > 0:
                self.logger.info(f"Encontradas {profitable_count} oportunidades rentables")
            
            return enhanced_items
            
        except Exception as e:
            self.logger.error(f"Error calculando rentabilidad: {e}")
            return items
    
    @abstractmethod  
    def parse_response(self, response: requests.Response) -> List[Dict]:
        """
        Método abstracto para parsear la respuesta.
        Cada scraper implementa su propia lógica de parsing.
        
        Args:
            response: Respuesta HTTP
            
        Returns:
            Lista de items parseados
        """
        pass
    
    @abstractmethod
    def fetch_data(self) -> List[Dict]:
        """
        Método abstracto que cada scraper debe implementar.
        
        Returns:
            Lista de diccionarios con formato estandarizado:
            [
                {
                    'Item': 'nombre_del_item',
                    'Price': 'precio_numerico',
                    'URL': 'url_opcional',
                    'Platform': 'nombre_plataforma',
                    'Timestamp': 'fecha_scraping'
                },
                ...
            ]
        """
        pass
    
    def validate_item(self, item: Dict) -> bool:
        """
        Valida que un item tenga los campos requeridos
        
        Args:
            item: Diccionario con datos del item
            
        Returns:
            True si el item es válido
        """
        required_fields = ['Item', 'Price']
        
        # Verificar campos requeridos
        for field in required_fields:
            if field not in item or not item[field]:
                self.logger.warning(f"Item inválido, falta campo {field}: {item}")
                return False
        
        # Verificar que el precio sea válido
        try:
            price_str = str(item['Price']).replace(',', '.').replace('$', '').replace('€', '').strip()
            price = float(price_str)
            if price < 0:
                self.logger.warning(f"Precio negativo en item: {item}")
                return False
            elif price == 0:
                return False  # Precio 0 no es válido para trading
        except (ValueError, TypeError):
            self.logger.warning(f"Precio inválido en item: {item}")
            return False
        
        return True
    
    def run_once(self) -> List[Dict]:
        """
        Ejecuta el scraper una vez y retorna los datos
        
        Returns:
            Lista de items obtenidos
        """
        start_time = time.time()
        self.logger.info(f"Iniciando scraper {self.platform_name}")
        self.stats['last_run'] = datetime.now()
        
        try:
            # Obtener datos
            data = self.fetch_data()
            
            if data:
                # Validar items
                valid_data = [item for item in data if self.validate_item(item)]
                invalid_count = len(data) - len(valid_data)
                
                if invalid_count > 0:
                    self.logger.warning(f"Se descartaron {invalid_count} items inválidos")
                
                # Calcular rentabilidad si está disponible
                enhanced_data = self.calculate_profitability(valid_data)
                
                # Actualizar estadísticas
                self.stats['items_fetched'] = len(enhanced_data)
                
                # Guardar datos
                if enhanced_data:
                    self.save_data(enhanced_data)
                    profitable_count = sum(1 for item in enhanced_data if item.get('is_profitable', False))
                    if profitable_count > 0:
                        self.logger.info(f"Scraper completado: {len(enhanced_data)} items válidos obtenidos ({profitable_count} rentables)")
                    else:
                        self.logger.info(f"Scraper completado: {len(enhanced_data)} items válidos obtenidos")
                else:
                    self.logger.warning("No se obtuvieron items válidos")
                
                # Actualizar estadísticas de tiempo
                runtime = time.time() - start_time
                self.stats['total_runtime'] += runtime
                self.stats['average_response_time'] = runtime
                
                # Calcular tasa de éxito
                total_requests = self.stats['requests_made']
                if total_requests > 0:
                    self.stats['success_rate'] = ((total_requests - self.stats['requests_failed']) / total_requests) * 100
                
                # Registrar estadísticas usando sistema unificado
                self.unified_logger.log_scraper_stats(self.platform_name, self.stats)
                
                # Registrar métricas de rendimiento
                if runtime > 0:
                    performance_metrics = {
                        'response_time': runtime,
                        'items_per_second': len(valid_data) / runtime if runtime > 0 else 0
                    }
                    self.unified_logger.log_performance_metrics(self.platform_name, performance_metrics)
                
                return enhanced_data
            else:
                self.logger.warning("No se obtuvieron datos")
                return []
                
        except Exception as e:
            self.logger.error(f"Error ejecutando scraper: {e}")
            self.stats['last_error'] = str(e)
            return []
    
    def run_forever(self, interval: Optional[int] = None):
        """
        Ejecuta el scraper en bucle infinito
        
        Args:
            interval: Segundos entre ejecuciones (None = usar config)
        """
        if interval is None:
            interval = self.config.get('interval', 60)
        
        self.logger.info(
            f"Iniciando bucle infinito para {self.platform_name} "
            f"(intervalo: {interval}s, proxy: {'Sí' if self.use_proxy else 'No'})"
        )
        
        while True:
            try:
                self.run_once()
                
                self.logger.info(f"Esperando {interval} segundos...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self.logger.info("Detenido por el usuario")
                break
                
            except Exception as e:
                self.logger.error(f"Error en bucle: {e}")
                self.logger.info(f"Esperando {interval} segundos antes de reintentar...")
                time.sleep(interval)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas de ejecución del scraper"""
        stats = self.stats.copy()
        stats['platform'] = self.platform_name
        stats['proxy_enabled'] = self.use_proxy
        stats['proxy_count'] = len(self.proxy_list) if self.proxy_list else 0
        stats['cache_enabled'] = self.cache_service is not None
        stats['active_proxy_failures'] = len(self.proxy_failures)
        
        # Formatear tiempos para legibilidad
        if stats['last_run']:
            stats['last_run_formatted'] = stats['last_run'].strftime('%Y-%m-%d %H:%M:%S')
        
        return stats
    
    def __enter__(self):
        """Context manager para limpieza automática"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra la sesión al salir"""
        try:
            # Cerrar ProxyManager si está activo
            if self.proxy_manager:
                self.proxy_manager.close()
                self.logger.info("ProxyManager cerrado")
            
            self.session.close()
            self.logger.info(f"Scraper {self.platform_name} cerrado correctamente")
        except Exception as e:
            self.logger.error(f"Error cerrando scraper: {e}")