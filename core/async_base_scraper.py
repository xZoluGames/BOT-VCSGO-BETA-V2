"""
Async Base Scraper - BOT-VCSGO-BETA-V2

Versión asíncrona del base scraper con mejoras de rendimiento:
- Soporte async/await nativo
- Connection pooling automático
- Rate limiting inteligente
- Métricas de rendimiento
"""

import asyncio
import aiohttp
import orjson
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import hashlib

from .config_manager import get_config_manager
from .path_manager import get_path_manager
from .exceptions import (
    APIError, RateLimitError, ParseError, ValidationError,
    ProxyConnectionError, ErrorHandler
)
from .async_cache_service import AsyncCacheService


@dataclass
class ScraperMetrics:
    """Métricas de rendimiento del scraper"""
    requests_made: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    total_items_scraped: int = 0
    total_time: float = 0.0
    api_response_times: List[float] = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0
    rate_limit_hits: int = 0
    proxy_rotations: int = 0
    
    def add_response_time(self, time: float):
        """Agrega tiempo de respuesta a las métricas"""
        self.api_response_times.append(time)
        # Mantener solo los últimos 100 tiempos
        if len(self.api_response_times) > 100:
            self.api_response_times.pop(0)
    
    def get_average_response_time(self) -> float:
        """Calcula el tiempo de respuesta promedio"""
        if not self.api_response_times:
            return 0.0
        return sum(self.api_response_times) / len(self.api_response_times)
    
    def get_success_rate(self) -> float:
        """Calcula la tasa de éxito"""
        if self.requests_made == 0:
            return 0.0
        return (self.requests_successful / self.requests_made) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte las métricas a diccionario"""
        return {
            'requests_made': self.requests_made,
            'requests_successful': self.requests_successful,
            'requests_failed': self.requests_failed,
            'success_rate': f"{self.get_success_rate():.2f}%",
            'total_items': self.total_items_scraped,
            'total_time': f"{self.total_time:.2f}s",
            'avg_response_time': f"{self.get_average_response_time():.3f}s",
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': f"{(self.cache_hits / (self.cache_hits + self.cache_misses) * 100) if (self.cache_hits + self.cache_misses) > 0 else 0:.2f}%",
            'rate_limit_hits': self.rate_limit_hits,
            'proxy_rotations': self.proxy_rotations
        }


class AsyncBaseScraper(ABC):
    """
    Clase base asíncrona para todos los scrapers
    
    Proporciona funcionalidad común con soporte async/await:
    - Connection pooling con aiohttp
    - Rate limiting adaptativo
    - Retry logic mejorado
    - Cache asíncrono
    - Métricas de rendimiento
    """
    
    def __init__(self, 
                 platform_name: str,
                 use_proxy: Optional[bool] = None,
                 proxy_manager: Optional[Any] = None,
                 custom_config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el scraper asíncrono
        
        Args:
            platform_name: Nombre de la plataforma
            use_proxy: Si usar proxy (None = usar config)
            proxy_manager: Gestor de proxies opcional
            custom_config: Configuración personalizada
        """
        self.platform_name = platform_name.lower()
        self.logger = logging.getLogger(f"AsyncScraper.{platform_name}")
        
        # Gestores de configuración
        self.config_manager = get_config_manager()
        self.path_manager = get_path_manager()
        
        # Configuración del scraper
        self.scraper_config = self.config_manager.get_scraper_config(platform_name)
        if custom_config:
            self.scraper_config.update(custom_config)
        
        # Configuración de proxy
        self.use_proxy = use_proxy if use_proxy is not None else self.scraper_config.get('use_proxy', False)
        self.proxy_manager = proxy_manager
        
        # Cache asíncrono
        self.cache = AsyncCacheService(
            cache_dir=self.path_manager.cache_dir,
            platform=platform_name
        )
        
        # API key
        self.api_key = self.config_manager.get_api_key(platform_name)
        
        # Session de aiohttp (se inicializa en setup)
        self.session: Optional[aiohttp.ClientSession] = None
        self.connector: Optional[aiohttp.TCPConnector] = None
        
        # Rate limiting
        self.rate_limiter = AsyncRateLimiter(
            requests_per_minute=self.scraper_config.get('rate_limit', 60),
            burst_size=self.scraper_config.get('burst_size', 10)
        )
        
        # Métricas
        self.metrics = ScraperMetrics()
        
        # Estado
        self.is_initialized = False
        
        self.logger.info(f"AsyncScraper inicializado para {platform_name}")
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.setup()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.cleanup()
    
    async def setup(self):
        """Inicializa recursos asíncronos"""
        if self.is_initialized:
            return
        
        # Crear connector con connection pooling
        self.connector = aiohttp.TCPConnector(
            limit=100,  # Conexiones totales
            limit_per_host=30,  # Conexiones por host
            ttl_dns_cache=300,  # Cache DNS 5 minutos
            enable_cleanup_closed=True
        )
        
        # Headers por defecto
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
        }
        
        # Agregar headers específicos del scraper
        if 'headers' in self.scraper_config:
            headers.update(self.scraper_config['headers'])
        
        # Timeout
        timeout = aiohttp.ClientTimeout(
            total=self.scraper_config.get('timeout_seconds', 30),
            connect=10,
            sock_read=20
        )
        
        # Crear session
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            headers=headers,
            timeout=timeout,
            json_serialize=lambda x: orjson.dumps(x).decode(),
            raise_for_status=False  # Manejaremos los errores manualmente
        )
        
        # Inicializar cache
        await self.cache.setup()
        
        self.is_initialized = True
        self.logger.info("Recursos asíncronos inicializados")
    
    async def cleanup(self):
        """Limpia recursos asíncronos"""
        if self.session:
            await self.session.close()
        
        if self.connector:
            await self.connector.close()
        
        await self.cache.cleanup()
        
        self.is_initialized = False
        self.logger.info("Recursos asíncronos liberados")
    
    async def fetch(self, 
                   url: str, 
                   method: str = 'GET',
                   **kwargs) -> aiohttp.ClientResponse:
        """
        Realiza una petición HTTP asíncrona con reintentos y rate limiting
        
        Args:
            url: URL a consultar
            method: Método HTTP
            **kwargs: Argumentos adicionales para la petición
            
        Returns:
            Response de aiohttp
        """
        if not self.is_initialized:
            await self.setup()
        
        # Rate limiting
        await self.rate_limiter.acquire()
        
        # Configurar proxy si está habilitado
        if self.use_proxy and self.proxy_manager:
            proxy = await self._get_proxy()
            if proxy:
                kwargs['proxy'] = proxy
        
        # Reintentos
        max_retries = self.scraper_config.get('max_retries', 3)
        retry_delay = self.scraper_config.get('retry_delay', 1)
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # Métricas
                start_time = time.time()
                self.metrics.requests_made += 1
                
                # Realizar petición
                async with self.session.request(method, url, **kwargs) as response:
                    # Métricas de tiempo
                    response_time = time.time() - start_time
                    self.metrics.add_response_time(response_time)
                    
                    # Verificar rate limit
                    if response.status == 429:
                        self.metrics.rate_limit_hits += 1
                        retry_after = int(response.headers.get('Retry-After', 60))
                        raise RateLimitError(self.platform_name, retry_after)
                    
                    # Verificar otros errores HTTP
                    if response.status >= 400:
                        text = await response.text()
                        raise APIError(
                            self.platform_name,
                            status_code=response.status,
                            response_text=text,
                            url=str(response.url)
                        )
                    
                    # Éxito
                    self.metrics.requests_successful += 1
                    return response
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                self.metrics.requests_failed += 1
                
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** attempt)  # Backoff exponencial
                    self.logger.warning(
                        f"Error en petición a {url}, reintentando en {wait_time}s... "
                        f"(intento {attempt + 1}/{max_retries + 1})"
                    )
                    await asyncio.sleep(wait_time)
                    
                    # Rotar proxy si está habilitado
                    if self.use_proxy and self.proxy_manager:
                        await self._rotate_proxy()
                else:
                    # Convertir a excepción personalizada
                    if isinstance(e, asyncio.TimeoutError):
                        raise APIError(
                            self.platform_name,
                            response_text="Request timeout",
                            url=url
                        )
                    else:
                        raise APIError(
                            self.platform_name,
                            response_text=str(e),
                            url=url
                        )
        
        # Si llegamos aquí, todos los reintentos fallaron
        raise APIError(
            self.platform_name,
            response_text=f"Max retries exceeded: {str(last_error)}",
            url=url
        )
    
    async def fetch_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch y parsea respuesta JSON con cache
        
        Args:
            url: URL a consultar
            **kwargs: Argumentos adicionales
            
        Returns:
            Datos parseados como diccionario
        """
        # Generar cache key
        cache_key = self._generate_cache_key(url, kwargs)
        
        # Intentar obtener del cache
        cached_data = await self.cache.get(cache_key)
        if cached_data is not None:
            self.metrics.cache_hits += 1
            self.logger.debug(f"Cache hit para {url}")
            return cached_data
        
        self.metrics.cache_misses += 1
        
        # Fetch desde API
        response = await self.fetch(url, **kwargs)
        
        try:
            # Parsear JSON con orjson (más rápido)
            text = await response.text()
            data = orjson.loads(text)
            
            # Guardar en cache
            ttl = self.scraper_config.get('cache_ttl', 300)
            await self.cache.set(cache_key, data, ttl=ttl)
            
            return data
            
        except orjson.JSONDecodeError as e:
            raise ParseError(
                self.platform_name,
                data_type="JSON",
                reason=str(e)
            )
    
    async def _get_proxy(self) -> Optional[str]:
        """Obtiene un proxy del manager"""
        if not self.proxy_manager:
            return None
        
        try:
            # Soporte para proxy managers síncronos y asíncronos
            if hasattr(self.proxy_manager, 'get_proxy_async'):
                return await self.proxy_manager.get_proxy_async()
            else:
                # Ejecutar en thread pool si es síncrono
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self.proxy_manager.get_proxy)
        except Exception as e:
            self.logger.error(f"Error obteniendo proxy: {e}")
            return None
    
    async def _rotate_proxy(self):
        """Rota el proxy actual"""
        if self.proxy_manager and hasattr(self.proxy_manager, 'report_failure'):
            self.metrics.proxy_rotations += 1
            try:
                if hasattr(self.proxy_manager, 'report_failure_async'):
                    await self.proxy_manager.report_failure_async()
                else:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.proxy_manager.report_failure)
            except Exception as e:
                self.logger.error(f"Error rotando proxy: {e}")
    
    def _generate_cache_key(self, url: str, params: Dict[str, Any]) -> str:
        """Genera una clave única para cache"""
        # Crear string único con URL y parámetros
        key_data = f"{url}:{orjson.dumps(params, option=orjson.OPT_SORT_KEYS).decode()}"
        # Hash para clave compacta
        return f"{self.platform_name}:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    @abstractmethod
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Método abstracto que debe implementar cada scraper
        
        Returns:
            Lista de items scrapeados
        """
        pass
    
    async def validate_item(self, item: Dict[str, Any]) -> bool:
        """
        Valida un item scrapeado
        
        Args:
            item: Item a validar
            
        Returns:
            True si es válido, False si no
        """
        required_fields = ['name', 'price']
        
        for field in required_fields:
            if field not in item or item[field] is None:
                self.logger.warning(f"Campo requerido '{field}' faltante en item")
                return False
        
        # Validar precio
        try:
            price = float(item['price'])
            if price <= 0:
                self.logger.warning(f"Precio inválido: {price}")
                return False
        except (ValueError, TypeError):
            self.logger.warning(f"Precio no numérico: {item['price']}")
            return False
        
        return True
    
    async def save_results(self, items: List[Dict[str, Any]]):
        """
        Guarda los resultados del scraping
        
        Args:
            items: Lista de items a guardar
        """
        # Validar items
        valid_items = []
        for item in items:
            if await self.validate_item(item):
                valid_items.append(item)
        
        if not valid_items:
            self.logger.warning("No hay items válidos para guardar")
            return
        
        # Preparar datos
        data = {
            'platform': self.platform_name,
            'timestamp': datetime.now().isoformat(),
            'total_items': len(valid_items),
            'items': valid_items,
            'metrics': self.metrics.to_dict()
        }
        
        # Guardar en archivo
        output_file = self.path_manager.get_data_file(f"{self.platform_name}_data.json")
        
        try:
            async with aiofiles.open(output_file, 'wb') as f:
                await f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
            
            self.logger.info(f"Guardados {len(valid_items)} items en {output_file}")
            
        except Exception as e:
            self.logger.error(f"Error guardando resultados: {e}")
            raise
    
    async def run(self) -> List[Dict[str, Any]]:
        """
        Ejecuta el scraper completo con métricas
        
        Returns:
            Lista de items scrapeados
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Iniciando scraping de {self.platform_name}")
            
            # Ejecutar scraping
            items = await self.scrape()
            
            # Actualizar métricas
            self.metrics.total_items_scraped = len(items)
            self.metrics.total_time = time.time() - start_time
            
            # Guardar resultados
            await self.save_results(items)
            
            # Log de métricas
            self.logger.info(f"Scraping completado: {self.metrics.to_dict()}")
            
            return items
            
        except Exception as e:
            self.metrics.total_time = time.time() - start_time
            self.logger.error(f"Error en scraping: {e}")
            ErrorHandler.log_exception(e, self.logger)
            raise
        finally:
            # Siempre limpiar recursos
            await self.cleanup()


class AsyncRateLimiter:
    """Rate limiter asíncrono con token bucket algorithm"""
    
    def __init__(self, requests_per_minute: int = 60, burst_size: int = 10):
        self.rate = requests_per_minute / 60.0  # Requests por segundo
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Adquiere un token, esperando si es necesario"""
        async with self._lock:
            # Actualizar tokens basado en tiempo transcurrido
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.burst_size, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            # Esperar si no hay tokens
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 1
            
            # Consumir token
            self.tokens -= 1


# Importar aiofiles si está disponible, si no usar alternativa
try:
    import aiofiles
except ImportError:
    # Fallback simple si aiofiles no está instalado
    class aiofiles:
        @staticmethod
        @asynccontextmanager
        async def open(filename, mode='r', **kwargs):
            import io
            
            # Ejecutar I/O en thread pool
            loop = asyncio.get_event_loop()
            
            if 'b' in mode:
                # Modo binario
                if 'w' in mode:
                    async def write(data):
                        await loop.run_in_executor(None, lambda: open(filename, mode).write(data))
                    
                    yield type('AsyncFile', (), {'write': write})()
                else:
                    data = await loop.run_in_executor(None, lambda: open(filename, mode).read())
                    yield io.BytesIO(data)
            else:
                # Modo texto
                if 'w' in mode:
                    async def write(data):
                        await loop.run_in_executor(None, lambda: open(filename, mode).write(data))
                    
                    yield type('AsyncFile', (), {'write': write})()
                else:
                    data = await loop.run_in_executor(None, lambda: open(filename, mode).read())
                    yield io.StringIO(data)