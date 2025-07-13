"""
White Async Scraper - BOT-vCSGO-Beta V2
Obtiene precios de White.market - marketplace con API JSON simple
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.async_base_scraper import AsyncBaseScraper


class AsyncWhiteScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para White.market
    Marketplace con API JSON simple (una sola petición HTTP)
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        # Configuración específica para White.market
        self.custom_config = {
            'rate_limit': 3,      # Conservador para API simple
            'burst_size': 1,      # 1 request por burst
            'cache_ttl': 300,     # 5 minutos
            'timeout_seconds': 30, # Timeout estándar
            'max_retries': 5,
            'max_concurrent': 1   # Solo una petición HTTP
        }
        
        super().__init__(
            platform_name="white",
            use_proxy=use_proxy,
            custom_config=self.custom_config
        )
        
        # URLs y endpoints
        self.api_url = "https://api.white.market/export/v1/prices/730.json"
        self.base_url = "https://white.market/"
        
        # Headers específicos para White.market
        self.white_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site'
        }
        
        self.logger.info("AsyncWhiteScraper inicializado para API JSON simple")
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Método principal de scraping que implementa la interfaz AsyncBaseScraper
        
        Returns:
            Lista de items scrapeados
        """
        return await self.fetch_data()
    
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Obtiene datos de White.market API (una sola petición HTTP)
        
        Returns:
            Lista de items con precios
        """
        self.logger.info("Iniciando scraping asíncrono de White.market...")
        
        try:
            async with self.session.get(
                self.api_url,
                headers=self.white_headers,
                timeout=aiohttp.ClientTimeout(total=self.custom_config['timeout_seconds'])
            ) as response:
                
                self.logger.info(f"Response status: {response.status}")
                
                if response.status != 200:
                    self.logger.error(f"Error HTTP {response.status} al obtener datos de White.market")
                    return []
                
                # Verificar que la respuesta no esté vacía
                text = await response.text()
                if not text.strip():
                    self.logger.error("Respuesta vacía de White.market")
                    return []
                
                # Parsear respuesta JSON
                data = await response.json()
                
                # Verificar que sea una lista
                if not isinstance(data, list):
                    self.logger.error(f"Formato inesperado en respuesta de White: {type(data)}")
                    return []
                
                self.logger.info(f"Recibidos {len(data)} items de White.market")
                
                # Procesar items
                processed_items = []
                
                for item in data:
                    try:
                        if not isinstance(item, dict):
                            continue
                        
                        # Validar campos requeridos
                        market_hash_name = item.get("market_hash_name")
                        price = item.get("price")
                        market_product_link = item.get("market_product_link")
                        
                        if market_hash_name and price is not None:
                            try:
                                price_float = float(price)
                            except (ValueError, TypeError):
                                self.logger.warning(f"Precio inválido para {market_hash_name}: {price}")
                                continue
                            
                            # Solo incluir items con precio válido
                            if price_float > 0:
                                formatted_item = {
                                    "name": market_hash_name,
                                    "price": price_float,
                                    "platform": "White",
                                    "url": market_product_link or self.base_url
                                }
                                processed_items.append(formatted_item)
                                
                    except Exception as e:
                        self.logger.warning(f"Error procesando item individual de White: {e}")
                        continue
                
                if processed_items:
                    # Obtener estadísticas
                    total_items = len(processed_items)
                    avg_price = sum(item['price'] for item in processed_items) / total_items
                    min_price = min(item['price'] for item in processed_items)
                    max_price = max(item['price'] for item in processed_items)
                    
                    self.logger.info(
                        f"White.market scraping completado: {total_items} items "
                        f"(precio promedio: ${avg_price:.2f}, rango: ${min_price:.2f}-${max_price:.2f})"
                    )
                else:
                    self.logger.warning("No se obtuvieron items válidos de White.market")
                
                return processed_items
                
        except asyncio.TimeoutError:
            self.logger.error("Timeout al obtener datos de White.market")
            return []
        except Exception as e:
            self.logger.error(f"Error en fetch_data de White.market: {e}")
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
            items = await self.fetch_data()
            
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
    async with AsyncWhiteScraper(use_proxy=False) as scraper:
        items = await scraper.run()
        
        print(f"Obtenidos {len(items)} items de White.market")
        
        # Mostrar algunos ejemplos
        if items:
            print("\nEjemplos de precios obtenidos:")
            for item in items[:5]:
                print(f"- {item['name']}: ${item['price']:.2f}")
        else:
            print("\nNOTA: White.market puede tener problemas de conectividad o API")
        
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