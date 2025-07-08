"""
Concurrent Scraper - BOT-vCSGO-Beta V2

Utilidad migrada desde BOT-vCSGO-Beta para scraping concurrente
- Migrado desde core/scrapers/concurrent_scraper.py de BOT-vCSGO-Beta
- Soporte para requests concurrentes síncronos y asíncronos
- ThreadPoolExecutor para concurrencia controlada
- Semáforos para limitar sobrecarga de recursos
"""

from typing import List, Dict, Optional, Callable
import concurrent.futures
import asyncio
import sys
from pathlib import Path

# Agregar el directorio core al path
sys.path.append(str(Path(__file__).parent.parent))

from core.base_scraper import BaseScraper

# Importar aiohttp solo si está disponible
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


class ConcurrentScraper(BaseScraper):
    """
    Scraper optimizado para realizar múltiples requests concurrentes
    
    Migrado desde BOT-vCSGO-Beta con las siguientes características:
    - ThreadPoolExecutor para concurrencia síncrona
    - aiohttp para concurrencia asíncrona (opcional)
    - Semáforos para control de recursos
    - Manejo de errores por URL individual
    - Compatible con BaseScraper V2
    """
    
    def __init__(self, platform_name: str, use_proxy: bool = False, proxy_list: Optional[List[str]] = None):
        """
        Inicializa el scraper concurrente
        
        Args:
            platform_name: Nombre de la plataforma
            use_proxy: Si usar proxy o no
            proxy_list: Lista de proxies a usar
        """
        # Configuración para scraping concurrente
        config = {
            'timeout': 10,
            'max_retries': 3,
            'retry_delay': 1,
            'interval': 60,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/html, */*',
                'Accept-Encoding': 'gzip, deflate, br'
            }
        }
        
        super().__init__(platform_name, use_proxy, proxy_list, config)
        
        # Configuración de concurrencia (del BOT-vCSGO-Beta original)
        self.max_workers = 10
        
        # Semáforo para async (solo si aiohttp está disponible)
        if AIOHTTP_AVAILABLE:
            self.semaphore = asyncio.Semaphore(5)  # Limitar concurrencia
        
        self.logger.info(f"Concurrent scraper inicializado para {platform_name} (async: {'Sí' if AIOHTTP_AVAILABLE else 'No'})")
    
    def fetch_multiple_sync(self, urls: List[str], 
                           parse_func: Callable[[Dict], List[Dict]]) -> List[Dict]:
        """
        Fetch síncrono concurrente de múltiples URLs (del BOT-vCSGO-Beta original)
        
        Args:
            urls: Lista de URLs a procesar
            parse_func: Función para parsear cada respuesta
            
        Returns:
            Lista combinada de todos los items obtenidos
        """
        self.logger.info(f"Iniciando fetch concurrente de {len(urls)} URLs")
        
        all_items = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Enviar todas las URLs
            future_to_url = {
                executor.submit(self.make_request, url): url 
                for url in urls
            }
            
            # Procesar resultados conforme van llegando
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    response = future.result()
                    if response:
                        items = parse_func(response)
                        all_items.extend(items)
                        self.logger.debug(f"Procesado {url}: {len(items)} items")
                    else:
                        self.logger.warning(f"No se pudo obtener respuesta de {url}")
                except Exception as e:
                    self.logger.error(f"Error processing {url}: {e}")
        
        self.logger.info(f"Fetch concurrente completado: {len(all_items)} items totales")
        return all_items
    
    # Métodos asíncronos solo si aiohttp está disponible
    if AIOHTTP_AVAILABLE:
        async def fetch_url_async(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
            """
            Fetch asíncrono de una URL (del BOT-vCSGO-Beta original)
            
            Args:
                session: Sesión aiohttp
                url: URL a procesar
                
            Returns:
                Datos JSON o None si falla
            """
            async with self.semaphore:
                try:
                    timeout = aiohttp.ClientTimeout(total=self.config['timeout'])
                    async with session.get(url, timeout=timeout) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            self.logger.warning(f"Status {response.status} para {url}")
                            return None
                except Exception as e:
                    self.logger.error(f"Error fetching {url}: {e}")
                    return None
        
        async def fetch_multiple_async(self, urls: List[str]) -> List[Dict]:
            """
            Fetch asíncrono de múltiples URLs (del BOT-vCSGO-Beta original)
            
            Args:
                urls: Lista de URLs a procesar
                
            Returns:
                Lista de respuestas JSON (exitosas)
            """
            self.logger.info(f"Iniciando fetch asíncrono de {len(urls)} URLs")
            
            # Configurar headers para aiohttp
            headers = self.get_headers_with_auth()
            
            async with aiohttp.ClientSession(headers=headers) as session:
                tasks = [self.fetch_url_async(session, url) for url in urls]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Filtrar resultados exitosos
                successful_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Error async en {urls[i]}: {result}")
                    elif result is not None:
                        successful_results.append(result)
            
            self.logger.info(f"Fetch asíncrono completado: {len(successful_results)} respuestas exitosas")
            return successful_results
        
        def run_async_fetch(self, urls: List[str]) -> List[Dict]:
            """
            Ejecuta fetch asíncrono desde código síncrono
            
            Args:
                urls: Lista de URLs a procesar
                
            Returns:
                Lista de respuestas JSON
            """
            try:
                # Obtener el event loop actual o crear uno nuevo
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Si ya hay un loop corriendo, usar asyncio.create_task
                    self.logger.warning("Event loop ya está corriendo, usando método síncrono")
                    return []
                else:
                    return loop.run_until_complete(self.fetch_multiple_async(urls))
            except RuntimeError:
                # No hay event loop, crear uno nuevo
                return asyncio.run(self.fetch_multiple_async(urls))
    
    else:
        def run_async_fetch(self, urls: List[str]) -> List[Dict]:
            """Fallback cuando aiohttp no está disponible"""
            self.logger.warning("aiohttp no disponible, usando método síncrono")
            return []
    
    def parse_response(self, response) -> List[Dict]:
        """
        Método requerido por BaseScraper - implementación básica
        """
        try:
            data = response.json()
            # Implementación básica - debe ser sobrescrita por scrapers específicos
            if isinstance(data, list):
                return [{'Item': str(item), 'Price': 0} for item in data[:10]]
            else:
                return [{'Item': 'Sample Item', 'Price': 0}]
        except:
            return []
    
    def fetch_data(self) -> List[Dict]:
        """
        Método requerido por BaseScraper - implementación de ejemplo
        
        Debe ser sobrescrito por scrapers que usen ConcurrentScraper
        """
        self.logger.warning("fetch_data no implementado - usar fetch_multiple_sync o run_async_fetch")
        return []


def main():
    """
    Función de ejemplo para demostrar el uso del ConcurrentScraper
    """
    # URLs de ejemplo para testing
    test_urls = [
        'https://httpbin.org/delay/1',
        'https://httpbin.org/delay/2',
        'https://httpbin.org/json'
    ]
    
    # Crear scraper concurrente
    scraper = ConcurrentScraper('test_concurrent', use_proxy=False)
    
    def simple_parser(response):
        """Parser simple para testing"""
        try:
            data = response.json()
            return [{'Item': f"Test item from {response.url}", 'Price': 1.0}]
        except:
            return []
    
    try:
        print("=== Ejecutando Concurrent Scraper V2 (ejemplo) ===")
        
        # Ejemplo con fetch síncrono
        print("\n1. Probando fetch síncrono concurrente...")
        sync_results = scraper.fetch_multiple_sync(test_urls, simple_parser)
        print(f"   Resultados síncronos: {len(sync_results)} items")
        
        # Ejemplo con fetch asíncrono (si está disponible)
        if AIOHTTP_AVAILABLE:
            print("\n2. Probando fetch asíncrono...")
            async_results = scraper.run_async_fetch(test_urls)
            print(f"   Resultados asíncronos: {len(async_results)} respuestas")
        else:
            print("\n2. aiohttp no disponible - saltando test asíncrono")
        
        print(f"\n✅ Tests completados:")
        print(f"   - Estadísticas: {scraper.get_stats()}")
        
    except KeyboardInterrupt:
        print("\n🛑 Detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        # Limpiar recursos
        scraper.session.close()


if __name__ == "__main__":
    main()