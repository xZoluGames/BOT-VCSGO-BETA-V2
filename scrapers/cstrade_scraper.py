"""
CSTrade Scraper - BOT-vCSGO-Beta V2
Obtiene precios de CS.Trade con ajuste automático por tasa de bono
"""

import time
import requests
import sys
from pathlib import Path
from typing import Dict, List, Optional
sys.path.append(str(Path(__file__).parent.parent))
from core.base_scraper import BaseScraper


class CSTradeScraper(BaseScraper):
    """
    Scraper para CS.Trade
    Obtiene precios con ajuste automático por tasa de bono del 50%
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        super().__init__(
            platform_name="cstrade",
            use_proxy=use_proxy
        )
        
        # Configuración específica de CSTrade
        self.api_url = "https://cdn.cs.trade:2096/api/prices_CSGO"
        self.bonus_rate = 50  # 50% tasa de bono por defecto
        
        # Headers específicos para CSTrade
        self.headers.update({
            'Accept': 'application/json',
            'Referer': 'https://cs.trade/',
            'Origin': 'https://cs.trade'
        })
        
        self.logger.info(f"CSTrade scraper inicializado (tasa bono: {self.bonus_rate}%)")
    
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
    
    def parse_response(self, response: requests.Response) -> List[Dict]:
        """
        Parsea la respuesta de CSTrade API
        
        Args:
            response: Respuesta HTTP de la API
            
        Returns:
            Lista de items parseados
        """
        try:
            data = response.json()
            items = []
            
            for item_name, item_data in data.items():
                # Verificar campos requeridos
                if not isinstance(item_data, dict):
                    continue
                
                tradable = item_data.get('tradable', 0)
                stock = item_data.get('have', 0)
                original_price = item_data.get('price')
                
                # Verificar que el item tenga stock disponible
                if (tradable == 0) or original_price is None or stock == 0:
                    continue
                
                try:
                    # Convertir precio a float
                    price_float = float(original_price)
                    
                    # Calcular precio real sin bono
                    real_price = self._calculate_real_price(price_float)
                    
                    # Solo incluir items con precio válido
                    if real_price > 0:
                        item = {
                            'Item': item_name,
                            'Price': round(real_price, 2),
                            'URL': f"https://cs.trade/trade?market_name={item_name.replace(' ', '%20')}",
                            'Platform': 'CSTrade',
                            'Tradable': tradable,
                            'Stock': stock,
                        }
                        items.append(item)
                        
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Precio inválido para {item_name}: {original_price} - {e}")
                    continue
            
            self.logger.info(f"Procesados {len(items)} items válidos de CSTrade")
            return items
            
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error parseando respuesta de CSTrade: {e}")
            return []
    
    def fetch_data(self) -> List[Dict]:
        """
        Obtiene datos de CSTrade API
        
        Returns:
            Lista de items con precios ajustados
        """
        self.logger.info("Iniciando scraping de CSTrade...")
        
        try:
            # Realizar petición a la API
            response = self.make_request(self.api_url)
            if not response:
                self.logger.error("No se pudo obtener respuesta de CSTrade API")
                return []
            
            # Parsear respuesta
            items = self.parse_response(response)
            
            if items:
                # Obtener estadísticas
                total_items = len(items)

                
                self.logger.info(
                    f"CSTrade scraping completado: {total_items} items "
                )
            else:
                self.logger.warning("No se obtuvieron items válidos de CSTrade")
            
            return items
            
        except Exception as e:
            self.logger.error(f"Error en fetch_data de CSTrade: {e}")
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
            item_data = data.get(item_name)
            
            if item_data and 'price' in item_data:
                original_price = float(item_data['price'])
                return self._calculate_real_price(original_price)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error obteniendo precio para {item_name}: {e}")
            return None


def main():
    """Función principal para testing"""
    scraper = CSTradeScraper(use_proxy=False)
    
    try:
        data = scraper.run_once()
        print(f"Obtenidos {len(data)} items de CSTrade")
        
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