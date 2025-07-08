"""
Skinport Scraper - BOT-vCSGO-Beta V2

Scraper simplificado para Skinport.com API
- Usa BaseScraper V2 simplificado
- API-based, no requiere proxy
- Filtra items con cantidad > 0
- Enfoque personal y simplificado
- Intervalos dinámicos: 2m sin proxy, 30s con proxy
"""

from typing import List, Dict, Optional
import sys
from pathlib import Path

# Agregar el directorio core al path
sys.path.append(str(Path(__file__).parent.parent))

from core.base_scraper import BaseScraper


class SkinportScraper(BaseScraper):
    """
    Scraper para Skinport.com - Versión V2 Simplificada
    
    Características:
    - API-based para máximo rendimiento
    - Intervalos dinámicos según modo proxy
    - Rate limiting incorporado
    - Soporte Brotli compression
    """
    
    def __init__(self, use_proxy: bool = False, proxy_list: Optional[List[str]] = None):
        """
        Inicializa el scraper de Skinport
        
        Args:
            use_proxy: Si usar proxy o no (Skinport no lo requiere)
            proxy_list: Lista de proxies a usar
        """
        # Configurar intervalo según modo proxy
        interval = 30 if use_proxy else 120  # 30s con proxy, 120s (2m) sin proxy
        
        # Configuración específica para Skinport
        config = {
            'timeout': 30,
            'max_retries': 3,
            'retry_delay': 2,
            'interval': interval,
            'headers': {
                'Accept': 'application/json',
                'Accept-Encoding': 'br, gzip, deflate'  # Agregado soporte Brotli
            }
        }
        
        super().__init__('skinport', use_proxy, proxy_list, config)
        
        # URL de la API de Skinport (USD por defecto)
        self.api_url = 'https://api.skinport.com/v1/items?app_id=730&currency=USD'
        
        # Guardar configuración de proxy para referencia
        self.proxy_mode = use_proxy
        
        self.logger.info(f"Skinport scraper inicializado - Modo proxy: {use_proxy}, Intervalo: {interval}s")
    
    def parse_api_response(self, response_data: List[Dict]) -> List[Dict]:
        """
        Parsea la respuesta de la API de Skinport
        
        Args:
            response_data: Lista de items de la API de Skinport
            
        Returns:
            Lista de items parseados
        """
        try:
            # Skinport devuelve una lista directamente
            if not isinstance(response_data, list):
                self.logger.error(f"Formato inesperado en respuesta de Skinport: {type(response_data)}")
                return []
            
            items = []
            for item in response_data:
                try:
                    # Solo items con cantidad > 0 (disponibles)
                    quantity = item.get('quantity', 0)
                    if quantity <= 0:
                        continue
                    
                    # Obtener datos del item
                    name = item.get('market_hash_name')
                    price = item.get('min_price')
                    url = item.get('item_page')
                    if not name or price is None:
                        continue
                    
                    # Crear item con formato estándar
                    formatted_item = {
                        'Item': name,
                        'Price': float(price),
                        'Platform': 'Skinport',
                        'Quantity': quantity,
                        'URL': url
                    }
                    
                    
                    items.append(formatted_item)
                    
                except Exception as e:
                    self.logger.warning(f"Error procesando item individual: {e}")
                    continue
            
            self.logger.info(f"Parseados {len(items)} items de Skinport")
            return items
            
        except Exception as e:
            self.logger.error(f"Error parseando respuesta de Skinport: {e}")
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
        Obtiene datos de la API de Skinport
        
        Returns:
            Lista de items obtenidos
        """
        mode_text = "con proxy" if self.proxy_mode else "sin proxy"
        self.logger.info(f"Obteniendo datos de Skinport API ({mode_text})...")
        
        try:
            # Hacer petición a la API
            response = self.make_request(self.api_url)
            
            if response:
                # Log del encoding usado si está disponible
                content_encoding = response.headers.get('content-encoding', 'none')
                self.logger.debug(f"Content-Encoding recibido: {content_encoding}")
                
                # Verificar que la respuesta no esté vacía
                if not response.text.strip():
                    self.logger.error("Respuesta vacía de Skinport")
                    return []
                
                try:
                    response_data = response.json()
                    return self.parse_api_response(response_data)
                except Exception as e:
                    self.logger.error(f"Error parseando JSON de Skinport: {e}")
                    return []
            else:
                self.logger.error("No se pudo obtener respuesta de Skinport")
                return []
                
        except Exception as e:
            self.logger.error(f"Error en fetch_data de Skinport: {e}")
            return []
    
    def get_interval_info(self) -> str:
        """
        Retorna información sobre el intervalo configurado
        
        Returns:
            String con información del intervalo
        """
        interval = self.config.get('interval', 60)
        mode = "Proxy" if self.proxy_mode else "Directo"
        return f"{mode} - {interval}s ({interval//60}m {interval%60}s)"


def main():
    """
    Función principal para ejecutar el scraper
    """
    print("=== Skinport Scraper V2 - Configuración ===")
    
    # Preguntar al usuario sobre el modo proxy
    use_proxy_input = input("¿Usar modo proxy? (y/N): ").lower()
    use_proxy = use_proxy_input == 'y'
    
    # Mostrar configuración
    interval = 30 if use_proxy else 120
    mode_text = "Proxy (30s)" if use_proxy else "Directo (2m)"
    print(f"Modo seleccionado: {mode_text}")
    
    # Crear scraper
    scraper = SkinportScraper(use_proxy=use_proxy)
    
    try:
        # Ejecutar una vez para prueba
        print(f"\n=== Ejecutando Skinport Scraper V2 ({scraper.get_interval_info()}) ===")
        data = scraper.run_once()
        
        print(f"\n✅ Scraper completado:")
        print(f"   - Items obtenidos: {len(data)}")
        print(f"   - Configuración: {scraper.get_interval_info()}")
        print(f"   - Estadísticas: {scraper.get_stats()}")
        
        if data:
            print(f"\n📋 Primeros 3 items:")
            for item in data[:3]:
                print(f"   - {item['Item']}: ${item['Price']} (Stock: {item.get('Quantity', 'N/A')})")
        
        # Opción para ejecutar en bucle
        run_forever = input(f"\n¿Ejecutar en bucle infinito cada {interval}s? (y/N): ").lower() == 'y'
        if run_forever:
            print(f"Iniciando bucle infinito (intervalo: {interval}s)... (Ctrl+C para detener)")
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