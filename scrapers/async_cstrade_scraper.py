"""
Async CS.Trade Scraper - BOT-VCSGO-BETA-V2

Versión asíncrona del scraper de CS.Trade con mejoras de rendimiento:
- Procesamiento asíncrono de la API
- Cálculo automático de precios reales (sin bono 50%)
- Control de rate limiting optimizado
- Conexiones persistentes optimizadas
- Manejo robusto de errores y reintentos
- Estadísticas de precios automáticas
- Validación de stock y tradable items
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


class AsyncCSTradeScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para CS.Trade
    
    Características:
    - API REST de CS.Trade
    - Procesamiento asíncrono de pricing data
    - Cálculo automático de precios reales (sin bono 50%)
    - Rate limiting adaptativo
    - Manejo de errores robusto con reintentos
    - Estadísticas de precios automáticas
    - Filtrado por stock y tradable items
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        """
        Inicializa el scraper de CS.Trade
        
        Args:
            use_proxy: Si usar proxy (None = usar configuración)
        """
        # Configuración específica de CS.Trade
        custom_config = {
            'rate_limit': 20,  # CS.Trade permite un rate limit moderado
            'burst_size': 3,   # 3 requests por burst
            'cache_ttl': 240,  # 4 minutos - precios cambian moderadamente
            'timeout_seconds': 25,
            'max_retries': 4,
            'max_concurrent': 8  # Buena concurrencia para CS.Trade
        }
        
        super().__init__(
            platform_name='cstrade',
            use_proxy=use_proxy,
            custom_config=custom_config
        )
        
        # URL de la API de CS.Trade
        self.api_url = "https://cdn.cs.trade:2096/api/prices_CSGO"
        self.bonus_rate = 50  # 50% tasa de bono por defecto
        
        # Headers específicos para CS.Trade
        self.cstrade_headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://cs.trade/',
            'Origin': 'https://cs.trade',
            'Connection': 'keep-alive'
        }
        
        self.logger.info(f"AsyncCSTradeScraper inicializado (tasa bono: {self.bonus_rate}%)")
    
    def _calculate_real_price(self, page_price: float, bonus_rate: float = None) -> float:
        """
        Calcula el precio real antes del bono
        
        Args:
            page_price: Precio mostrado en la página
            bonus_rate: Tasa de bono (por defecto usa self.bonus_rate)
            
        Returns:
            Precio real sin bono aplicado
        """
        if bonus_rate is None:
            bonus_rate = self.bonus_rate
        
        bonus_decimal = bonus_rate / 100
        real_price = page_price / (1 + bonus_decimal)
        return real_price
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Ejecuta el scraping de CS.Trade
        
        Returns:
            Lista de items con sus precios reales
        """
        try:
            self.logger.info("Iniciando scraping de CS.Trade")
            
            # Obtener datos de la API
            formatted_items = await self._fetch_pricing_data()
            
            # Generar estadísticas de precios
            if formatted_items:
                self._log_price_statistics(formatted_items)
            
            self.logger.info(
                f"CS.Trade scraping completado - "
                f"Items obtenidos: {len(formatted_items)}"
            )
            
            return formatted_items
            
        except Exception as e:
            self.logger.error(f"Error en scraping: {e}")
            raise
    
    async def _fetch_pricing_data(self) -> List[Dict]:
        """
        Obtiene datos de pricing de la API de CS.Trade
        
        Returns:
            Lista de items formateados
        """
        if not self.session:
            await self.setup()
        
        try:
            self.logger.debug("Obteniendo datos de pricing de CS.Trade API")
            
            # Rate limiting
            await self.rate_limiter.acquire()
            
            # Update metrics
            self.metrics.requests_made += 1
            request_start = time.time()
            
            async with self.session.get(
                self.api_url,
                headers=self.cstrade_headers
            ) as response:
                request_time = time.time() - request_start
                self.metrics.add_response_time(request_time)
                
                if response.status == 429:
                    self.logger.warning("Rate limit hit en CS.Trade")
                    self.metrics.rate_limit_hits += 1
                    await asyncio.sleep(5)
                    return []
                elif response.status != 200:
                    self.logger.error(f"HTTP {response.status} en CS.Trade API")
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
            self.logger.error("Timeout en CS.Trade API")
            return []
        except Exception as e:
            self.metrics.requests_failed += 1
            self.logger.error(f"Error fetching CS.Trade data: {e}")
            return []
    
    def _parse_api_response(self, data: Dict) -> List[Dict]:
        """
        Parsea la respuesta de la API de CS.Trade
        
        Args:
            data: Datos JSON de respuesta de la API
            
        Returns:
            Lista de items parseados
        """
        try:
            items = []
            
            for item_name, item_data in data.items():
                try:
                    # Verificar campos requeridos
                    if not isinstance(item_data, dict):
                        continue
                    
                    tradable = item_data.get('tradable', 0)
                    stock = item_data.get('have', 0)
                    original_price = item_data.get('price')
                    
                    # Verificar que el item tenga stock disponible y sea tradable
                    if (tradable == 0) or original_price is None or stock == 0:
                        continue
                    
                    # Convertir precio a float
                    price_float = float(original_price)
                    
                    # Calcular precio real sin bono
                    real_price = self._calculate_real_price(price_float)
                    
                    # Solo incluir items con precio válido
                    if real_price > 0:
                        # Limpiar nombre del item
                        name = item_name.replace("/", "-").strip()
                        
                        # Crear item con formato estándar
                        formatted_item = {
                            'name': name,
                            'price': round(real_price, 2),
                            'platform': 'cstrade',
                            'cstrade_url': f"https://cs.trade/trade?market_name={item_name.replace(' ', '%20')}",
                            'stock': stock,
                            'tradable': tradable,
                            'original_price': round(price_float, 2),
                            'bonus_rate': self.bonus_rate,
                            'last_update': datetime.now().isoformat()
                        }
                        
                        items.append(formatted_item)
                        
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Error procesando item {item_name}: {e}")
                    continue
            
            self.logger.info(f"Parseados {len(items)} items de CS.Trade")
            return items
            
        except Exception as e:
            self.logger.error(f"Error parseando respuesta de CS.Trade: {e}")
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
                self.logger.info("CS.Trade estadísticas - No hay precios válidos")
                return
            
            total_items = len(items)
            valid_prices = len(prices)
            avg_price = sum(prices) / valid_prices
            min_price = min(prices)
            max_price = max(prices)
            
            # Estadísticas de stock
            total_stock = sum(item['stock'] for item in items)
            avg_stock = total_stock / total_items if total_items > 0 else 0
            
            self.logger.info(
                f"CS.Trade estadísticas - "
                f"Items totales: {total_items}, "
                f"Con precio: {valid_prices} ({valid_prices/total_items*100:.1f}%), "
                f"Precio promedio: ${avg_price:.2f}, "
                f"Rango: ${min_price:.2f}-${max_price:.2f}, "
                f"Stock total: {total_stock}, Stock promedio: {avg_stock:.1f}"
            )
            
        except Exception as e:
            self.logger.warning(f"Error calculando estadísticas de precios: {e}")
    
    async def validate_item(self, item: Dict[str, Any]) -> bool:
        """
        Validación específica para items de CS.Trade
        
        Args:
            item: Item a validar
            
        Returns:
            True si es válido
        """
        # Validación base
        if not await super().validate_item(item):
            return False
        
        try:
            # Validaciones específicas de CS.Trade
            price = float(item['price'])
            if price < 0 or price > 50000:  # CS.Trade no suele tener items tan caros
                return False
            
            # Verificar que el nombre sea razonable
            name = item['name']
            if len(name.strip()) < 2 or len(name) > 200:
                return False
            
            # Verificar stock válido
            stock = item.get('stock', 0)
            if stock < 0 or stock > 10000:
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
    
    print("\n=== Comparación de Rendimiento: CS.Trade ===\n")
    
    # Test asíncrono
    print("🚀 Ejecutando versión ASÍNCRONA...")
    start_async = time.time()
    
    async with AsyncCSTradeScraper(use_proxy=False) as scraper:
        items_async = await scraper.run()
    
    time_async = time.time() - start_async
    
    print(f"✅ Asíncrono completado:")
    print(f"   - Items: {len(items_async)}")
    print(f"   - Tiempo: {time_async:.2f}s")
    print(f"   - Métricas: {scraper.metrics.to_dict()}")
    
    # Comparar con versión síncrona (si existe)
    try:
        from scrapers.cstrade_scraper import CSTradeScraper
        
        print("\n🐌 Ejecutando versión SÍNCRONA...")
        start_sync = time.time()
        
        sync_scraper = CSTradeScraper(use_proxy=False)
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
    async with AsyncCSTradeScraper(use_proxy=False) as scraper:
        items = await scraper.run()
        print(f"\n✅ Scraping completado: {len(items)} items")
        
        # Mostrar algunos items de ejemplo
        if items:
            print("\n📦 Primeros 5 items:")
            for item in items[:5]:
                print(f"  - {item['name']}: ${item['price']:.2f} (stock: {item['stock']})")
            
            # Mostrar estadísticas de precios
            prices = [item['price'] for item in items if item['price'] > 0]
            if prices:
                print(f"\n📊 Estadísticas de precios:")
                print(f"  - Precio mínimo: ${min(prices):.2f}")
                print(f"  - Precio máximo: ${max(prices):.2f}")
                print(f"  - Precio promedio: ${sum(prices)/len(prices):.2f}")
                
                # Estadísticas de stock
                total_stock = sum(item['stock'] for item in items)
                print(f"  - Stock total: {total_stock} items")
    
    # Ejecutar comparación de rendimiento
    await compare_performance()


if __name__ == "__main__":
    asyncio.run(main())