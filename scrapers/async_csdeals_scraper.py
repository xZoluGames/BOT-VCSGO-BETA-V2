"""
Async CS.Deals Scraper - BOT-VCSGO-BETA-V2

Versión asíncrona del scraper de CS.Deals con mejoras de rendimiento:
- Procesamiento asíncrono de la API
- Control de rate limiting optimizado
- Conexiones persistentes optimizadas
- Manejo robusto de errores y reintentos
- Estadísticas de precios automáticas
- Validación de estructura de respuesta success
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


class AsyncCSDealsScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para CS.Deals
    
    Características:
    - API REST de CS.Deals
    - Procesamiento asíncrono de pricing data
    - Rate limiting adaptativo
    - Manejo de errores robusto con reintentos
    - Estadísticas de precios automáticas
    - Validación de estructura success en respuesta
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        """
        Inicializa el scraper de CS.Deals
        
        Args:
            use_proxy: Si usar proxy (None = usar configuración)
        """
        # Configuración específica de CS.Deals
        custom_config = {
            'rate_limit': 30,  # CS.Deals permite un rate limit moderado
            'burst_size': 5,   # 5 requests por burst
            'cache_ttl': 180,  # 3 minutos - precios cambian moderadamente
            'timeout_seconds': 30,
            'max_retries': 5,
            'max_concurrent': 10  # Buena concurrencia para CS.Deals
        }
        
        super().__init__(
            platform_name='csdeals',
            use_proxy=use_proxy,
            custom_config=custom_config
        )
        
        # URL de la API de CS.Deals
        self.api_url = 'https://cs.deals/API/IPricing/GetLowestPrices/v1?appid=730'
        
        # Headers específicos para CS.Deals
        self.csdeals_headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://cs.deals/',
            'Connection': 'keep-alive'
        }
        
        self.logger.info("AsyncCSDealsScraper inicializado")
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Ejecuta el scraping de CS.Deals
        
        Returns:
            Lista de items con sus precios
        """
        try:
            self.logger.info("Iniciando scraping de CS.Deals")
            
            # Obtener datos de la API
            formatted_items = await self._fetch_pricing_data()
            
            # Generar estadísticas de precios
            if formatted_items:
                self._log_price_statistics(formatted_items)
            
            self.logger.info(
                f"CS.Deals scraping completado - "
                f"Items obtenidos: {len(formatted_items)}"
            )
            
            return formatted_items
            
        except Exception as e:
            self.logger.error(f"Error en scraping: {e}")
            raise
    
    async def _fetch_pricing_data(self) -> List[Dict]:
        """
        Obtiene datos de pricing de la API de CS.Deals
        
        Returns:
            Lista de items formateados
        """
        if not self.session:
            await self.setup()
        
        try:
            self.logger.debug("Obteniendo datos de pricing de CS.Deals API")
            
            # Rate limiting
            await self.rate_limiter.acquire()
            
            # Update metrics
            self.metrics.requests_made += 1
            request_start = time.time()
            
            async with self.session.get(
                self.api_url,
                headers=self.csdeals_headers
            ) as response:
                request_time = time.time() - request_start
                self.metrics.add_response_time(request_time)
                
                if response.status == 429:
                    self.logger.warning("Rate limit hit en CS.Deals")
                    self.metrics.rate_limit_hits += 1
                    await asyncio.sleep(5)
                    return []
                elif response.status != 200:
                    self.logger.error(f"HTTP {response.status} en CS.Deals API")
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
            self.logger.error("Timeout en CS.Deals API")
            return []
        except Exception as e:
            self.metrics.requests_failed += 1
            self.logger.error(f"Error fetching CS.Deals data: {e}")
            return []
    
    def _parse_api_response(self, response_data: Dict) -> List[Dict]:
        """
        Parsea la respuesta de la API de CS.Deals
        
        Args:
            response_data: Datos JSON de respuesta de la API
            
        Returns:
            Lista de items parseados
        """
        try:
            # Verificar estructura de respuesta de CS.Deals
            if not response_data.get('success'):
                self.logger.error(f"Respuesta no exitosa de CS.Deals: {response_data}")
                return []
            
            # CS.Deals tiene la estructura: data -> response -> items
            if 'response' not in response_data or 'items' not in response_data['response']:
                self.logger.warning("Estructura inesperada en respuesta de CS.Deals")
                return []
            
            # Procesar items
            items = []
            for item in response_data['response']['items']:
                try:
                    # Obtener campos necesarios
                    name = item.get('marketname')
                    price = item.get('lowest_price')
                    
                    if not name or price is None:
                        continue
                    
                    # Limpiar nombre del item
                    name = name.replace("/", "-").strip()
                    
                    # Crear item con formato estándar
                    formatted_item = {
                        'name': name,
                        'price': round(float(price), 2),  # CS.Deals ya devuelve el precio en formato decimal
                        'platform': 'csdeals',
                        'csdeals_url': f"https://cs.deals/new?name={name.replace(' ', '%20')}&game=csgo&sort=price&sort_desc=0",
                        'last_update': datetime.now().isoformat()
                    }
                    
                    # Información adicional si está disponible
                    if item.get('quantity'):
                        formatted_item['quantity'] = item['quantity']
                    
                    if item.get('condition'):
                        formatted_item['condition'] = item['condition']
                    
                    items.append(formatted_item)
                    
                except Exception as e:
                    self.logger.warning(f"Error procesando item individual: {e}")
                    continue
            
            self.logger.info(f"Parseados {len(items)} items de CS.Deals")
            return items
            
        except Exception as e:
            self.logger.error(f"Error parseando respuesta de CS.Deals: {e}")
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
                self.logger.info("CS.Deals estadísticas - No hay precios válidos")
                return
            
            total_items = len(items)
            valid_prices = len(prices)
            avg_price = sum(prices) / valid_prices
            min_price = min(prices)
            max_price = max(prices)
            
            self.logger.info(
                f"CS.Deals estadísticas - "
                f"Items totales: {total_items}, "
                f"Con precio: {valid_prices} ({valid_prices/total_items*100:.1f}%), "
                f"Precio promedio: ${avg_price:.2f}, "
                f"Rango: ${min_price:.2f}-${max_price:.2f}"
            )
            
        except Exception as e:
            self.logger.warning(f"Error calculando estadísticas de precios: {e}")
    
    async def validate_item(self, item: Dict[str, Any]) -> bool:
        """
        Validación específica para items de CS.Deals
        
        Args:
            item: Item a validar
            
        Returns:
            True si es válido
        """
        # Validación base
        if not await super().validate_item(item):
            return False
        
        try:
            # Validaciones específicas de CS.Deals
            price = float(item['price'])
            if price < 0 or price > 50000:  # CS.Deals no suele tener items tan caros
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
    
    print("\n=== Comparación de Rendimiento: CS.Deals ===\n")
    
    # Test asíncrono
    print("🚀 Ejecutando versión ASÍNCRONA...")
    start_async = time.time()
    
    async with AsyncCSDealsScraper(use_proxy=False) as scraper:
        items_async = await scraper.run()
    
    time_async = time.time() - start_async
    
    print(f"✅ Asíncrono completado:")
    print(f"   - Items: {len(items_async)}")
    print(f"   - Tiempo: {time_async:.2f}s")
    print(f"   - Métricas: {scraper.metrics.to_dict()}")
    
    # Comparar con versión síncrona (si existe)
    try:
        from scrapers.csdeals_scraper import CSDealsScraper
        
        print("\n🐌 Ejecutando versión SÍNCRONA...")
        start_sync = time.time()
        
        sync_scraper = CSDealsScraper(use_proxy=False)
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
    async with AsyncCSDealsScraper(use_proxy=False) as scraper:
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