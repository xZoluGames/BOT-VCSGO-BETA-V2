"""
ManncoStore Async Scraper - BOT-vCSGO-Beta V2
Obtiene precios de ManncoStore.com - marketplace con paginación por skip
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
from pathlib import Path
import urllib.request
from urllib.error import HTTPError, URLError
import orjson
sys.path.append(str(Path(__file__).parent.parent))
from core.async_base_scraper import AsyncBaseScraper


class AsyncManncoStoreScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para ManncoStore.com
    Marketplace con API paginada usando parámetro skip
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        # Configuración específica para ManncoStore
        # API paginada, usar configuración moderada para múltiples requests
        self.custom_config = {
            'rate_limit': 10,     # Moderado para API paginada
            'burst_size': 3,      # 3 requests por burst para paginación
            'cache_ttl': 300,     # 5 minutos
            'timeout_seconds': 30, # Timeout estándar
            'max_retries': 3,
            'max_concurrent': 5   # Concurrencia moderada para paginación
        }
        
        super().__init__(
            platform_name="manncostore",
            use_proxy=use_proxy,
            custom_config=self.custom_config
        )
        
        # URLs y endpoints
        self.api_url_template = "https://mannco.store/items/get?price=DESC&page=1&i=0&game=730&skip={}"
        self.store_url = "https://mannco.store/item/"
        self.items_per_page = 50
        
        # Headers específicos para ManncoStore - usar los mismos que funcionan en sync
        self.manncostore_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
        }
        
        self.logger.info("AsyncManncoStoreScraper inicializado con configuración para paginación")
    
    def _transform_price(self, price) -> float:
        """
        Transforma el precio de entero a formato decimal
        
        Args:
            price: Precio en formato entero (ej: 1250 = 12.50)
            
        Returns:
            Precio en formato float
        """
        try:
            price_str = str(price)
            if len(price_str) > 2:
                return float(f"{price_str[:-2]}.{price_str[-2:]}")
            else:
                return float(f"0.{price_str.zfill(2)}")
        except (ValueError, TypeError):
            return 0.0
    
    async def _init_session(self):
        """
        Inicializa la sesión - removido, vamos directo a la API como en sync
        """
        # Removido: No visitar página principal, ir directo a la API como sync
        pass
    
    async def _fetch_page_data(self, skip: int) -> Optional[List[Dict[str, Any]]]:
        """
        Obtiene una página de datos usando el parámetro skip
        USANDO URLLIB COMO BYPASS - igual que sync pero en async wrapper
        
        Args:
            skip: Número de items a saltar
            
        Returns:
            Lista de items formateados o None si no hay más datos
        """
        url = self.api_url_template.format(skip)
        
        # Usar urllib.request como en sync pero en async wrapper
        def _sync_request():
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0')
            req.add_header('Accept', 'application/json, text/plain, */*')
            req.add_header('Accept-Language', 'es-ES,es;q=0.9,en;q=0.8')
            
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    raw = response.read().decode('utf-8')
                    data = orjson.loads(raw)
                    
                    if isinstance(data, list) and len(data) > 0:
                        formatted_items = []
                        for item in data:
                            try:
                                item_name = item.get('name', '')
                                price_raw = item.get('price', 0)
                                url_suffix = item.get('url', '')
                                
                                if not item_name or price_raw is None:
                                    continue
                                
                                # Transformar precio
                                price = self._transform_price(price_raw)
                                
                                # Solo incluir items con precio válido
                                if price > 0:
                                    formatted_item = {
                                        'Item': item_name,
                                        'Price': price,
                                        'Platform': 'ManncoStore',
                                        'URL': self.store_url + (url_suffix if url_suffix else "")
                                    }
                                    formatted_items.append(formatted_item)
                                    
                            except (ValueError, TypeError, KeyError) as e:
                                self.logger.warning(f"Error procesando item de ManncoStore: {item} - {e}")
                                continue
                        
                        return formatted_items
                    else:
                        return None
                        
            except HTTPError as e:
                self.logger.error(f"HTTPError al obtener datos (skip={skip}): {e.code} - {e.reason}")
                return None
            except URLError as e:
                self.logger.error(f"URLError al obtener datos (skip={skip}): {e.reason}")
                return None
            except orjson.JSONDecodeError as e:
                self.logger.error(f"Error JSON en skip={skip}: {e}")
                return None
            except Exception as e:
                self.logger.error(f"Error general en skip={skip}: {e}")
                return None
        
        # Ejecutar la función sync en un executor para mantener async
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _sync_request)
        except Exception as e:
            self.logger.error(f"Error en async wrapper para skip={skip}: {e}")
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
        Obtiene datos de ManncoStore API con paginación por skip
        
        Returns:
            Lista de items con precios
        """
        self.logger.info("Iniciando scraping asíncrono de ManncoStore con paginación...")
        
        skip = 0
        all_items = []
        
        try:
            # Ahora con los headers correctos de sync, debería funcionar
            while True:
                items = await self._fetch_page_data(skip)
                
                if items:
                    all_items.extend(items)
                    skip += self.items_per_page
                    self.logger.info(f"Obtenidos {len(items)} items de página skip={skip-self.items_per_page} (total: {len(all_items)})")
                    await asyncio.sleep(0.5)  # Rate limiting
                else:
                    break
            
            if all_items:
                # Obtener estadísticas
                total_items = len(all_items)
                avg_price = sum(item['Price'] for item in all_items) / total_items
                min_price = min(item['Price'] for item in all_items)
                max_price = max(item['Price'] for item in all_items)
                
                self.logger.info(
                    f"ManncoStore scraping completado: {total_items} items "
                    f"(precio promedio: ${avg_price:.2f}, rango: ${min_price:.2f}-${max_price:.2f})"
                )
            
            return all_items
            
        except Exception as e:
            self.logger.error(f"Error en fetch_data de ManncoStore: {e}")
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
                    if item['Item'] == item_name:
                        return item['Price']
            
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
    async with AsyncManncoStoreScraper(use_proxy=False) as scraper:
        items = await scraper.run()
        
        print(f"Obtenidos {len(items)} items de ManncoStore")
        
        # Mostrar algunos ejemplos
        if items:
            print("\nEjemplos de precios obtenidos:")
            for item in items[:5]:
                print(f"- {item['Item']}: ${item['Price']:.2f}")
        
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