"""
TradeIt Scraper - BOT-vCSGO-Beta V2

Scraper migrado desde BOT-vCSGO-Beta para TradeIt.gg
- Migrado desde core/scrapers/tradeit_scraper.py de BOT-vCSGO-Beta
- API-based usando endpoints oficiales de TradeIt
- Cliente optimizado sin dependencias de Selenium
- Paginación automática para obtener todo el inventario
"""

from typing import List, Dict, Optional
import sys
from pathlib import Path
import time

# Agregar el directorio core al path
sys.path.append(str(Path(__file__).parent.parent))

from core.base_scraper import BaseScraper


class TradeitClient:
    """
    Cliente optimizado para TradeIt.gg (migrado desde BOT-vCSGO-Beta)
    
    Características migradas:
    - API endpoint: https://tradeit.gg/api/v2/inventory/data
    - Paginación con offset/limit
    - Parámetros: gameId=730, sortType=Popularity
    - Conversión de precios: priceForTrade / 100
    - Sistema de reintentos automáticos
    """
    
    BASE_WEBSITE_URI = "https://tradeit.gg/"
    MAX_PAGE_LIMIT = 1000
    WAIT_TIME = 0.5
    MAX_RETRY_COUNT = 5
    
    def __init__(self, session, logger=None):
        """
        Inicializa el cliente TradeIt
        
        Args:
            session: Sesión de requests del BaseScraper
            logger: Logger para registro de eventos
        """
        self.session = session
        self.logger = logger
        
        # Headers específicos para TradeIt (del BOT-vCSGO-Beta original)
        self.session.headers.update({
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Referer': 'https://tradeit.gg/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        })
    
    def get_inventory_data(self, app_id, offset=0, limit=None):
        """
        Obtiene datos del inventario (lógica del BOT-vCSGO-Beta original)
        
        Args:
            app_id: ID del juego (730 para CS:GO)
            offset: Offset para paginación
            limit: Límite de items por página
            
        Returns:
            Lista de items o None si falla
        """
        if limit is None:
            limit = self.MAX_PAGE_LIMIT
            
        url = f"{self.BASE_WEBSITE_URI}api/v2/inventory/data"
        params = {
            'gameId': app_id,
            'sortType': 'Popularity',
            'offset': offset,
            'limit': limit,
            'fresh': 'true'
        }
        
        if self.logger:
            self.logger.info(f"Fetching data from TradeIt API: offset {offset}")
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parsear el contenido JSON
            data = response.json()
            items = data.get('items', [])
            
            if not items:
                return None
            
            inventory_data = []
            
            for item in items:
                try:
                    name = item.get('name', 'Unnamed Item')
                    price_for_trade = item.get('priceForTrade', 0)
                    
                    # Convertir el precio a float (del BOT-vCSGO-Beta original)
                    price_float = float(price_for_trade) / 100
                    
                    inventory_data.append({
                        "Item": name,
                        "Price": price_float,
                        "Platform": "TradeIt",
                        "URL": f"https://tradeit.gg/csgo/trade?search={name.replace(' ', '%20')}"
                    })
                    
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error procesando item individual: {e}")
                    continue
            
            return inventory_data
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error en get_inventory_data: {e}")
            return None


class TradeitScraper(BaseScraper):
    """
    Scraper para TradeIt.gg - Migrado desde BOT-vCSGO-Beta
    
    Características migradas del BOT-vCSGO-Beta:
    - Cliente optimizado sin Selenium
    - API endpoint: tradeit.gg/api/v2/inventory/data
    - Paginación automática con offset/limit
    - Sistema de reintentos con MAX_RETRY_COUNT
    - Conversión de precios: priceForTrade / 100
    - Headers específicos para evitar detección
    
    Mejoras en V2:
    - Usa BaseScraper V2 con todas las optimizaciones
    - Integración con API keys (opcional)
    - Cache automático
    - Profitability engine integrado
    - Logging mejorado
    """
    
    def __init__(self, use_proxy: bool = False, proxy_list: Optional[List[str]] = None):
        """
        Inicializa el scraper de TradeIt
        
        Args:
            use_proxy: Si usar proxy o no
            proxy_list: Lista de proxies a usar
        """
        # Configuración específica para TradeIt
        config = {
            'timeout': 30,
            'max_retries': 5,
            'retry_delay': 1,  # Tiempo del BOT-vCSGO-Beta original
            'interval': 120,   # Más tiempo por ser paginado
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Encoding': 'gzip, deflate, br'
            }
        }
        
        super().__init__('tradeit', use_proxy, proxy_list, config)
        
        # Inicializar cliente TradeIt usando la sesión del BaseScraper
        self.client = TradeitClient(self.session, logger=self.logger)
        
        self.logger.info("TradeIt scraper inicializado (migrado desde BOT-vCSGO-Beta)")
    
    def parse_response(self, response) -> List[Dict]:
        """
        Método requerido por BaseScraper - no usado directamente en TradeIt
        """
        return []
    
    def fetch_data(self) -> List[Dict]:
        """
        Obtiene datos de TradeIt usando paginación automática
        
        Usa la lógica exacta del BOT-vCSGO-Beta:
        - Paginación con offset automático
        - Sistema de reintentos por página
        - CS:GO app_id = "730"
        - Pausa entre requests para no sobrecargar
        
        Returns:
            Lista completa de items del inventario
        """
        self.logger.info("Iniciando obtención de datos de TradeIt (usando lógica BOT-vCSGO-Beta)...")
        
        # Log sobre API key
        if self.api_key:
            self.logger.info("Usando API key de TradeIt para autenticación")
        
        offset = 0
        total_inventory = []
        retry_count = 0
        app_id = "730"  # CS:GO (del BOT-vCSGO-Beta original)
        
        while True:
            inventory_data = self.client.get_inventory_data(app_id, offset=offset)
            
            if not inventory_data:
                retry_count += 1
                self.logger.warning(f"No items found at offset {offset}. Retry count: {retry_count}/{self.client.MAX_RETRY_COUNT}")
                
                if retry_count >= self.client.MAX_RETRY_COUNT:
                    self.logger.info(f"Max retry limit ({self.client.MAX_RETRY_COUNT}) reached. Stopping scraping.")
                    break
                
                self.logger.info(f"Waiting {self.client.WAIT_TIME} seconds before retrying...")
                time.sleep(self.client.WAIT_TIME)
                continue  # Volver a intentar con el mismo offset
            
            # Reiniciar contador de reintentos al encontrar items
            retry_count = 0
            items_fetched = len(inventory_data)
            total_inventory.extend(inventory_data)
            
            self.logger.info(f"Fetched {items_fetched} items at offset {offset}. Total so far: {len(total_inventory)}")
            
            # Incrementar el offset basándose en la cantidad de objetos obtenidos
            offset += items_fetched
            
            self.logger.debug(f"Next request will use offset: {offset}")
            
            # Pequeña pausa entre requests para no sobrecargar la API (del BOT-vCSGO-Beta original)
            time.sleep(0.5)
        
        if total_inventory:
            self.logger.info(f"Scraping completed. Total items collected: {len(total_inventory)}")
        else:
            self.logger.warning("No items were collected during this run.")
        
        return total_inventory


def main():
    """
    Función principal para ejecutar el scraper
    Mantiene compatibilidad con el comportamiento del BOT-vCSGO-Beta
    """
    # Crear y ejecutar scraper (sin proxy por defecto, como BOT-vCSGO-Beta)
    scraper = TradeitScraper(use_proxy=False)
    
    try:
        # Ejecutar una vez para prueba
        print("=== Ejecutando TradeIt Scraper V2 (migrado desde BOT-vCSGO-Beta) ===")
        print("NOTA: Este scraper usa paginación automática - puede tomar varios minutos")
        
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