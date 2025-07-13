"""
MarketCSGO Async Scraper - BOT-vCSGO-Beta V2
Obtiene precios de Market.CSGO.com - marketplace ruso popular
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.async_base_scraper import AsyncBaseScraper


class AsyncMarketCSGOScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para Market.CSGO.com
    Marketplace ruso con API JSON simple
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        # Configuración específica para MarketCSGO
        # API simple con respuesta JSON grande, usar configuración conservadora
        self.custom_config = {
            'rate_limit': 5,      # Conservador para API rusa
            'burst_size': 1,      # Un request por burst
            'cache_ttl': 300,     # 5 minutos
            'timeout_seconds': 45, # Timeout generoso para API internacional
            'max_retries': 3,
            'max_concurrent': 2   # Muy conservador para API externa
        }
        
        super().__init__(
            platform_name="marketcsgo",
            use_proxy=use_proxy,
            custom_config=self.custom_config
        )
        
        # URLs y endpoints
        self.api_url = "https://market.csgo.com/api/v2/prices/USD.json"
        
        # Headers específicos para MarketCSGO
        self.marketcsgo_headers = {
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'Referer': 'https://market.csgo.com/',
            'Origin': 'https://market.csgo.com'
        }
        
        self.logger.info("AsyncMarketCSGOScraper inicializado con configuración conservadora")
    
    def _format_url_name(self, name: str) -> str:
        """
        Formatea el nombre del item para URL de MarketCSGO
        
        Args:
            name: Nombre del item
            
        Returns:
            Nombre formateado para URL
        """
        return name.replace(' ', '%20').replace('|', '%7C')
    
    async def _parse_api_response(self, data: Dict) -> List[Dict[str, Any]]:
        """
        Parsea la respuesta de MarketCSGO API
        
        Args:
            data: Datos JSON de la API
            
        Returns:
            Lista de items parseados
        """
        try:
            # Verificar que la respuesta sea exitosa
            if not data.get("success", False):
                self.logger.error("API de MarketCSGO reportó error: respuesta no exitosa")
                return []
            
            # Obtener items del array
            raw_items = data.get("items", [])
            if not raw_items:
                self.logger.warning("No se encontraron items en la respuesta de MarketCSGO")
                return []
            
            items = []
            for item in raw_items:
                try:
                    # Extraer datos del item
                    item_name = item.get("market_hash_name")
                    price_value = item.get("price")
                    
                    if not item_name or price_value is None:
                        continue
                    
                    # Convertir precio a float
                    price = float(price_value)
                    
                    # Solo incluir items con precio válido
                    if price > 0:
                        parsed_item = {
                            'name': item_name,
                            'price': round(price, 2),
                            'platform': 'marketcsgo',
                            'marketcsgo_url': f"https://market.csgo.com/es/{self._format_url_name(item_name)}",
                            'last_update': datetime.now().isoformat()
                        }
                        items.append(parsed_item)
                        
                except (ValueError, TypeError, KeyError) as e:
                    self.logger.warning(f"Error procesando item de MarketCSGO: {item} - {e}")
                    continue
            
            self.logger.info(f"Procesados {len(items)} items válidos de MarketCSGO")
            return items
            
        except Exception as e:
            self.logger.error(f"Error parseando respuesta de MarketCSGO: {e}")
            return []
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Método principal de scraping que implementa la interfaz AsyncBaseScraper
        
        Returns:
            Lista de items scrapeados
        """
        return await self.fetch_data()
    
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Obtiene datos de MarketCSGO API
        
        Returns:
            Lista de items con precios
        """
        self.logger.info("Iniciando scraping asíncrono de MarketCSGO...")
        
        try:
            # Realizar petición a la API
            async with self.session.get(
                self.api_url,
                headers=self.marketcsgo_headers,
                timeout=aiohttp.ClientTimeout(total=self.custom_config['timeout_seconds'])
            ) as response:
                if response.status != 200:
                    self.logger.error(f"Error HTTP {response.status} al obtener datos de MarketCSGO")
                    return []
                
                # Leer respuesta como JSON
                data = await response.json()
                
                # Parsear respuesta
                items = await self._parse_api_response(data)
                
                if items:
                    # Obtener estadísticas
                    total_items = len(items)
                    avg_price = sum(item['price'] for item in items) / total_items
                    min_price = min(item['price'] for item in items)
                    max_price = max(item['price'] for item in items)
                    
                    self.logger.info(
                        f"MarketCSGO scraping completado: {total_items} items "
                        f"(precio promedio: ${avg_price:.2f}, rango: ${min_price:.2f}-${max_price:.2f})"
                    )
                else:
                    self.logger.warning("No se obtuvieron items válidos de MarketCSGO")
                
                return items
                
        except asyncio.TimeoutError:
            self.logger.error("Timeout al obtener datos de MarketCSGO API")
            return []
        except Exception as e:
            self.logger.error(f"Error en fetch_data de MarketCSGO: {e}")
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
            async with self.session.get(
                self.api_url,
                headers=self.marketcsgo_headers,
                timeout=aiohttp.ClientTimeout(total=self.custom_config['timeout_seconds'])
            ) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                if not data.get("success", False):
                    return None
                
                items = data.get("items", [])
                for item in items:
                    if item.get("market_hash_name") == item_name:
                        price = item.get("price")
                        if price is not None:
                            return float(price)
                
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
    async with AsyncMarketCSGOScraper(use_proxy=False) as scraper:
        items = await scraper.run()
        
        print(f"Obtenidos {len(items)} items de MarketCSGO")
        
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