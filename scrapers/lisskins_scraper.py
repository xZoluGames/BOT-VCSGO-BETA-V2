"""
LisSkins Scraper - BOT-vCSGO-Beta V2

Scraper migrado desde BOT-vCSGO-Beta para LisSkins.com
- Migrado desde core/scrapers/lisskins_scraper.py de BOT-vCSGO-Beta
- API-based usando endpoint JSON de LisSkins
- Compatibilidad con API key opcional para mejores rate limits
- Lógica de deduplicación: mantiene el item más barato por nombre
"""

from typing import List, Dict, Optional
import sys
from pathlib import Path

# Agregar el directorio core al path
sys.path.append(str(Path(__file__).parent.parent))

from core.base_scraper import BaseScraper


class LisskinsScraper(BaseScraper):
    """
    Scraper para LisSkins.com - Migrado desde BOT-vCSGO-Beta
    
    Características migradas:
    - API URL: https://lis-skins.com/market_export_json/api_csgo_full.json
    - Lógica de deduplicación: mantiene el más barato por nombre
    - Formateo de URLs para items individuales
    - Estructura de datos: items[] → name/price
    
    Mejoras en V2:
    - Usa BaseScraper V2 con todas las optimizaciones
    - Integración con API keys (opcional)
    - Cache automático
    - Profitability engine integrado
    - Manejo de errores mejorado
    """
    
    def __init__(self, use_proxy: bool = False, proxy_list: Optional[List[str]] = None):
        """
        Inicializa el scraper de LisSkins
        
        Args:
            use_proxy: Si usar proxy o no
            proxy_list: Lista de proxies a usar
        """
        # Configuración específica para LisSkins
        config = {
            'timeout': 30,
            'max_retries': 5,
            'retry_delay': 2,
            'interval': 60,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate',
                'Referer': 'https://lis-skins.com/'
            }
        }
        
        super().__init__('lisskins', use_proxy, proxy_list, config)
        
        # URL de la API de LisSkins (del BOT-vCSGO-Beta original)
        self.api_url = 'https://lis-skins.com/market_export_json/api_csgo_full.json'
        
        self.logger.info("LisSkins scraper inicializado (migrado desde BOT-vCSGO-Beta)")
    
    def _format_url_name(self, item_name: str) -> str:
        """
        Formatea el nombre del item para la URL (lógica del BOT-vCSGO-Beta original)
        
        Args:
            item_name: Nombre del item a formatear
            
        Returns:
            Nombre formateado para URL
        """
        chars_to_remove = "™(),/|"
        
        for char in chars_to_remove:
            item_name = item_name.replace(char, '')
        
        item_name = item_name.replace(' ', '-')
        
        while '--' in item_name:
            item_name = item_name.replace('--', '-')
        
        return item_name.strip('-')
    
    def parse_response(self, response) -> List[Dict]:
        """
        Parsea la respuesta de la API de LisSkins
        
        Usa la lógica exacta del BOT-vCSGO-Beta:
        - Busca data['items']
        - Extrae 'name' y 'price'
        - Deduplicación: mantiene el item más barato por nombre
        - Genera URLs usando _format_url_name
        
        Args:
            response: Objeto Response de requests
            
        Returns:
            Lista de items parseados (deduplicados por precio)
        """
        try:
            data = response.json()
            
            # Diccionario para almacenar el item más barato de cada nombre
            # (lógica del BOT-vCSGO-Beta original)
            cheapest_items = {}
            
            for item in data.get('items', []):
                name = item.get('name')
                price = item.get('price')
                
                if name and price is not None:
                    try:
                        price_float = float(price)
                    except (ValueError, TypeError):
                        self.logger.warning(f"Precio inválido para {name}: {price}")
                        continue
                    
                    if name in cheapest_items:
                        # Si ya existe, mantener el más barato
                        if price_float < cheapest_items[name]['Price']:
                            cheapest_items[name] = {
                                'Item': name,
                                'Price': price_float,
                                'Platform': 'LisSkins',
                                'URL': f"https://lis-skins.com/en/market/csgo/{self._format_url_name(name)}"
                            }
                    else:
                        # Nuevo item
                        cheapest_items[name] = {
                            'Item': name,
                            'Price': price_float,
                            'Platform': 'LisSkins',
                            'URL': f"https://lis-skins.com/en/market/csgo/{self._format_url_name(name)}"
                        }
            
            items = list(cheapest_items.values())
            self.logger.info(f"Parseados {len(items)} items de LisSkins (deduplicados por precio)")
            
            return items
            
        except Exception as e:
            self.logger.error(f"Error parseando respuesta de LisSkins: {e}")
            return []
    
    def fetch_data(self) -> List[Dict]:
        """
        Obtiene datos de la API de LisSkins
        
        Usa la misma URL del BOT-vCSGO-Beta con mejoras V2:
        - Headers con autenticación si está disponible
        - User-Agent para evitar bloqueos
        - Error handling mejorado
        
        Returns:
            Lista de items obtenidos
        """
        self.logger.info("Obteniendo datos de LisSkins API (usando lógica BOT-vCSGO-Beta)...")
        
        try:
            # Preparar headers con autenticación si está disponible (mejora V2)
            headers = self.get_headers_with_auth()
            
            # Hacer petición a la API usando URL del BOT-vCSGO-Beta
            response = self.make_request(self.api_url, headers=headers)
            
            if response:
                # Log adicional si usamos API key
                if self.api_key:
                    self.logger.info("Usando API key de LisSkins para mejor rate limiting")
                
                return self.parse_response(response)
            else:
                self.logger.error("No se pudo obtener respuesta de LisSkins")
                return []
                
        except Exception as e:
            self.logger.error(f"Error en fetch_data de LisSkins: {e}")
            return []


def main():
    """
    Función principal para ejecutar el scraper
    Mantiene compatibilidad con el comportamiento del BOT-vCSGO-Beta
    """
    # Crear y ejecutar scraper (sin proxy por defecto, como BOT-vCSGO-Beta)
    scraper = LisskinsScraper(use_proxy=False)
    
    try:
        # Ejecutar una vez para prueba
        print("=== Ejecutando LisSkins Scraper V2 (migrado desde BOT-vCSGO-Beta) ===")
        data = scraper.run_once()
        
        print(f"\n✅ Scraper completado:")
        print(f"   - Items obtenidos: {len(data)}")
        print(f"   - Estadísticas: {scraper.get_stats()}")
        
        if data:
            print(f"\n📋 Primeros 3 items:")
            for item in data[:3]:
                print(f"   - {item['Item']}: ${item['Price']}")
                
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