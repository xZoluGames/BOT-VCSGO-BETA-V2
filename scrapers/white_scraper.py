"""
White Scraper - BOT-vCSGO-Beta V2

Scraper migrado desde BOT-vCSGO-Beta para White.market
- Migrado desde core/scrapers/white_scraper.py de BOT-vCSGO-Beta
- API-based usando endpoint JSON de White.market
- Simple y directo: una sola petición HTTP
- Formato: market_hash_name + price + market_product_link
"""

from typing import List, Dict, Optional
import sys
from pathlib import Path

# Agregar el directorio core al path
sys.path.append(str(Path(__file__).parent.parent))

from core.base_scraper import BaseScraper


class WhiteScraper(BaseScraper):
    """
    Scraper para White.market - Migrado desde BOT-vCSGO-Beta
    
    Características migradas del BOT-vCSGO-Beta:
    - API URL: https://api.white.market/export/v1/prices/730.json
    - Estructura de datos: lista directa de items
    - Campos: market_hash_name, price, market_product_link
    - Validación de formato de respuesta (debe ser lista)
    - Manejo de respuestas vacías
    
    Mejoras en V2:
    - Usa BaseScraper V2 con todas las optimizaciones
    - Integración con API keys (opcional)
    - Cache automático
    - Profitability engine integrado
    - Manejo de errores mejorado
    """
    
    def __init__(self, use_proxy: bool = False, proxy_list: Optional[List[str]] = None):
        """
        Inicializa el scraper de White.market
        
        Args:
            use_proxy: Si usar proxy o no
            proxy_list: Lista de proxies a usar
        """
        # Configuración específica para White.market
        config = {
            'timeout': 30,  # Timeout del BOT-vCSGO-Beta original
            'max_retries': 5,
            'retry_delay': 2,
            'interval': 60,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate, br'
            }
        }
        
        super().__init__('white', use_proxy, proxy_list, config)
        
        # URL de la API de White.market (del BOT-vCSGO-Beta original)
        self.api_url = 'https://api.white.market/export/v1/prices/730.json'
        
        self.logger.info("White.market scraper inicializado (migrado desde BOT-vCSGO-Beta)")
    
    def parse_response_data(self, response) -> List[Dict]:
        """
        Parsea la respuesta de White.market (lógica del BOT-vCSGO-Beta original)
        
        Args:
            response: Objeto Response de requests
            
        Returns:
            Lista de items parseados
        """
        try:
            # Verificar que la respuesta no esté vacía (del BOT-vCSGO-Beta original)
            if not response.text.strip():
                self.logger.error("Respuesta vacía de White.market")
                return []
            
            datos_originales = response.json()
            
            # Verificar que sea una lista (del BOT-vCSGO-Beta original)
            if not isinstance(datos_originales, list):
                self.logger.error(f"Formato inesperado en respuesta de White: {type(datos_originales)}")
                return []
            
            datos_procesados = []
            for item in datos_originales:
                try:
                    # Validar campos requeridos (del BOT-vCSGO-Beta original)
                    market_hash_name = item.get("market_hash_name")
                    price = item.get("price")
                    market_product_link = item.get("market_product_link")
                    
                    if market_hash_name and price is not None:
                        try:
                            price_float = float(price)
                        except (ValueError, TypeError):
                            self.logger.warning(f"Precio inválido para {market_hash_name}: {price}")
                            continue
                        
                        # Crear item con formato compatible + mejoras V2
                        formatted_item = {
                            "Item": market_hash_name,  # Del BOT-vCSGO-Beta
                            "Price": price_float,      # Del BOT-vCSGO-Beta
                            "Platform": "White",       # Mejora V2
                            "URL": market_product_link # Del BOT-vCSGO-Beta
                        }
                        
                        datos_procesados.append(formatted_item)
                        
                except Exception as e:
                    self.logger.warning(f"Error procesando item individual de White: {e}")
                    continue
            
            self.logger.info(f"Parseados {len(datos_procesados)} items de White.market")
            return datos_procesados
            
        except Exception as e:
            self.logger.error(f"Error parseando respuesta de White.market: {e}")
            return []
    
    def parse_response(self, response) -> List[Dict]:
        """
        Método requerido por BaseScraper para parsear respuesta HTTP
        
        Args:
            response: Objeto Response de requests
            
        Returns:
            Lista de items parseados
        """
        return self.parse_response_data(response)
    
    def fetch_data(self) -> List[Dict]:
        """
        Obtiene datos de White.market
        
        Usa la misma URL del BOT-vCSGO-Beta con mejoras V2:
        - Headers con autenticación si está disponible
        - Manejo de errores mejorado
        - Uso del sistema de reintentos del BaseScraper
        
        Returns:
            Lista de items obtenidos
        """
        self.logger.info("Obteniendo datos de White.market API (usando lógica BOT-vCSGO-Beta)...")
        
        try:
            # Preparar headers con autenticación si está disponible (mejora V2)
            headers = self.get_headers_with_auth()
            
            # Hacer petición a la API usando URL del BOT-vCSGO-Beta
            response = self.make_request(self.api_url, headers=headers)
            
            if response:
                # Log adicional si usamos API key
                if self.api_key:
                    self.logger.info("Usando API key de White.market para autenticación")
                
                return self.parse_response_data(response)
            else:
                self.logger.error("No se pudo obtener respuesta de White.market")
                return []
                
        except Exception as e:
            self.logger.error(f"Error en fetch_data de White.market: {e}")
            return []


def main():
    """
    Función principal para ejecutar el scraper
    Mantiene compatibilidad con el comportamiento del BOT-vCSGO-Beta
    """
    # Crear y ejecutar scraper (sin proxy por defecto, como BOT-vCSGO-Beta)
    scraper = WhiteScraper(use_proxy=False)
    
    try:
        # Ejecutar una vez para prueba
        print("=== Ejecutando White.market Scraper V2 (migrado desde BOT-vCSGO-Beta) ===")
        data = scraper.run_once()
        
        print(f"\n✅ Scraper completado:")
        print(f"   - Items obtenidos: {len(data)}")
        print(f"   - Estadísticas: {scraper.get_stats()}")
        
        if data:
            print(f"\n📋 Primeros 3 items:")
            for item in data[:3]:
                print(f"   - {item['Item']}: ${item['Price']}")
                if item.get('URL'):
                    print(f"     URL: {item['URL']}")
                
            # Mostrar rentabilidad si está disponible
            profitable_items = [item for item in data if item.get('is_profitable', False)]
            if profitable_items:
                print(f"\n💰 Items rentables encontrados: {len(profitable_items)}")
                for item in profitable_items[:3]:
                    print(f"   - {item['Item']}: Comprar ${item['Price']} → Vender ${item.get('sell_price', 'N/A')} (Ganancia: {item.get('profit_margin', 0):.1f}%)")
        
        # Opción para ejecutar en bucle (como BOT-vCSGO-Beta)
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