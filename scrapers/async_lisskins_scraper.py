"""
Async LisSkins Scraper - BOT-VCSGO-BETA-V2

Versión asíncrona del scraper de LisSkins con mejoras de rendimiento:
- Procesamiento asíncrono de la API
- Lógica de deduplicación: mantiene el item más barato por nombre
- Control de rate limiting optimizado
- Conexiones persistentes optimizadas
- Manejo robusto de errores y reintentos
- Estadísticas de precios automáticas
- Formateo de URLs para items individuales
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


class AsyncLisskinsScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para LisSkins.com
    
    Características:
    - API REST de LisSkins
    - Procesamiento asíncrono de pricing data
    - Lógica de deduplicación por precio (mantiene el más barato)
    - Rate limiting adaptativo
    - Manejo de errores robusto con reintentos
    - Estadísticas de precios automáticas
    - Formateo automático de URLs de items
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        """
        Inicializa el scraper de LisSkins
        
        Args:
            use_proxy: Si usar proxy (None = usar configuración)
        """
        # Configuración específica de LisSkins
        custom_config = {
            'rate_limit': 10,  # LisSkins más conservador por el JSON grande
            'burst_size': 1,   # 1 request por burst para evitar sobrecarga
            'cache_ttl': 300,  # 5 minutos - precios cambian moderadamente
            'timeout_seconds': 60,  # Timeout más largo para API grande
            'max_retries': 3,
            'max_concurrent': 3  # Concurrencia baja para LisSkins por el JSON grande
        }
        
        super().__init__(
            platform_name='lisskins',
            use_proxy=use_proxy,
            custom_config=custom_config
        )
        
        # URL de la API de LisSkins
        self.api_url = 'https://lis-skins.com/market_export_json/api_csgo_full.json'
        
        # Headers específicos para LisSkins
        self.lisskins_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://lis-skins.com/',
            'Connection': 'keep-alive'
        }
        
        self.logger.info("AsyncLisskinsScraper inicializado")
    
    def _format_url_name(self, item_name: str) -> str:
        """
        Formatea el nombre del item para la URL (lógica original)
        
        Args:
            item_name: Nombre del item a formatear
            
        Returns:
            Nombre formateado para URL
        """
        chars_to_remove = "™(),/|"
        
        for char in chars_to_remove:
            item_name = item_name.replace(char, '')
        
        item_name = item_name.replace(' ', '-')
        
        while '--' in item_name:
            item_name = item_name.replace('--', '-')
        
        return item_name.strip('-')
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Ejecuta el scraping de LisSkins
        
        Returns:
            Lista de items con sus precios (deduplicados)
        """
        try:
            self.logger.info("Iniciando scraping de LisSkins")
            
            # Obtener datos de la API
            formatted_items = await self._fetch_pricing_data()
            
            # Generar estadísticas de precios
            if formatted_items:
                self._log_price_statistics(formatted_items)
            
            self.logger.info(
                f"LisSkins scraping completado - "
                f"Items obtenidos: {len(formatted_items)}"
            )
            
            return formatted_items
            
        except Exception as e:
            self.logger.error(f"Error en scraping: {e}")
            raise
    
    async def _fetch_pricing_data(self) -> List[Dict]:
        """
        Obtiene datos de pricing de la API de LisSkins
        
        Returns:
            Lista de items formateados y deduplicados
        """
        if not self.session:
            await self.setup()
        
        try:
            self.logger.debug("Obteniendo datos de pricing de LisSkins API")
            
            # Rate limiting
            await self.rate_limiter.acquire()
            
            # Update metrics
            self.metrics.requests_made += 1
            request_start = time.time()
            
            async with self.session.get(
                self.api_url,
                headers=self.lisskins_headers
            ) as response:
                request_time = time.time() - request_start
                self.metrics.add_response_time(request_time)
                
                if response.status == 429:
                    self.logger.warning("Rate limit hit en LisSkins")
                    self.metrics.rate_limit_hits += 1
                    await asyncio.sleep(5)
                    return []
                elif response.status != 200:
                    self.logger.error(f"HTTP {response.status} en LisSkins API")
                    self.metrics.requests_failed += 1
                    return []
                
                # Leer y parsear respuesta
                content = await response.read()
                if not content:
                    self.metrics.requests_failed += 1
                    return []
                
                data = orjson.loads(content)
                
                # Update metrics
                self.metrics.requests_successful += 1
                
                # Parsear y formatear items
                return self._parse_api_response(data)
                
        except asyncio.TimeoutError:
            self.metrics.requests_failed += 1
            self.logger.error("Timeout en LisSkins API")
            return []
        except Exception as e:
            self.metrics.requests_failed += 1
            self.logger.error(f"Error fetching LisSkins data: {e}")
            return []
    
    def _parse_api_response(self, data: Dict) -> List[Dict]:
        """
        Parsea la respuesta de la API de LisSkins
        
        Usa lógica de deduplicación: mantiene el item más barato por nombre
        
        Args:
            data: Datos JSON de respuesta de la API
            
        Returns:
            Lista de items parseados y deduplicados
        """
        try:
            # Diccionario para almacenar el item más barato de cada nombre
            cheapest_items = {}
            
            for item in data.get('items', []):
                try:
                    name = item.get('name')
                    price = item.get('price')
                    
                    if not name or price is None:
                        continue
                    
                    # Convertir precio a float
                    price_float = float(price)
                    
                    # Limpiar nombre del item
                    name = name.replace("/", "-").strip()
                    
                    if name in cheapest_items:
                        # Si ya existe, mantener el más barato
                        if price_float < cheapest_items[name]['price']:
                            cheapest_items[name] = {
                                'name': name,
                                'price': round(price_float, 2),
                                'platform': 'lisskins',
                                'lisskins_url': f"https://lis-skins.com/en/market/csgo/{self._format_url_name(name)}",
                                'last_update': datetime.now().isoformat()
                            }
                    else:
                        # Nuevo item
                        cheapest_items[name] = {
                            'name': name,
                            'price': round(price_float, 2),
                            'platform': 'lisskins',
                            'lisskins_url': f"https://lis-skins.com/en/market/csgo/{self._format_url_name(name)}",
                            'last_update': datetime.now().isoformat()
                        }
                        
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Error procesando item {name}: {e}")
                    continue
            
            items = list(cheapest_items.values())
            self.logger.info(f"Parseados {len(items)} items de LisSkins (deduplicados por precio)")
            return items
            
        except Exception as e:
            self.logger.error(f"Error parseando respuesta de LisSkins: {e}")
            return []
    
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
                self.logger.info("LisSkins estadísticas - No hay precios válidos")
                return
            
            total_items = len(items)
            valid_prices = len(prices)
            avg_price = sum(prices) / valid_prices
            min_price = min(prices)
            max_price = max(prices)
            
            self.logger.info(
                f"LisSkins estadísticas - "
                f"Items totales: {total_items}, "
                f"Con precio: {valid_prices} ({valid_prices/total_items*100:.1f}%), "
                f"Precio promedio: ${avg_price:.2f}, "
                f"Rango: ${min_price:.2f}-${max_price:.2f}"
            )
            
        except Exception as e:
            self.logger.warning(f"Error calculando estadísticas de precios: {e}")
    
    async def validate_item(self, item: Dict[str, Any]) -> bool:
        """
        Validación específica para items de LisSkins
        
        Args:
            item: Item a validar
            
        Returns:
            True si es válido
        """
        # Validación base
        if not await super().validate_item(item):
            return False
        
        try:
            # Validaciones específicas de LisSkins
            price = float(item['price'])
            if price < 0 or price > 25000:  # LisSkins no suele tener items tan caros
                return False
            
            # Verificar que el nombre sea razonable
            name = item['name']
            if len(name.strip()) < 2 or len(name) > 200:
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
    
    print("\n=== Comparación de Rendimiento: LisSkins ===\n")
    
    # Test asíncrono
    print("🚀 Ejecutando versión ASÍNCRONA...")
    start_async = time.time()
    
    async with AsyncLisskinsScraper(use_proxy=False) as scraper:
        items_async = await scraper.run()
    
    time_async = time.time() - start_async
    
    print(f"✅ Asíncrono completado:")
    print(f"   - Items: {len(items_async)}")
    print(f"   - Tiempo: {time_async:.2f}s")
    print(f"   - Métricas: {scraper.metrics.to_dict()}")
    
    # Comparar con versión síncrona (si existe)
    try:
        from scrapers.lisskins_scraper import LisskinsScraper
        
        print("\n🐌 Ejecutando versión SÍNCRONA...")
        start_sync = time.time()
        
        sync_scraper = LisskinsScraper(use_proxy=False)
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
    async with AsyncLisskinsScraper(use_proxy=False) as scraper:
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