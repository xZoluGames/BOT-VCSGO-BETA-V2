"""
Async Steam Market Scraper - BOT-VCSGO-BETA-V2

Versión asíncrona del scraper de Steam Market con mejoras de rendimiento:
- Procesamiento asíncrono masivo con aiohttp
- Control de rate limiting inteligente
- Conexiones persistentes optimizadas
- Manejo robusto de errores y reintentos
- Estadísticas de precios automáticas
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import orjson
import sys
from pathlib import Path
from urllib.parse import unquote
import aiohttp
import time

# Agregar directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from core.async_base_scraper import AsyncBaseScraper
from core.exceptions import APIError, ParseError, ValidationError


class AsyncSteamMarketScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para Steam Market
    
    Características:
    - API REST de Steam Community Market
    - Procesamiento asíncrono de item nameids
    - Rate limiting conservador para evitar bloqueos
    - Manejo de errores robusto con reintentos
    - Estadísticas de precios automáticas
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        """
        Inicializa el scraper de Steam Market
        
        Args:
            use_proxy: Si usar proxy (None = usar configuración)
        """
        # Configuración específica de Steam Market
        custom_config = {
            'rate_limit': 50,  # Steam es muy estricto con rate limiting
            'burst_size': 5,   # Conservador para evitar bloqueos
            'cache_ttl': 600,  # 10 minutos - precios cambian frecuentemente
            'timeout_seconds': 15,
            'max_retries': 3,
            'max_concurrent': 100  # Límite conservador para Steam
        }
        
        super().__init__(
            platform_name='steam_market',
            use_proxy=use_proxy,
            custom_config=custom_config
        )
        
        # URL de la API de Steam Market
        self.api_url_template = "https://steamcommunity.com/market/itemordershistogram?country=PK&language=english&currency=1&item_nameid={item_nameid}&two_factor=0&norender=1"
        
        # Headers específicos para Steam Market
        self.steam_headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Connection': 'keep-alive'
        }
        
        self.logger.info("AsyncSteamMarketScraper inicializado")
    
    def _find_nameids_file(self) -> Optional[Path]:
        """
        Busca el archivo de nameids en ubicaciones conocidas
        
        Returns:
            Path al archivo o None si no se encuentra
        """
        possible_paths = [
            self.path_manager.data_dir / "item_nameids.json",
            self.path_manager.data_dir.parent / "JSON" / "item_nameids.json",
            self.path_manager.data_dir.parent / "data" / "item_nameids.json"
        ]
        
        for path in possible_paths:
            if path.exists():
                self.logger.info(f"Archivo nameids encontrado: {path}")
                return path
        
        self.logger.warning("Archivo item_nameids.json no encontrado")
        return None
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Ejecuta el scraping de Steam Market
        
        Returns:
            Lista de items con sus precios
        """
        try:
            # Buscar archivo de nameids
            item_nameids_file = self._find_nameids_file()
            
            if not item_nameids_file or not item_nameids_file.exists():
                self.logger.error("item_nameids.json no encontrado")
                raise APIError(self.platform_name, response_text="item_nameids.json no encontrado")
            
            self.logger.info("Iniciando scraping de Steam Market")
            
            # Cargar nameids de items
            nameids = await self._load_item_nameids(item_nameids_file)
            
            if not nameids:
                self.logger.warning("No se cargaron nameids")
                return []
            
            self.logger.info(f"Cargados {len(nameids)} nameids para procesar")
            
            # Procesar items en lotes para evitar sobrecarga
            formatted_items = await self._process_items_async(nameids)
            
            # Generar estadísticas de precios
            if formatted_items:
                self._log_price_statistics(formatted_items)
            
            self.logger.info(
                f"Steam Market scraping completado - "
                f"Items procesados: {len(nameids)}, "
                f"Items válidos: {len(formatted_items)}"
            )
            
            return formatted_items
            
        except Exception as e:
            self.logger.error(f"Error en scraping: {e}")
            raise
    
    async def _load_item_nameids(self, nameids_file: Path) -> List[Dict]:
        """
        Carga el archivo de nameids de items
        
        Args:
            nameids_file: Path al archivo de nameids
        
        Returns:
            Lista de items con nameids
        """
        try:
            with open(nameids_file, 'rb') as f:
                data = orjson.loads(f.read())
            
            if not isinstance(data, list):
                self.logger.error(f"Formato de nameids inválido: esperaba list, obtuvo {type(data)}")
                return []
            
            # Filtrar items válidos
            valid_items = []
            for item in data:
                if isinstance(item, dict) and 'id' in item and 'name' in item:
                    valid_items.append(item)
            
            self.logger.info(f"Nameids cargados: {len(data)} total, {len(valid_items)} válidos")
            return valid_items
            
        except Exception as e:
            self.logger.error(f"Error cargando nameids: {e}")
            return []
    
    async def _process_items_async(self, nameids: List[Dict]) -> List[Dict]:
        """
        Procesa items de forma asíncrona con control de concurrencia
        
        Args:
            nameids: Lista de items con nameids
            
        Returns:
            Lista de items formateados
        """
        formatted_items = []
        
        if not self.session:
            await self.setup()
        
        # Crear semáforo para controlar concurrencia
        semaphore = asyncio.Semaphore(self.scraper_config.get('max_concurrent', 100))
        
        # Crear tareas asíncronas
        tasks = []
        for item in nameids:
            task = self._fetch_item_with_semaphore(semaphore, item)
            tasks.append(task)
        
        # Ejecutar tareas en lotes para evitar sobrecarga
        batch_size = 50
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            
            self.logger.info(f"Procesando lote {i//batch_size + 1}/{(len(tasks) + batch_size - 1)//batch_size}")
            
            # Procesar lote
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            # Recopilar resultados válidos
            for result in batch_results:
                if isinstance(result, dict):
                    formatted_items.append(result)
                elif isinstance(result, Exception):
                    self.logger.debug(f"Error en item: {result}")
            
            # Pequeña pausa entre lotes
            if i + batch_size < len(tasks):
                await asyncio.sleep(0.5)
        
        return formatted_items
    
    async def _fetch_item_with_semaphore(self, semaphore: asyncio.Semaphore, item: Dict) -> Optional[Dict]:
        """
        Fetch item con control de semáforo
        
        Args:
            semaphore: Semáforo para controlar concurrencia
            item: Item con nameid
            
        Returns:
            Item formateado o None
        """
        async with semaphore:
            return await self._fetch_item_price(item)
    
    async def _fetch_item_price(self, item: Dict) -> Optional[Dict]:
        """
        Obtiene el precio de un item específico
        
        Args:
            item: Item con nameid e información
            
        Returns:
            Item formateado con precio o None
        """
        item_nameid = item.get('id')
        name = unquote(item.get('name', ''))
        
        if not item_nameid or not name:
            return None
        
        url = self.api_url_template.format(item_nameid=item_nameid)
        
        try:
            # Rate limiting
            await self.rate_limiter.wait()
            
            self.logger.debug(f"Fetching {name} from {url}")
            
            # Update metrics
            self.metrics.requests_made += 1
            
            async with self.session.get(
                url,
                headers=self.steam_headers
            ) as response:
                if response.status == 429:
                    self.logger.warning("Rate limit hit, esperando...")
                    await asyncio.sleep(2)
                    return None
                elif response.status != 200:
                    self.logger.debug(f"HTTP {response.status} para {name}")
                    return None
                
                # Leer y parsear respuesta
                content = await response.read()
                if not content:
                    return None
                
                data = orjson.loads(content)
                
                # Extraer precio
                price = 0.0
                if 'highest_buy_order' in data and data['highest_buy_order']:
                    price = float(data['highest_buy_order']) / 100.0
                
                # Update metrics
                self.metrics.requests_successful += 1
                
                # Crear item formateado
                formatted_item = {
                    'name': name.strip(),
                    'price': round(price, 2),
                    'platform': 'steam_market',
                    'steam_market_url': f"https://steamcommunity.com/market/listings/730/{name.replace(' ', '%20')}",
                    'last_update': datetime.now().isoformat()
                }
                
                return formatted_item
                
        except asyncio.TimeoutError:
            self.metrics.requests_failed += 1
            self.logger.debug(f"Timeout para {name}")
            return None
        except Exception as e:
            self.metrics.requests_failed += 1
            self.logger.debug(f"Error fetching {name}: {e}")
            return None
    
    def _log_price_statistics(self, items: List[Dict]) -> None:
        """
        Genera y registra estadísticas de precios
        
        Args:
            items: Lista de items formateados
        """
        try:
            if not items:
                return
            
            prices = [item['price'] for item in items if item['price'] > 0]
            if not prices:
                self.logger.info("Steam Market estadísticas - No hay precios válidos")
                return
            
            total_items = len(items)
            valid_prices = len(prices)
            avg_price = sum(prices) / valid_prices
            min_price = min(prices)
            max_price = max(prices)
            
            self.logger.info(
                f"Steam Market estadísticas - "
                f"Items totales: {total_items}, "
                f"Con precio: {valid_prices} ({valid_prices/total_items*100:.1f}%), "
                f"Precio promedio: ${avg_price:.2f}, "
                f"Rango: ${min_price:.2f}-${max_price:.2f}"
            )
            
        except Exception as e:
            self.logger.warning(f"Error calculando estadísticas de precios: {e}")
    
    async def validate_item(self, item: Dict[str, Any]) -> bool:
        """
        Validación específica para items de Steam Market
        
        Args:
            item: Item a validar
            
        Returns:
            True si es válido
        """
        # Validación base
        if not await super().validate_item(item):
            return False
        
        try:
            # Validaciones específicas de Steam Market
            price = float(item['price'])
            if price < 0 or price > 100000:  # Steam puede tener items muy caros
                return False
            
            # Verificar que el nombre sea razonable
            name = item['name']
            if len(name.strip()) < 3 or len(name) > 300:
                return False
            
            return True
            
        except (ValueError, TypeError, KeyError):
            return False
    
    async def get_item_price(self, item_name: str) -> Optional[float]:
        """
        Obtiene el precio de un item específico por nombre
        
        Args:
            item_name: Nombre del item
            
        Returns:
            Precio del item o None si no se encuentra
        """
        try:
            items = await self.run()
            
            for item in items:
                if item['name'] == item_name:
                    return item['price']
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error obteniendo precio para {item_name}: {e}")
            return None


