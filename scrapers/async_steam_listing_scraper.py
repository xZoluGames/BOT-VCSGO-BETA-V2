"""
Async Steam Listing Scraper - BOT-VCSGO-BETA-V2

Versión asíncrona del scraper de Steam Community Market Listings con mejoras de rendimiento:
- Procesamiento asíncrono de búsquedas paginadas
- Control de rate limiting inteligente para Steam
- Conexiones persistentes optimizadas
- Manejo robusto de errores y reintentos
- Estadísticas de precios automáticas
- Procesamiento incremental de batches
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import orjson
import sys
from pathlib import Path
import aiohttp
import time

# Agregar directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from core.async_base_scraper import AsyncBaseScraper
from core.exceptions import APIError, ParseError, ValidationError


class AsyncSteamListingScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para Steam Community Market Listings
    
    Características:
    - API REST de Steam Community Market Search
    - Procesamiento asíncrono de páginas paginadas
    - Rate limiting conservador para evitar bloqueos de Steam
    - Manejo de errores robusto con reintentos
    - Estadísticas de precios automáticas
    - Extracción de iconos y precios de venta
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        """
        Inicializa el scraper de Steam Listing
        
        Args:
            use_proxy: Si usar proxy (None = usar configuración)
        """
        # Configuración específica de Steam Listing
        custom_config = {
            'rate_limit': 10,  # Extremadamente conservador para Steam
            'burst_size': 1,   # Solo 1 request por burst
            'cache_ttl': 300,  # 5 minutos - listings cambian frecuentemente
            'timeout_seconds': 20,
            'max_retries': 3,
            'max_concurrent': 5  # Muy limitado para Steam Listings
        }
        
        super().__init__(
            platform_name='steam_listing',
            use_proxy=use_proxy,
            custom_config=custom_config
        )
        
        # URL base de la API de Steam Market Search
        self.base_url = "https://steamcommunity.com/market/search/render/?query=&start={}&count={}&search_descriptions=0&sort_column=name&sort_dir=asc&appid=730&norender=1"
        
        # Headers específicos para Steam Listing
        self.steam_headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://steamcommunity.com/market/search?appid=730',
            'Connection': 'keep-alive'
        }
        
        self.logger.info("AsyncSteamListingScraper inicializado")
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Ejecuta el scraping de Steam Listings
        
        Returns:
            Lista de items con sus precios e iconos
        """
        try:
            self.logger.info("Iniciando scraping de Steam Listing")
            
            # Paso 1: Obtener el conteo total de items
            total_count = await self._get_total_count()
            
            if not total_count:
                self.logger.error("No se pudo obtener el conteo total de Steam")
                return []
            
            self.logger.info(f"Total de items disponibles: {total_count}")
            
            # Paso 2: Procesar items en lotes para evitar sobrecarga
            formatted_items = await self._process_items_async(total_count)
            
            # Generar estadísticas de precios
            if formatted_items:
                self._log_price_statistics(formatted_items)
            
            self.logger.info(
                f"Steam Listing scraping completado - "
                f"Items totales: {total_count}, "
                f"Items obtenidos: {len(formatted_items)}"
            )
            
            return formatted_items
            
        except Exception as e:
            self.logger.error(f"Error en scraping: {e}")
            raise
    
    async def _get_total_count(self) -> Optional[int]:
        """
        Obtiene el conteo total de items disponibles en Steam Market
        
        Returns:
            Número total de items o None si falla
        """
        if not self.session:
            await self.setup()
        
        # URL para obtener solo el conteo (1 item)
        url = self.base_url.format(0, 1)
        
        try:
            self.logger.debug("Obteniendo conteo total de items")
            
            # Rate limiting
            await self.rate_limiter.acquire()
            
            async with self.session.get(
                url,
                headers=self.steam_headers
            ) as response:
                if response.status == 429:
                    self.logger.warning("Rate limit hit obteniendo conteo total")
                    await asyncio.sleep(5)
                    return None
                elif response.status != 200:
                    self.logger.error(f"HTTP {response.status} obteniendo conteo total")
                    return None
                
                # Leer y parsear respuesta
                content = await response.read()
                if not content:
                    return None
                
                data = orjson.loads(content)
                
                total_count = data.get('total_count')
                if total_count:
                    return int(total_count)
                
                return None
                
        except Exception as e:
            self.logger.error(f"Error obteniendo conteo total: {e}")
            return None
    
    async def _process_items_async(self, total_count: int) -> List[Dict]:
        """
        Procesa items de forma asíncrona con control de concurrencia
        
        Args:
            total_count: Número total de items a procesar
            
        Returns:
            Lista de items formateados
        """
        formatted_items = []
        
        if not self.session:
            await self.setup()
        
        # Configurar el tamaño de lote (Steam permite hasta 100)
        batch_size = 10  # Conservador para evitar problemas
        total_batches = (total_count + batch_size - 1) // batch_size
        
        # Limitar el número de batches para evitar sobrecarga
        max_batches = min(total_batches, 1000)  # Máximo 10,000 items
        
        self.logger.info(f"Procesando {max_batches} lotes de {batch_size} items")
        
        # Crear semáforo para controlar concurrencia
        semaphore = asyncio.Semaphore(self.scraper_config.get('max_concurrent', 50))
        
        # Crear tareas asíncronas
        tasks = []
        for i in range(max_batches):
            start_index = i * batch_size
            task = self._fetch_batch_with_semaphore(semaphore, start_index, batch_size)
            tasks.append(task)
        
        # Ejecutar tareas en lotes para evitar sobrecarga
        batch_group_size = 10
        for i in range(0, len(tasks), batch_group_size):
            batch_group = tasks[i:i + batch_group_size]
            
            self.logger.info(f"Procesando grupo de lotes {i//batch_group_size + 1}/{(len(tasks) + batch_group_size - 1)//batch_group_size}")
            
            # Procesar grupo de lotes
            batch_results = await asyncio.gather(*batch_group, return_exceptions=True)
            
            # Recopilar resultados válidos
            for result in batch_results:
                if isinstance(result, list):
                    formatted_items.extend(result)
                elif isinstance(result, Exception):
                    self.logger.debug(f"Error en lote: {result}")
            
            # Pequeña pausa entre grupos de lotes
            if i + batch_group_size < len(tasks):
                await asyncio.sleep(1)
        
        return formatted_items
    
    async def _fetch_batch_with_semaphore(self, semaphore: asyncio.Semaphore, start: int, count: int) -> List[Dict]:
        """
        Fetch batch con control de semáforo
        
        Args:
            semaphore: Semáforo para controlar concurrencia
            start: Índice de inicio
            count: Número de items por lote
            
        Returns:
            Lista de items del lote o lista vacía
        """
        async with semaphore:
            return await self._fetch_batch(start, count)
    
    async def _fetch_batch(self, start: int, count: int) -> List[Dict]:
        """
        Obtiene un lote de items desde Steam Market
        
        Args:
            start: Índice de inicio
            count: Número de items a obtener
            
        Returns:
            Lista de items formateados
        """
        url = self.base_url.format(start, count)
        
        try:
            # Rate limiting
            await self.rate_limiter.acquire()
            
            self.logger.debug(f"Fetching batch start={start}, count={count}")
            
            # Update metrics
            self.metrics.requests_made += 1
            
            async with self.session.get(
                url,
                headers=self.steam_headers
            ) as response:
                if response.status == 429:
                    self.logger.warning(f"Rate limit hit para lote {start}")
                    await asyncio.sleep(3)
                    return []
                elif response.status != 200:
                    self.logger.debug(f"HTTP {response.status} para lote {start}")
                    self.metrics.requests_failed += 1
                    return []
                
                # Leer y parsear respuesta
                content = await response.read()
                if not content:
                    return []
                
                data = orjson.loads(content)
                
                # Update metrics
                self.metrics.requests_successful += 1
                
                # Extraer y formatear items
                if "results" in data and data["results"]:
                    return self._extract_items(data["results"])
                else:
                    return []
                
        except asyncio.TimeoutError:
            self.metrics.requests_failed += 1
            self.logger.debug(f"Timeout para lote {start}")
            return []
        except Exception as e:
            self.metrics.requests_failed += 1
            self.logger.debug(f"Error fetching lote {start}: {e}")
            return []
    
    def _extract_items(self, json_data: List) -> List[Dict]:
        """
        Extrae items de los datos JSON de Steam
        
        Args:
            json_data: Lista de datos JSON de items
            
        Returns:
            Lista de items formateados
        """
        items = []
        
        for item in json_data:
            try:
                # Obtener nombre del item
                name = item.get('name', 'Unknown')
                name = name.replace("/", "-")  # Limpiar caracteres problemáticos
                
                # Obtener precio de venta
                sell_price_cents = item.get('sell_price', 0)
                sell_price_dollars = sell_price_cents / 100.0
                
                # Extraer URL del icono
                icon_url = ""
                asset_desc = item.get('asset_description', {})
                if isinstance(asset_desc, dict):
                    icon_url_part = asset_desc.get('icon_url', '')
                    if icon_url_part:
                        icon_url = f"https://community.fastly.steamstatic.com/economy/image/{icon_url_part}"
                
                # Crear item formateado
                formatted_item = {
                    'name': name.strip(),
                    'price': round(float(sell_price_dollars), 2),
                    'platform': 'steam_listing',
                    'icon_url': icon_url,
                    'steam_listing_url': f"https://steamcommunity.com/market/listings/730/{name.replace(' ', '%20')}",
                    'last_update': datetime.now().isoformat()
                }
                
                items.append(formatted_item)
                
            except Exception as e:
                self.logger.warning(f"Error extrayendo item: {e}")
                continue
        
        return items
    
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
                self.logger.info("Steam Listing estadísticas - No hay precios válidos")
                return
            
            total_items = len(items)
            valid_prices = len(prices)
            avg_price = sum(prices) / valid_prices
            min_price = min(prices)
            max_price = max(prices)
            
            self.logger.info(
                f"Steam Listing estadísticas - "
                f"Items totales: {total_items}, "
                f"Con precio: {valid_prices} ({valid_prices/total_items*100:.1f}%), "
                f"Precio promedio: ${avg_price:.2f}, "
                f"Rango: ${min_price:.2f}-${max_price:.2f}"
            )
            
        except Exception as e:
            self.logger.warning(f"Error calculando estadísticas de precios: {e}")
    
    async def validate_item(self, item: Dict[str, Any]) -> bool:
        """
        Validación específica para items de Steam Listing
        
        Args:
            item: Item a validar
            
        Returns:
            True si es válido
        """
        # Validación base
        if not await super().validate_item(item):
            return False
        
        try:
            # Validaciones específicas de Steam Listing
            price = float(item['price'])
            if price < 0 or price > 100000:  # Steam puede tener items muy caros
                return False
            
            # Verificar que el nombre sea razonable
            name = item['name']
            if len(name.strip()) < 2 or len(name) > 300:
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
    
    print("\n=== Comparación de Rendimiento: Steam Listing ===\n")
    
    # Test asíncrono
    print("🚀 Ejecutando versión ASÍNCRONA...")
    start_async = time.time()
    
    async with AsyncSteamListingScraper(use_proxy=False) as scraper:
        items_async = await scraper.run()
    
    time_async = time.time() - start_async
    
    print(f"✅ Asíncrono completado:")
    print(f"   - Items: {len(items_async)}")
    print(f"   - Tiempo: {time_async:.2f}s")
    print(f"   - Métricas: {scraper.metrics.to_dict()}")
    
    # Comparar con versión síncrona (si existe)
    try:
        from scrapers.steam_listing_scraper import SteamListingScraper
        
        print("\n🐌 Ejecutando versión SÍNCRONA...")
        start_sync = time.time()
        
        sync_scraper = SteamListingScraper(use_proxy=False)
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
    async with AsyncSteamListingScraper(use_proxy=False) as scraper:
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