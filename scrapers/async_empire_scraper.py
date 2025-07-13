"""
Async CSGOEmpire Scraper - BOT-VCSGO-BETA-V2

Versión asíncrona del scraper de CSGOEmpire con mejoras de rendimiento:
- Procesamiento paralelo de páginas auction/direct
- Rate limiting inteligente 
- Conversión automática de monedas Empire a USD
- Manejo robusto de errores con reintentos
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import orjson
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.async_base_scraper import AsyncBaseScraper
from core.exceptions import APIError, ParseError, ValidationError


class AsyncEmpireScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para CSGOEmpire
    
    Características:
    - Procesamiento paralelo de auction=yes y auction=no
    - Rate limiting automático
    - Conversión de monedas Empire a USD
    - Paginación asíncrona
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        """
        Inicializa el scraper de CSGOEmpire
        
        Args:
            use_proxy: Si usar proxy (None = usar configuración)
        """
        # Configuración específica de Empire
        custom_config = {
            'rate_limit': 60,  # Empire es más conservador
            'burst_size': 10,
            'cache_ttl': 300,  # 5 minutos
            'timeout_seconds': 30,
            'max_retries': 3
        }
        
        super().__init__(
            platform_name='empire',
            use_proxy=use_proxy,
            custom_config=custom_config
        )
        
        # URL de la API de CSGOEmpire
        self.api_base_url = 'https://csgoempire.com/api/v2/trading/items'
        
        # Tasa de conversión de monedas Empire a USD (calculada previamente)
        self.conversion_rate = 0.6154
        
        # Headers específicos para CSGOEmpire con API key
        self.empire_headers = {
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Agregar Authorization si hay API key
        if self.api_key:
            self.empire_headers['Authorization'] = f'Bearer {self.api_key}'
        
        # Configuración de paginación
        self.per_page = 2500  # Máximo permitido por Empire
        self.max_pages = 100  # Límite de seguridad
        
        self.logger.info(f"AsyncEmpireScraper inicializado - API Key: {'Sí' if self.api_key else 'No'}")
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Ejecuta el scraping de CSGOEmpire con procesamiento paralelo
        
        Returns:
            Lista de items con sus precios
        """
        try:
            if not self.api_key:
                self.logger.error("API key requerida para CSGOEmpire")
                raise APIError(self.platform_name, response_text="API key requerida")
            
            self.logger.info("Iniciando scraping de CSGOEmpire")
            
            # Procesar auction=yes y auction=no en paralelo
            tasks = [
                asyncio.create_task(self._fetch_items_by_auction_type("yes")),
                asyncio.create_task(self._fetch_items_by_auction_type("no"))
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verificar resultados
            items_auction = results[0] if not isinstance(results[0], Exception) else {}
            items_direct = results[1] if not isinstance(results[1], Exception) else {}
            
            if isinstance(results[0], Exception):
                self.logger.error(f"Error en auction=yes: {results[0]}")
            if isinstance(results[1], Exception):
                self.logger.error(f"Error en auction=no: {results[1]}")
            
            # Combinar y seleccionar mejores precios
            combined_items = self._combine_item_lists(items_auction, items_direct)
            
            # Formatear a estructura estándar
            formatted_items = self._format_items(combined_items)
            
            self.logger.info(
                f"CSGOEmpire scraping completado - "
                f"Auction: {len(items_auction)}, "
                f"Direct: {len(items_direct)}, "
                f"Final: {len(formatted_items)}"
            )
            
            return formatted_items
            
        except Exception as e:
            self.logger.error(f"Error en scraping: {e}")
            raise
    
    async def _fetch_items_by_auction_type(self, auction_type: str) -> Dict[str, Dict]:
        """
        Obtiene items de CSGOEmpire por tipo de subasta de forma asíncrona
        
        Args:
            auction_type: "yes" para subastas, "no" para compra directa
            
        Returns:
            Diccionario con items {nombre: {data}}
        """
        all_items = {}
        page = 1
        
        self.logger.info(f"Iniciando fetch para auction={auction_type}")
        
        while page <= self.max_pages:
            try:
                # Parámetros de la petición
                params = {
                    "per_page": self.per_page,
                    "page": page,
                    "order": "market_value",
                    "sort": "asc",
                    "auction": auction_type
                }
                
                self.logger.debug(f"Obteniendo página {page} con auction={auction_type}")
                
                # Realizar petición asíncrona
                data = await self._fetch_empire_page(params)
                
                if not data:
                    self.logger.warning(f"No data en página {page} para auction={auction_type}")
                    break
                
                items = data.get('data', [])
                
                if not items:
                    self.logger.info(f"No más items en página {page} para auction={auction_type}")
                    break
                
                # Procesar items de esta página
                page_processed = 0
                for item in items:
                    processed_item = self._process_empire_item(item)
                    if processed_item:
                        name = processed_item['name']
                        price_usd = processed_item['price_usd']
                        
                        # Guardar si es nuevo o tiene mejor precio
                        if name not in all_items or price_usd < all_items[name]['price_usd']:
                            all_items[name] = processed_item
                            page_processed += 1
                
                self.logger.debug(
                    f"Página {page}: {len(items)} items obtenidos, "
                    f"{page_processed} procesados para auction={auction_type}"
                )
                
                page += 1
                
                # Pequeña pausa entre páginas
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error en página {page} para auction={auction_type}: {e}")
                break
        
        self.logger.info(f"Total items únicos obtenidos con auction={auction_type}: {len(all_items)}")
        return all_items
    
    async def _fetch_empire_page(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fetch de una página específica de Empire
        
        Args:
            params: Parámetros de la petición
            
        Returns:
            Datos de la página o None si falla
        """
        if not self.session:
            await self.setup()
            
        try:
            async with self.session.get(
                self.api_base_url,
                params=params,
                headers=self.empire_headers
            ) as response:
                if response.status != 200:
                    self.logger.error(f"HTTP {response.status} en Empire API")
                    return None
                
                # Leer respuesta completa
                content = await response.read()
                text = content.decode('utf-8')
                data = orjson.loads(text)
                
                return data
                
        except Exception as e:
            self.logger.error(f"Error fetching Empire page: {e}")
            return None
    
    def _process_empire_item(self, item: Dict) -> Optional[Dict]:
        """
        Procesa un item individual de CSGOEmpire
        
        Args:
            item: Item raw de la API
            
        Returns:
            Item procesado o None si es inválido
        """
        try:
            name = item.get("market_name")
            market_value = item.get("market_value", 0)
            item_id = item.get("id")
            
            if not name or not isinstance(name, str):
                return None
            
            if not isinstance(market_value, (int, float)) or market_value <= 0:
                return None
            
            # Convertir centavos de monedas a monedas
            price_in_coins = float(market_value) / 100.0
            
            # Convertir monedas a USD
            price_usd = price_in_coins * self.conversion_rate
            
            # Filtrar precios muy bajos o muy altos
            if price_usd < 0.01 or price_usd > 50000:
                return None
            
            return {
                'name': name.strip(),
                'price_usd': round(price_usd, 3),
                'price_coins': round(price_in_coins, 3),
                'market_value_cents': market_value,
                'item_id': item_id,
                'platform': 'empire',
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.warning(f"Error procesando item de Empire: {e}")
            return None
    
    def _combine_item_lists(self, items_auction: Dict, items_direct: Dict) -> Dict:
        """
        Combina listas de items seleccionando mejores precios
        
        Args:
            items_auction: Items de subastas
            items_direct: Items de compra directa
            
        Returns:
            Items combinados con mejores precios
        """
        combined = items_auction.copy()
        
        for name, item_data in items_direct.items():
            if name not in combined or item_data['price_usd'] < combined[name]['price_usd']:
                combined[name] = item_data
        
        self.logger.debug(
            f"Combinación completada - "
            f"Auction: {len(items_auction)}, "
            f"Direct: {len(items_direct)}, "
            f"Combined: {len(combined)}"
        )
        
        return combined
    
    def _format_items(self, items_dict: Dict) -> List[Dict]:
        """
        Formatea items al formato estándar del sistema asíncrono
        
        Args:
            items_dict: Diccionario de items procesados
            
        Returns:
            Lista de items en formato estándar
        """
        formatted_items = []
        
        for name, item_data in items_dict.items():
            formatted_item = {
                'name': name,
                'price': item_data['price_usd'],
                'platform': 'empire',
                'quantity': 1,  # Empire no proporciona cantidad
                'empire_url': f"https://csgoempire.com/item/{item_data.get('item_id', '')}",
                'original_price_coins': item_data['price_coins'],
                'conversion_rate': self.conversion_rate,
                'last_update': item_data['last_update']
            }
            
            formatted_items.append(formatted_item)
        
        # Ordenar por precio ascendente
        formatted_items.sort(key=lambda x: x['price'])
        
        return formatted_items
    
    async def validate_item(self, item: Dict[str, Any]) -> bool:
        """
        Validación específica para items de CSGOEmpire
        
        Args:
            item: Item a validar
            
        Returns:
            True si es válido
        """
        # Validación base
        if not await super().validate_item(item):
            return False
        
        try:
            # Validaciones específicas de Empire
            price = float(item['price'])
            if price < 0.01 or price > 50000:
                return False
            
            # Verificar que tenga datos de Empire
            if 'original_price_coins' not in item:
                return False
            
            return True
            
        except (ValueError, TypeError, KeyError):
            return False


async def compare_performance():
    """
    Función para comparar rendimiento con versión síncrona
    """
    import time
    
    print("\n=== Comparación de Rendimiento: CSGOEmpire ===\n")
    
    # Test asíncrono
    print("🚀 Ejecutando versión ASÍNCRONA...")
    start_async = time.time()
    
    async with AsyncEmpireScraper(use_proxy=False) as scraper:
        items_async = await scraper.run()
    
    time_async = time.time() - start_async
    
    print(f"✅ Asíncrono completado:")
    print(f"   - Items: {len(items_async)}")
    print(f"   - Tiempo: {time_async:.2f}s")
    print(f"   - Métricas: {scraper.metrics.to_dict()}")
    
    # Comparar con versión síncrona (si existe)
    try:
        from scrapers.empire_scraper import CSGOEmpireScraper
        
        print("\n🐌 Ejecutando versión SÍNCRONA...")
        start_sync = time.time()
        
        sync_scraper = CSGOEmpireScraper(use_proxy=False)
        items_sync = sync_scraper.fetch_data()
        
        time_sync = time.time() - start_sync
        
        print(f"✅ Síncrono completado:")
        print(f"   - Items: {len(items_sync)}")
        print(f"   - Tiempo: {time_sync:.2f}s")
        
        # Calcular mejora
        if time_sync > 0:
            improvement = ((time_sync - time_async) / time_sync) * 100
            speedup = time_sync / time_async
            
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
    async with AsyncEmpireScraper(use_proxy=False) as scraper:
        items = await scraper.run()
        print(f"\n✅ Scraping completado: {len(items)} items")
        
        # Mostrar algunos items de ejemplo
        if items:
            print("\n📦 Primeros 5 items:")
            for item in items[:5]:
                print(f"  - {item['name']}: ${item['price']:.2f}")
    
    # Ejecutar comparación de rendimiento
    await compare_performance()


if __name__ == "__main__":
    asyncio.run(main())