"""
ShadowPay Scraper - BOT-vCSGO-Beta V2 (Corregido)
Obtiene precios de ShadowPay.com - marketplace con API Bearer
"""

import time
import requests
from typing import Dict, List, Optional
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.base_scraper import BaseScraper

SHADOWPAY_URL = "https://shadowpay.com/csgo-items?search="
SHADOWPAY_URL2 = "&sort_column=price&sort_dir=asc"
class ShadowPayScraper(BaseScraper):
    """
    Scraper para ShadowPay.com
    Marketplace con API simple que requiere Bearer token
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        super().__init__(
            platform_name="shadowpay",
            use_proxy=use_proxy
        )
        
        # Configuración específica de ShadowPay
        self.api_url = "https://api.shadowpay.com/api/v2/user/items/prices"
        
        # Headers básicos - solo los necesarios
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        self.logger.info(f"ShadowPay scraper inicializado (API key: {'Sí' if self.api_key else 'No'})")
    
    def parse_response(self, response: requests.Response) -> List[Dict]:
        """
        Parsea la respuesta de ShadowPay API
        
        Args:
            response: Respuesta HTTP de la API
            
        Returns:
            Lista de items parseados
        """
        try:
            data = response.json()
            
            # Verificar que existe el campo data
            raw_items = data.get("data", [])
            if not raw_items:
                self.logger.warning("No se encontraron items en la respuesta de ShadowPay")
                return []
            
            items = []
            for item in raw_items:
                try:
                    # Extraer solo los datos básicos que sabemos que existen
                    item_name = item.get("steam_market_hash_name")
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
                            'Platform': 'ShadowPay',
                            'URL': SHADOWPAY_URL + item_name.replace(' ', '%20').replace('|', '%7C') + SHADOWPAY_URL2
                        }
                        
                        items.append(parsed_item)
                        
                except (ValueError, TypeError, KeyError) as e:
                    self.logger.warning(f"Error procesando item de ShadowPay: {item} - {e}")
                    continue
            
            self.logger.info(f"Procesados {len(items)} items válidos de ShadowPay")
            return items
            
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error parseando respuesta de ShadowPay: {e}")
            return []
    
    def fetch_data(self) -> List[Dict]:
        """
        Obtiene datos de ShadowPay API
        
        Returns:
            Lista de items con precios
        """
        if not self.api_key:
            self.logger.error("API key requerida para ShadowPay. Configure la API key en config/api_keys.json")
            return []
        
        self.logger.info("Iniciando scraping de ShadowPay...")
        
        try:
            # Realizar petición a la API usando requests directamente
            response = requests.get(self.api_url, headers=self.headers)
            
            # Verificar código de estado
            if response.status_code != 200:
                self.logger.error(f"Error HTTP {response.status_code} de ShadowPay API")
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
                    f"ShadowPay scraping completado: {total_items} items "
                    f"(precio promedio: ${avg_price:.2f}, rango: ${min_price:.2f}-${max_price:.2f})"
                )
            else:
                self.logger.warning("No se obtuvieron items válidos de ShadowPay")
            
            return items
            
        except Exception as e:
            self.logger.error(f"Error en fetch_data de ShadowPay: {e}")
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
            items = self.fetch_data()
            
            for item in items:
                if item['Item'] == item_name:
                    return item['Price']
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error obteniendo precio para {item_name}: {e}")
            return None


def main():
    """Función principal para testing"""
    scraper = ShadowPayScraper(use_proxy=False)
    
    try:
        data = scraper.run_once()
        print(f"Obtenidos {len(data)} items de ShadowPay")
        
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