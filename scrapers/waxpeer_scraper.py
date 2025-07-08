"""
Waxpeer Scraper - BOT-vCSGO-Beta V2

Scraper simplificado para Waxpeer.com API
- Usa BaseScraper V2 simplificado
- API-based, rápido y confiable
- Convierte precios de centavos a decimales
- Enfoque personal y simplificado
"""
WAXPEER_URL = "https://waxpeer.com/es?sort=ASC&order=price&all=0&search="
from typing import List, Dict, Optional
import sys
from pathlib import Path

# Agregar el directorio core al path
sys.path.append(str(Path(__file__).parent.parent))

from core.base_scraper import BaseScraper


class PriceFormatter:
    """Utilidades para formatear precios"""
    
    @staticmethod
    def from_cents(cents) -> float:
        """Convierte centavos a valor decimal"""
        try:
            return float(cents) / 1000.0
        except (ValueError, TypeError):
            return 0.0


class WaxpeerScraper(BaseScraper):
    """
    Scraper para Waxpeer.com - Versión V2 Simplificada
    
    Características:
    - API-based para máximo rendimiento
    - Manejo automático de proxies
    - Conversión automática de precios
    - Rate limiting incorporado
    """
    
    def __init__(self, use_proxy: bool = False, proxy_list: Optional[List[str]] = None):
        """
        Inicializa el scraper de Waxpeer
        
        Args:
            use_proxy: Si usar proxy o no
            proxy_list: Lista de proxies a usar
        """
        # Configuración específica para Waxpeer
        config = {
            'timeout': 30,
            'max_retries': 5,
            'retry_delay': 2,
            'interval': 60,
            'headers': {
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate'
            }
        }
        
        super().__init__('waxpeer', use_proxy, proxy_list, config)
        
        # URL de la API de Waxpeer
        self.api_url = 'https://api.waxpeer.com/v1/prices?game=csgo&minified=0&single=0'
        
        self.logger.info("Waxpeer scraper inicializado")
    
    def parse_api_response(self, response_data: Dict) -> List[Dict]:
        """
        Parsea la respuesta de la API de Waxpeer
        
        Args:
            response_data: Datos JSON de respuesta de la API
            
        Returns:
            Lista de items parseados
        """
        try:
            # Verificar que la respuesta sea exitosa
            if not response_data.get('success'):
                self.logger.error(f"Respuesta no exitosa de Waxpeer: {response_data}")
                return []
            
            # Verificar que haya items
            if 'items' not in response_data:
                self.logger.warning("No se encontraron items en la respuesta")
                return []
            
            # Procesar items
            items = []
            for item in response_data['items']:
                try:
                    # Obtener nombre y precio
                    name = item.get('name')
                    price_raw = item.get('min', 0)
                    
                    if not name or not price_raw:
                        continue
                    
                    # Formatear precio usando la utilidad común
                    price = PriceFormatter.from_cents(price_raw)
                    
                    # Crear item con formato estándar
                    formatted_item = {
                        'Item': name,
                        'Price': price,
                        'Platform': 'Waxpeer',
                        'URL': WAXPEER_URL + name.replace(' ', '%20').replace('|', '%7C')
                    }
                    
                    
                    items.append(formatted_item)
                    
                except Exception as e:
                    self.logger.warning(f"Error procesando item individual: {e}")
                    continue
            
            self.logger.info(f"Parseados {len(items)} items de Waxpeer")
            return items
            
        except Exception as e:
            self.logger.error(f"Error parseando respuesta de Waxpeer: {e}")
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
        Obtiene datos de la API de Waxpeer
        
        Returns:
            Lista de items obtenidos
        """
        self.logger.info("Obteniendo datos de Waxpeer API...")
        
        try:
            # Preparar headers con autenticación si está disponible
            headers = self.get_headers_with_auth()
            
            # Hacer petición a la API con headers de autenticación
            response = self.make_request(self.api_url, headers=headers)
            
            if response:
                # Parsear respuesta JSON
                try:
                    response_data = response.json()
                    
                    # Log adicional si usamos API key
                    if self.api_key:
                        self.logger.info("Usando API key de Waxpeer para mejor rate limiting")
                    
                    return self.parse_api_response(response_data)
                except Exception as e:
                    self.logger.error(f"Error parseando JSON de Waxpeer: {e}")
                    return []
            else:
                self.logger.error("No se pudo obtener respuesta de Waxpeer")
                return []
                
        except Exception as e:
            self.logger.error(f"Error en fetch_data de Waxpeer: {e}")
            return []


def main():
    """
    Función principal para ejecutar el scraper
    """
    # Crear y ejecutar scraper (sin proxy por defecto)
    scraper = WaxpeerScraper(use_proxy=False)
    
    try:
        # Ejecutar una vez para prueba
        print("=== Ejecutando Waxpeer Scraper V2 ===")
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