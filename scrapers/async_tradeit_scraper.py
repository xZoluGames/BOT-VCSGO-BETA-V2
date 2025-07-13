"""
TradeitGG Async Scraper - BOT-vCSGO-Beta V2
Obtiene precios de TradeIt.gg - marketplace con API paginada
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.async_base_scraper import AsyncBaseScraper


class AsyncTradeitScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para TradeIt.gg
    Marketplace con API paginada usando offset/limit
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        # Configuración específica para TradeitGG
        # API paginada, usar configuración moderada para múltiples requests
        self.custom_config = {
            'rate_limit': 5,      # Conservador para API paginada
            'burst_size': 2,      # 2 requests por burst para paginación
            'cache_ttl': 300,     # 5 minutos
            'timeout_seconds': 30, # Timeout estándar
            'max_retries': 5,
            'max_concurrent': 3   # Concurrencia baja para API paginada
        }
        
        super().__init__(
            platform_name="tradeit",
            use_proxy=use_proxy,
            custom_config=self.custom_config
        )
        
        # URLs y endpoints
        self.api_url = "https://tradeit.gg/api/v2/inventory/data"
        self.base_url = "https://tradeit.gg/"
        self.items_per_page = 1000
        self.app_id = "730"  # CS:GO
        
        # Headers específicos para TradeitGG
        self.tradeit_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://tradeit.gg/',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        
        self.logger.info("AsyncTradeitScraper inicializado con configuración para paginación")
    
    async def _fetch_page_data(self, offset: int) -> Optional[List[Dict[str, Any]]]:
        """
        Obtiene una página de datos usando el parámetro offset
        
        Args:
            offset: Número de items a saltar
            
        Returns:
            Lista de items formateados o None si no hay más datos
        """
        params = {
            'gameId': self.app_id,
            'sortType': 'Popularity',
            'offset': offset,
            'limit': self.items_per_page,
            'fresh': 'true'
        }
        
        try:
            async with self.session.get(
                self.api_url,
                params=params,
                headers=self.tradeit_headers,
                timeout=aiohttp.ClientTimeout(total=self.custom_config['timeout_seconds'])
            ) as response:
                if response.status != 200:
                    self.logger.error(f"Error HTTP {response.status} al obtener página offset={offset}")
                    return None
                
                # Leer respuesta como JSON
                data = await response.json()
                
                # Verificar si tenemos datos válidos
                items = data.get('items', [])
                if not items:
                    return None
                
                formatted_items = []
                for item in items:
                    try:
                        item_name = item.get('name', '')
                        price_for_trade = item.get('priceForTrade', 0)
                        
                        if not item_name or price_for_trade is None:
                            continue
                        
                        # Convertir precio: priceForTrade / 100
                        price = float(price_for_trade) / 100.0
                        
                        # Solo incluir items con precio válido
                        if price > 0:
                            formatted_item = {
                                'name': item_name,
                                'price': price,
                                'platform': 'tradeit',
                                'tradeit_url': f"https://tradeit.gg/csgo/trade?search={item_name.replace(' ', '%20')}",
                                'original_price': price_for_trade,
                                'last_update': datetime.now().isoformat()
                            }
                            formatted_items.append(formatted_item)
                            
                    except (ValueError, TypeError, KeyError) as e:
                        self.logger.warning(f"Error procesando item de TradeitGG: {item} - {e}")
                        continue
                
                return formatted_items
                
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout al obtener página offset={offset}")
            return None
        except Exception as e:
            self.logger.error(f"Error obteniendo página offset={offset}: {e}")
            return None
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Método principal de scraping que implementa la interfaz AsyncBaseScraper
        
        Returns:
            Lista de items scrapeados
        """
        return await self.fetch_data()
    
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Obtiene datos de TradeitGG API con paginación por offset
        
        Returns:
            Lista de items con precios
        """
        self.logger.info("Iniciando scraping asíncrono de TradeitGG con paginación...")
        
        offset = 0
        all_items = []
        max_retries = 5
        retry_count = 0
        
        try:
            while True:
                items = await self._fetch_page_data(offset)
                
                if items:
                    # Reiniciar contador de reintentos al encontrar items
                    retry_count = 0
                    all_items.extend(items)
                    items_fetched = len(items)
                    offset += items_fetched
                    
                    self.logger.info(f"Obtenidos {items_fetched} items de página offset={offset-items_fetched} (total: {len(all_items)})")
                    
                    # Rate limiting entre páginas
                    await asyncio.sleep(0.5)
                else:
                    # No hay más datos o error
                    retry_count += 1
                    self.logger.warning(f"No items found at offset {offset}. Retry count: {retry_count}/{max_retries}")
                    
                    if retry_count >= max_retries:
                        self.logger.info(f"Max retry limit ({max_retries}) reached. Stopping scraping.")
                        break
                    
                    # Pausa antes de reintentar
                    await asyncio.sleep(1)
            
            if all_items:
                # Obtener estadísticas
                total_items = len(all_items)
                avg_price = sum(item['price'] for item in all_items) / total_items
                min_price = min(item['price'] for item in all_items)
                max_price = max(item['price'] for item in all_items)
                
                self.logger.info(
                    f"TradeitGG scraping completado: {total_items} items "
                    f"(precio promedio: ${avg_price:.2f}, rango: ${min_price:.2f}-${max_price:.2f})"
                )
            
            return all_items
            
        except Exception as e:
            self.logger.error(f"Error en fetch_data de TradeitGG: {e}")
            return []
    
    async def get_item_price(self, item_name: str) -> Optional[float]:
        """
        Obtiene el precio de un item específico
        
        Args:
            item_name: Nombre del item
            
        Returns:
            Precio del item o None si no se encuentra
        """
        try:
            # Buscar solo en la primera página
            items = await self._fetch_page_data(0)
            
            if items:
                for item in items:
                    if item['name'] == item_name:
                        return item['price']
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error obteniendo precio para {item_name}: {e}")
            return None


async def main():
    """Función principal para testing"""
    import logging
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Ejecutar scraper
    async with AsyncTradeitScraper(use_proxy=False) as scraper:
        items = await scraper.run()
        
        print(f"Obtenidos {len(items)} items de TradeitGG")
        
        # Mostrar algunos ejemplos
        if items:
            print("\nEjemplos de precios obtenidos:")
            for item in items[:5]:
                print(f"- {item['name']}: ${item['price']:.2f}")
        
        # Mostrar estadísticas finales
        try:
            metrics = scraper.get_metrics()
            print(f"\nMétricas finales:")
            print(f"- Requests realizados: {metrics.requests_made}")
            print(f"- Items procesados: {metrics.total_items_scraped}")
            print(f"- Tiempo total: {metrics.total_time:.2f}s")
        except AttributeError:
            print("\nMétricas no disponibles en esta versión")


if __name__ == "__main__":
    asyncio.run(main())