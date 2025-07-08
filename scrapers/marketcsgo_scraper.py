"""
MarketCSGO Scraper - BOT-vCSGO-Beta V2
Obtiene precios de Market.CSGO.com - marketplace ruso popular
"""

import time
import requests
from typing import Dict, List, Optional
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.base_scraper import BaseScraper


class MarketCSGOScraper(BaseScraper):
    """
    Scraper para Market.CSGO.com
    Marketplace ruso con API JSON simple
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        super().__init__(
            platform_name="marketcsgo",
            use_proxy=use_proxy
        )
        
        # Configuración específica de MarketCSGO
        self.api_url = "https://market.csgo.com/api/v2/prices/USD.json"
        
        # Headers específicos para MarketCSGO
        self.headers.update({
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'Referer': 'https://market.csgo.com/',
            'Origin': 'https://market.csgo.com'
        })
        
        self.logger.info("MarketCSGO scraper inicializado")
    
    def parse_response(self, response: requests.Response) -> List[Dict]:
        """
        Parsea la respuesta de MarketCSGO API
        
        Args:
            response: Respuesta HTTP de la API
            
        Returns:
            Lista de items parseados
        """
        try:
            data = response.json()
            
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
                            'Item': item_name,
                            'Price': round(price, 2),
                            'URL': f"https://market.csgo.com/es/{item_name.replace(' ', '%20').replace('|', '%7C')}",
                            'Platform': 'Market.CSGO',
                        }
                        items.append(parsed_item)
                        
                except (ValueError, TypeError, KeyError) as e:
                    self.logger.warning(f"Error procesando item de MarketCSGO: {item} - {e}")
                    continue
            
            self.logger.info(f"Procesados {len(items)} items válidos de MarketCSGO")
            return items
            
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error parseando respuesta de MarketCSGO: {e}")
            return []
    
    def fetch_data(self) -> List[Dict]:
        """
        Obtiene datos de MarketCSGO API
        
        Returns:
            Lista de items con precios
        """
        self.logger.info("Iniciando scraping de MarketCSGO...")
        
        try:
            # Realizar petición a la API
            response = self.make_request(self.api_url)
            if not response:
                self.logger.error("No se pudo obtener respuesta de MarketCSGO API")
                return []
            
            # Parsear respuesta
            items = self.parse_response(response)
            
            if items:
                # Obtener estadísticas
                total_items = len(items)
                avg_price = sum(item['Price'] for item in items) / total_items
                min_price = min(item['Price'] for item in items)
                max_price = max(item['Price'] for item in items)
                
                self.logger.info(
                    f"MarketCSGO scraping completado: {total_items} items "
                    f"(precio promedio: ${avg_price:.2f}, rango: ${min_price:.2f}-${max_price:.2f})"
                )
            else:
                self.logger.warning("No se obtuvieron items válidos de MarketCSGO")
            
            return items
            
        except Exception as e:
            self.logger.error(f"Error en fetch_data de MarketCSGO: {e}")
            return []
    
    def get_item_price(self, item_name: str) -> Optional[float]:
        """
        Obtiene el precio de un item específico
        
        Args:
            item_name: Nombre del item
            
        Returns:
            Precio del item o None si no se encuentra
        """
        try:
            response = self.make_request(self.api_url)
            if not response:
                return None
            
            data = response.json()
            
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


def main():
    """Función principal para testing"""
    scraper = MarketCSGOScraper(use_proxy=False)
    
    try:
        data = scraper.run_once()
        print(f"Obtenidos {len(data)} items de MarketCSGO")
        
        # Mostrar algunos ejemplos
        if data:
            print("\nEjemplos de precios obtenidos:")
            for item in data[:5]:
                print(f"- {item['Item']}: ${item['Price']:.2f}")
        
    except KeyboardInterrupt:
        print("\nScraping interrumpido por el usuario")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()