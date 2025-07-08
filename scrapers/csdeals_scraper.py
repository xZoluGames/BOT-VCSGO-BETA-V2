"""
CSDeals Scraper - BOT-vCSGO-Beta V2

Scraper simplificado para CS.deals API
- Usa BaseScraper V2 simplificado
- API-based con validación de success
- Estructura de respuesta: data.response.items
- Enfoque personal y simplificado
"""

from typing import List, Dict, Optional
import sys
from pathlib import Path

# Agregar el directorio core al path
sys.path.append(str(Path(__file__).parent.parent))

from core.base_scraper import BaseScraper


class CSDealsScraper(BaseScraper):
    """
    Scraper para CS.deals - Versión V2 Simplificada
    
    Características:
    - API-based para máximo rendimiento
    - Validación de respuesta success
    - Estructura de datos: data.response.items
    - Rate limiting incorporado
    """
    
    def __init__(self, use_proxy: bool = False, proxy_list: Optional[List[str]] = None):
        """
        Inicializa el scraper de CSDeals
        
        Args:
            use_proxy: Si usar proxy o no
            proxy_list: Lista de proxies a usar
        """
        # Configuración específica para CSDeals
        config = {
            'timeout': 30,
            'max_retries': 5,
            'retry_delay': 2,
            'interval': 60,
            'headers': {
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate',
                'Referer': 'https://cs.deals/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }
        
        super().__init__('csdeals', use_proxy, proxy_list, config)
        
        # URL de la API de CSDeals
        self.api_url = 'https://cs.deals/API/IPricing/GetLowestPrices/v1?appid=730'
        
        self.logger.info("CSDeals scraper inicializado")
    
    def parse_api_response(self, response_data: Dict) -> List[Dict]:
        """
        Parsea la respuesta de la API de CSDeals
        
        Args:
            response_data: Datos JSON de respuesta de la API
            
        Returns:
            Lista de items parseados
        """
        try:
            # Verificar estructura de respuesta de CSDeals
            if not response_data.get('success'):
                self.logger.error(f"Respuesta no exitosa de CSDeals: {response_data}")
                return []
            
            # CSDeals tiene la estructura: data -> response -> items
            if 'response' not in response_data or 'items' not in response_data['response']:
                self.logger.warning("Estructura inesperada en respuesta de CSDeals")
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
                    
                    # Crear item con formato estándar
                    formatted_item = {
                        'Item': name,
                        'Price': float(price),  # CSDeals ya devuelve el precio en formato decimal
                        'Platform': 'CSDeals'
                    }
                    
                    # Información adicional si está disponible
                    if item.get('quantity'):
                        formatted_item['Quantity'] = item['quantity']
                    
                    if item.get('condition'):
                        formatted_item['Condition'] = item['condition']
                    
                    # URL del item
                    if name:
                        formatted_item['URL'] = f"https://cs.deals/new?name={name.replace(' ', '%20')}&game=csgo&sort=price&sort_desc=0"
                    
                    items.append(formatted_item)
                    
                except Exception as e:
                    self.logger.warning(f"Error procesando item individual: {e}")
                    continue
            
            self.logger.info(f"Parseados {len(items)} items de CSDeals")
            return items
            
        except Exception as e:
            self.logger.error(f"Error parseando respuesta de CSDeals: {e}")
            return []
    
    def parse_response(self, response) -> List[Dict]:
        """
        Método requerido por BaseScraper para parsear respuesta HTTP
        
        Args:
            response: Objeto Response de requests
            
        Returns:
            Lista de items parseados
        """
        try:
            return self.parse_api_response(response.json())
        except Exception as e:
            self.logger.error(f"Error en parse_response: {e}")
            return []
    
    def fetch_data(self) -> List[Dict]:
        """
        Obtiene datos de la API de CSDeals
        
        Returns:
            Lista de items obtenidos
        """
        self.logger.info("Obteniendo datos de CSDeals API...")
        
        try:
            # Hacer petición a la API
            response = self.make_request(self.api_url)
            
            if response:
                try:
                    response_data = response.json()
                    return self.parse_api_response(response_data)
                except Exception as e:
                    self.logger.error(f"Error parseando JSON de CSDeals: {e}")
                    return []
            else:
                self.logger.error("No se pudo obtener respuesta de CSDeals")
                return []
                
        except Exception as e:
            self.logger.error(f"Error en fetch_data de CSDeals: {e}")
            return []


def main():
    """
    Función principal para ejecutar el scraper
    """
    # Crear y ejecutar scraper
    scraper = CSDealsScraper(use_proxy=False)
    
    try:
        # Ejecutar una vez para prueba
        print("=== Ejecutando CSDeals Scraper V2 ===")
        data = scraper.run_once()
        
        print(f"\n✅ Scraper completado:")
        print(f"   - Items obtenidos: {len(data)}")
        print(f"   - Estadísticas: {scraper.get_stats()}")
        
        if data:
            print(f"\n📋 Primeros 3 items:")
            for item in data[:3]:
                print(f"   - {item['Item']}: ${item['Price']}")
        
        # Opción para ejecutar en bucle
        run_forever = input("\n¿Ejecutar en bucle infinito? (y/N): ").lower() == 'y'
        if run_forever:
            print("Iniciando bucle infinito... (Ctrl+C para detener)")
            scraper.run_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        # Limpiar recursos
        scraper.session.close()


if __name__ == "__main__":
    main()