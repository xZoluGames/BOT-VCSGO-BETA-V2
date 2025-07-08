"""
CSGOEmpire Scraper - BOT-vCSGO-Beta V2

Scraper para CSGOEmpire.com marketplace
Migrado desde OLD BASE y Beta, unificando funcionalidad de proxy/noproxy

Características:
- API REST de CSGOEmpire con autenticación requerida
- Paginación automática para obtener todos los items
- Comparación de precios entre auction=yes y auction=no
- Conversión de monedas a dólares usando tasa calculada
- Soporte completo para proxies y rate limiting
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional
import time

# Agregar el directorio padre al path para imports
sys.path.append(str(Path(__file__).parent.parent))

from core.base_scraper import BaseScraper

class CSGOEmpireScraper(BaseScraper):
    """
    Scraper para CSGOEmpire.com
    
    CSGOEmpire es un marketplace que requiere API key para acceso.
    Los precios vienen en centavos de monedas internas, requieren conversión a USD.
    """
    
    def __init__(self, use_proxy: Optional[bool] = None, config: Optional[Dict] = None):
        """
        Inicializa el scraper de CSGOEmpire
        
        Args:
            use_proxy: Forzar uso de proxy (None = usar configuración)
            config: Configuración personalizada
        """
        super().__init__('empire', use_proxy, config=config)
        
        # URL base de la API de CSGOEmpire
        self.api_base_url = self.config.get(
            'api_url', 
            'https://csgoempire.com/api/v2/trading/items'
        )
        
        # Tasa de conversión de monedas Empire a USD (calculada previamente)
        self.conversion_rate = self.config.get('conversion_rate', 0.6154)
        
        # Verificar API key
        if not self.api_key:
            self.logger.error(
                "API key de CSGOEmpire requerida. "
                "Configúrala en config/api_keys.json o variable de entorno BOT_API_KEY_EMPIRE"
            )
        
        # Headers específicos para CSGOEmpire
        self.empire_headers = {
            "Authorization": f"Bearer {self.api_key}",
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        self.logger.info(
            f"CSGOEmpire scraper inicializado - "
            f"API: {self.api_base_url}, "
            f"API Key: {'Sí' if self.api_key else 'No'}, "
            f"Conversión: {self.conversion_rate} USD por moneda"
        )
    
    def fetch_data(self) -> List[Dict]:
        """
        Obtiene datos de la API de CSGOEmpire
        
        Returns:
            Lista de items con formato estándar
        """
        if not self.api_key:
            self.logger.error("No se puede proceder sin API key de CSGOEmpire")
            return []
        
        self.logger.info("Obteniendo datos de CSGOEmpire...")
        
        try:
            # Obtener items con auction=yes
            self.logger.info("Obteniendo items con auction=yes...")
            items_auction = self._fetch_items_by_auction_type("yes")
            
            # Obtener items con auction=no
            self.logger.info("Obteniendo items con auction=no...")
            items_direct = self._fetch_items_by_auction_type("no")
            
            # Combinar y seleccionar mejores precios
            combined_items = self._combine_item_lists(items_auction, items_direct)
            
            # Formatear a estructura estándar
            formatted_items = self._format_items(combined_items)
            
            self.logger.info(
                f"CSGOEmpire scraping completado - "
                f"Auction: {len(items_auction)}, "
                f"Direct: {len(items_direct)}, "
                f"Final: {len(formatted_items)}"
            )
            
            return formatted_items
            
        except Exception as e:
            self.logger.error(f"Error obteniendo datos de CSGOEmpire: {e}")
            return []
    
    def _fetch_items_by_auction_type(self, auction_type: str) -> Dict[str, Dict]:
        """
        Obtiene items de CSGOEmpire por tipo de subasta
        
        Args:
            auction_type: "yes" para subastas, "no" para compra directa
            
        Returns:
            Diccionario con items {nombre: {data}}
        """
        all_items = {}
        page = 1
        max_pages = self.config.get('max_pages', 100)  # Límite de seguridad
        
        while page <= max_pages:
            self.logger.debug(f"Obteniendo página {page} con auction={auction_type}...")
            
            # Parámetros de la petición
            params = {
                "per_page": 2500,  # Máximo permitido
                "page": page,
                "order": "market_value",
                "sort": "asc",
                "auction": auction_type
            }
            
            # Realizar petición
            response = self.make_request(
                self.api_base_url,
                params=params,
                headers=self.empire_headers
            )
            
            if not response:
                self.logger.warning(f"No se pudo obtener página {page} para auction={auction_type}")
                break
            
            # Parsear respuesta
            try:
                data = response.json()
                items = data.get('data', [])
                
                if not items:
                    self.logger.info(f"No hay más items en página {page} para auction={auction_type}")
                    break
                
                # Procesar items de esta página
                page_processed = 0
                for item in items:
                    processed_item = self._process_empire_item(item)
                    if processed_item:
                        name = processed_item['name']
                        price_usd = processed_item['price_usd']
                        
                        # Guardar si es nuevo o tiene mejor precio
                        if name not in all_items or price_usd < all_items[name]['price_usd']:
                            all_items[name] = processed_item
                            page_processed += 1
                
                self.logger.debug(
                    f"Página {page}: {len(items)} items obtenidos, "
                    f"{page_processed} procesados para auction={auction_type}"
                )
                
                page += 1
                
                # Rate limiting
                time.sleep(self.config.get('page_delay', 1))
                
            except Exception as e:
                self.logger.error(f"Error procesando página {page} para auction={auction_type}: {e}")
                break
        
        self.logger.info(f"Total items únicos obtenidos con auction={auction_type}: {len(all_items)}")
        return all_items
    
    def _process_empire_item(self, item: Dict) -> Optional[Dict]:
        """
        Procesa un item individual de CSGOEmpire
        
        Args:
            item: Item raw de la API
            
        Returns:
            Item procesado o None si es inválido
        """
        try:
            name = item.get("market_name")
            market_value = item.get("market_value", 0)
            item_id = item.get("id")
            
            if not name or not isinstance(name, str):
                return None
            
            if not isinstance(market_value, (int, float)) or market_value <= 0:
                return None
            
            # Convertir centavos de monedas a monedas
            price_in_coins = float(market_value) / 100.0
            
            # Convertir monedas a USD
            price_usd = price_in_coins * self.conversion_rate
            
            # Filtrar precios muy bajos o muy altos
            if price_usd < 0.01 or price_usd > 50000:
                return None
            
            return {
                'name': name.strip(),
                'price_usd': round(price_usd, 3),
                'price_coins': round(price_in_coins, 3),
                'market_value_cents': market_value,
                'item_id': item_id,
                'raw_item': item  # Para debugging
            }
            
        except Exception as e:
            self.logger.warning(f"Error procesando item de Empire: {e}")
            return None
    
    def _combine_item_lists(self, items_auction: Dict, items_direct: Dict) -> Dict:
        """
        Combina listas de items seleccionando mejores precios
        
        Args:
            items_auction: Items de subastas
            items_direct: Items de compra directa
            
        Returns:
            Items combinados con mejores precios
        """
        combined = items_auction.copy()
        
        for name, item_data in items_direct.items():
            if name not in combined or item_data['price_usd'] < combined[name]['price_usd']:
                combined[name] = item_data
        
        self.logger.debug(
            f"Combinación completada - "
            f"Auction: {len(items_auction)}, "
            f"Direct: {len(items_direct)}, "
            f"Combined: {len(combined)}"
        )
        
        return combined
    
    def _format_items(self, items_dict: Dict) -> List[Dict]:
        """
        Formatea items al formato estándar del sistema
        
        Args:
            items_dict: Diccionario de items procesados
            
        Returns:
            Lista de items en formato estándar
        """
        formatted_items = []
        
        for name, item_data in items_dict.items():
            formatted_item = {
                'Item': name,
                'Price': item_data['price_usd'],
                'Platform': 'empire',
                'URL': f"https://csgoempire.com/item/{item_data.get('item_id', '')}",
                'Original_Price_Coins': item_data['price_coins']
            }
            
            formatted_items.append(formatted_item)
        
        return formatted_items
    
    def parse_response(self, response) -> List[Dict]:
        """
        Método abstracto implementado (no usado directamente en Empire)
        
        Args:
            response: Respuesta HTTP
            
        Returns:
            Lista vacía (parsing se hace en fetch_data)
        """
        # En Empire el parsing se hace directamente en fetch_data
        # debido a la complejidad de manejar múltiples tipos de auction
        return []
    
    def validate_item(self, item: Dict) -> bool:
        """
        Validación específica para items de CSGOEmpire
        
        Args:
            item: Item a validar
            
        Returns:
            True si el item es válido
        """
        # Validación base
        if not super().validate_item(item):
            return False
        
        try:
            # Validaciones específicas de Empire
            price = float(item['Price'])
            if price < 0.01 or price > 50000:
                self.logger.warning(f"Precio fuera de rango en Empire: {price}")
                return False
            
            # Verificar que tenga datos de Empire
            if 'Original_Price_Coins' not in item:
                self.logger.warning("Item de Empire sin datos de monedas originales")
                return False
            
            return True
            
        except (ValueError, TypeError, KeyError) as e:
            self.logger.warning(f"Error validando item de Empire: {e}")
            return False
    
    def get_platform_info(self) -> Dict[str, str]:
        """
        Información sobre la plataforma CSGOEmpire
        
        Returns:
            Información de la plataforma
        """
        return {
            'name': 'CSGOEmpire',
            'url': 'https://csgoempire.com',
            'api_url': self.api_base_url,
            'description': 'Marketplace premium con sistema de monedas internas',
            'currency': 'USD (convertido desde monedas Empire)',
            'api_key_required': True,
            'api_key_improves_limits': False,
            'supported_games': ['CS:GO', 'CS2'],
            'notes': f'Conversión automática usando tasa {self.conversion_rate}',
            'auction_types': ['yes (subastas)', 'no (compra directa)']
        }

def main():
    """Función principal para ejecutar el scraper individualmente"""
    scraper = CSGOEmpireScraper()
    
    try:
        print("👑 Iniciando CSGOEmpire Scraper...")
        print(f"📊 Configuración: {scraper.get_platform_info()}")
        print("-" * 50)
        
        # Verificar API key
        if not scraper.api_key:
            print("❌ Error: API key requerida para CSGOEmpire")
            print("💡 Configúrala en config/api_keys.json o variable BOT_API_KEY_EMPIRE")
            return
        
        # Ejecutar una vez para testing
        data = scraper.run_once()
        
        if data:
            print(f"✅ Scraping exitoso: {len(data)} items obtenidos")
            print(f"📈 Estadísticas: {scraper.get_stats()}")
            
            # Mostrar algunos ejemplos
            print("\n🎮 Primeros 3 items:")
            for i, item in enumerate(data[:3]):
                print(f"  {i+1}. {item['Item']} - ${item['Price']} (ID: {item.get('Item_ID', 'N/A')})")
                
            # Estadísticas de precios
            prices = [item['Price'] for item in data]
            if prices:
                print(f"\n💰 Rango de precios: ${min(prices):.2f} - ${max(prices):.2f}")
                print(f"💰 Precio promedio: ${sum(prices)/len(prices):.2f}")
        else:
            print("❌ No se obtuvieron datos")
            
    except KeyboardInterrupt:
        print("\n⏹️  Detenido por el usuario")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("🔚 CSGOEmpire Scraper finalizado")

if __name__ == "__main__":
    main()