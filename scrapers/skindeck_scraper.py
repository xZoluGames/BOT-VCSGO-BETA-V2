"""
SkinDeck Scraper - BOT-vCSGO-Beta V2 (Corregido)
Obtiene precios de SkinDeck.com - marketplace con paginación
"""

import time
import requests 
from typing import Dict, List, Optional
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.base_scraper import BaseScraper

SKINDECK_URL = "https://skindeck.com/sell?tab=withdraw"
class SkinDeckScraper(BaseScraper):
    """
    Scraper para SkinDeck.com
    Marketplace con API paginada que requiere autenticación
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        super().__init__(
            platform_name="skindeck",
            use_proxy=use_proxy
        )
        
        # Configuración específica de SkinDeck
        self.api_url = "https://api.skindeck.com/client/market"
        self.per_page = 100000  # Máximo items por página
        self.max_pages = 10    # Límite de páginas para evitar bucles infinitos
        
        # Headers específicos para SkinDeck - simplificados
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Referer': 'https://api.skindeck.com/',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        self.logger.info(f"SkinDeck scraper inicializado (API key: {'Sí' if self.api_key else 'No'})")
        self.logger.info(f"Token (primeros 20 chars): {self.api_key[:20] if self.api_key else 'None'}...")
    
    def parse_response(self, response: requests.Response) -> List[Dict]:
        """
        Parsea la respuesta de SkinDeck API
        
        Args:
            response: Respuesta HTTP de la API
            
        Returns:
            Lista de items parseados
        """
        try:
            # Log detallado de la respuesta
            self.logger.info(f"Response status code: {response.status_code}")
            self.logger.info(f"Response headers: {dict(response.headers)}")
            self.logger.info(f"Response content (first 500 chars): {response.text[:500]}")
            
            data = response.json()
            
            # Log detallado de la estructura de datos
            self.logger.info(f"Response JSON keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            self.logger.info(f"Success field: {data.get('success') if isinstance(data, dict) else 'N/A'}")
            
            # Verificar que la respuesta sea exitosa
            if not data.get("success", False):
                self.logger.error(f"API de SkinDeck reportó error: respuesta no exitosa. Full response: {data}")
                return []
            
            # Obtener items del array
            raw_items = data.get("items", [])
            if not raw_items:
                self.logger.warning("No se encontraron items en la respuesta de SkinDeck")
                return []
            
            self.logger.info(f"Items array length: {len(raw_items)}")
            
            # Log de estructura del primer item
            if len(raw_items) > 0:
                first_item = raw_items[0]
                self.logger.info(f"First item keys: {list(first_item.keys()) if isinstance(first_item, dict) else 'Not a dict'}")
                self.logger.info(f"First item structure: {first_item}")
            
            items = []
            processed_count = 0
            skipped_count = 0
            
            for item in raw_items:
                processed_count += 1
                
                # Log estructura del item cada 100 items procesados
                if processed_count % 100 == 1:
                    self.logger.info(f"Processing item {processed_count}, structure: {item}")
                
                try:
                    if not isinstance(item, dict):
                        skipped_count += 1
                        continue
                    
                    # Verificar que el item tenga offer (estructura crítica)
                    offer = item.get('offer')
                    if not offer:
                        skipped_count += 1
                        if processed_count % 100 == 1:
                            self.logger.info(f"Item {processed_count} has no offer: {item}")
                        continue
                    
                    # Extraer datos del item
                    item_name = item.get("market_hash_name")
                    price_value = offer.get("price")
                    
                    if not item_name:
                        skipped_count += 1
                        if processed_count % 100 == 1:
                            self.logger.info(f"Item {processed_count} has no market_hash_name: {item}")
                        continue
                    
                    if price_value is None:
                        skipped_count += 1
                        if processed_count % 100 == 1:
                            self.logger.info(f"Item {processed_count} offer has no price: {offer}")
                        continue
                    
                    # Convertir precio a float
                    price = float(price_value)
                    
                    # Solo incluir items con precio válido
                    if price > 0:
                        parsed_item = {
                            'Item': item_name,
                            'Price': round(price, 2),
                            'Platform': 'SkinDeck',
                            'URL': SKINDECK_URL
                        }
                        
                        items.append(parsed_item)
                    else:
                        skipped_count += 1
                        
                except (ValueError, TypeError, KeyError) as e:
                    skipped_count += 1
                    if processed_count % 100 == 1:
                        self.logger.warning(f"Error procesando item de SkinDeck: {item} - {e}")
                    continue
            
            self.logger.info(f"Processing summary:")
            self.logger.info(f"  - Raw items received: {len(raw_items)}")
            self.logger.info(f"  - Items processed: {processed_count}")
            self.logger.info(f"  - Items skipped: {skipped_count}")
            self.logger.info(f"  - Valid items parsed: {len(items)}")
            
            return items
            
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error parseando respuesta de SkinDeck: {e}")
            return []
    
    def _get_page_data(self, page: int) -> List[Dict]:
        """
        Obtiene datos de una página específica
        
        Args:
            page: Número de página
            
        Returns:
            Lista de items de la página
        """
        params = {
            'page': page,
            'perPage': self.per_page,
            'sort': 'price_desc'  # Ordenar por precio descendente
        }
        
        try:
            # Log detallado de la request
            self.logger.info(f"Request URL: {self.api_url}")
            self.logger.info(f"Request params: {params}")
            self.logger.info(f"Request headers: {self.headers}")
            
            # Usar requests.get directamente como en la versión que funciona
            response = requests.get(self.api_url, params=params, headers=self.headers, timeout=30)
            
            # Verificar código de estado
            if response.status_code != 200:
                self.logger.error(f"Error HTTP {response.status_code} de SkinDeck API")
                self.logger.error(f"Response text: {response.text}")
                return []
            
            return self.parse_response(response)
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error obteniendo página {page} de SkinDeck: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error obteniendo página {page} de SkinDeck: {e}")
            return []
    
    def fetch_data(self) -> List[Dict]:
        """
        Obtiene datos de SkinDeck API con paginación
        
        Returns:
            Lista de items con precios
        """
        if not self.api_key:
            self.logger.error("API key requerida para SkinDeck. Configure la API key en config/api_keys.json")
            return []
        
        self.logger.info("Iniciando scraping de SkinDeck...")
        self.logger.info(f"Using API key: {self.api_key[:20]}...")
        
        all_items = []
        page = 1
        
        try:
            while page <= self.max_pages:
                self.logger.info(f"Obteniendo página {page} de SkinDeck...")
                
                page_items = self._get_page_data(page)
                
                if not page_items:
                    self.logger.info(f"No se encontraron más items en página {page}, finalizando")
                    break
                
                all_items.extend(page_items)
                self.logger.info(f"Página {page}: {len(page_items)} items obtenidos. Total acumulado: {len(all_items)}")
                
                # Si obtuvimos menos items que el máximo por página, es la última página
                if len(page_items) < self.per_page:
                    self.logger.info("Última página alcanzada")
                    break
                
                page += 1
                
                # Pequeña pausa entre páginas para ser respetuosos
                time.sleep(0.5)
            
            if all_items:
                # Obtener estadísticas
                total_items = len(all_items)
                avg_price = sum(item['Price'] for item in all_items) / total_items
                min_price = min(item['Price'] for item in all_items)
                max_price = max(item['Price'] for item in all_items)
                
                self.logger.info(
                    f"SkinDeck scraping completado: {total_items} items en {page-1} páginas "
                    f"(precio promedio: ${avg_price:.2f}, rango: ${min_price:.2f}-${max_price:.2f})"
                )
                
                # Log de algunos ejemplos
                if len(all_items) > 0:
                    self.logger.info("Sample items:")
                    for i, item in enumerate(all_items[:3]):
                        self.logger.info(f"  Item {i+1}: {item}")
            else:
                self.logger.warning("No se obtuvieron items válidos de SkinDeck")
            
            return all_items
            
        except Exception as e:
            self.logger.error(f"Error en fetch_data de SkinDeck: {e}")
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
            # Buscar solo en la primera página para un item específico
            params = {
                'page': 1,
                'perPage': 100,
                'search': item_name
            }
            
            response = requests.get(self.api_url, params=params, headers=self.headers, timeout=30)
            if response.status_code != 200:
                self.logger.error(f"Error HTTP {response.status_code} buscando item {item_name}")
                return None
            
            items = self.parse_response(response)
            for item in items:
                if item['Item'] == item_name:
                    return item['Price']
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error obteniendo precio para {item_name}: {e}")
            return None


def main():
    """Función principal para testing"""
    scraper = SkinDeckScraper(use_proxy=False)
    
    try:
        data = scraper.run_once()
        print(f"Obtenidos {len(data)} items de SkinDeck")
        
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