async def compare_performance():
    """
    Función para comparar rendimiento con versión síncrona
    """
    import time
    
    print("\n=== Comparación de Rendimiento: Steam Market ===\n")
    
    # Test asíncrono
    print("🚀 Ejecutando versión ASÍNCRONA...")
    start_async = time.time()
    
    async with AsyncSteamMarketScraper(use_proxy=False) as scraper:
        items_async = await scraper.run()
    
    time_async = time.time() - start_async
    
    print(f"✅ Asíncrono completado:")
    print(f"   - Items: {len(items_async)}")
    print(f"   - Tiempo: {time_async:.2f}s")
    print(f"   - Métricas: {scraper.metrics.to_dict()}")
    
    # Comparar con versión síncrona (si existe)
    try:
        from scrapers.steam_market_scraper import SteamMarketScraper
        
        print("\n🐌 Ejecutando versión SÍNCRONA...")
        start_sync = time.time()
        
        sync_scraper = SteamMarketScraper(use_proxy=False)
        items_sync = sync_scraper.fetch_data()
        
        time_sync = time.time() - start_sync
        
        print(f"✅ Síncrono completado:")
        print(f"   - Items: {len(items_sync)}")
        print(f"   - Tiempo: {time_sync:.2f}s")
        
        # Calcular mejora
        if time_sync > 0:
            improvement = ((time_sync - time_async) / time_sync) * 100
            speedup = time_sync / time_async if time_async > 0 else 0
            
            print(f"\n📊 RESULTADOS:")
            print(f"   - Mejora: {improvement:.1f}%")
            print(f"   - Speedup: {speedup:.1f}x más rápido")
            print(f"   - Tiempo ahorrado: {time_sync - time_async:.2f}s")
        
    except ImportError:
        print("\n⚠️  No se pudo importar la versión síncrona para comparar")
    except Exception as e:
        print(f"\n❌ Error en comparación: {e}")


async def main():
    """Función principal para testing"""
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Ejecutar scraper
    async with AsyncSteamMarketScraper(use_proxy=False) as scraper:
        items = await scraper.run()
        print(f"\n✅ Scraping completado: {len(items)} items")
        
        # Mostrar algunos items de ejemplo
        if items:
            print("\n📦 Primeros 5 items:")
            for item in items[:5]:
                print(f"  - {item['name']}: ${item['price']:.2f}")
            
            # Mostrar estadísticas de precios
            prices = [item['price'] for item in items if item['price'] > 0]
            if prices:
                print(f"\n📊 Estadísticas de precios:")
                print(f"  - Precio mínimo: ${min(prices):.2f}")
                print(f"  - Precio máximo: ${max(prices):.2f}")
                print(f"  - Precio promedio: ${sum(prices)/len(prices):.2f}")
    
    # Ejecutar comparación de rendimiento
    await compare_performance()


if __name__ == "__main__":
    asyncio.run(main())