"""
ManncoStore Scraper - BOT-vCSGO-Beta V2 (Adaptado a urllib.request)
Obtiene precios de ManncoStore.com - marketplace con paginación por skip
"""

import time
import urllib.request
from urllib.error import HTTPError, URLError
import orjson
import json
from typing import Dict, List, Optional
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.base_scraper import BaseScraper


class ManncoStoreScraper(BaseScraper):
    """
    Scraper para ManncoStore.com
    Marketplace con API paginada usando parámetro skip
    Adaptado para usar urllib.request y estructura simplificada
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        super().__init__(
            platform_name="manncostore",
        )
        
        # Configuración específica de ManncoStore
        self.api_url_template = "https://mannco.store/items/get?price=DESC&page=1&i=0&game=730&skip={}"
        self.store_url = "https://mannco.store/item/"
        self.items_per_page = 50
        
        self.logger.info("ManncoStore scraper inicializado")

    def fetch_data(self) -> List[Dict]:
        """
        Obtiene datos de ManncoStore API con paginación por skip
        
        Returns:
            Lista de items con precios
        """
        self.logger.info("Obteniendo datos de MannCo Store...")
        
        skip = 0
        all_items = []
        
        while True:
            items = self._fetch_page_data(skip)
            
            if items:
                all_items.extend(items)
                skip += self.items_per_page
                self.logger.info(f"Obtenidos {len(items)} items (total: {len(all_items)})")
                time.sleep(0.5)
            else:
                break
        
        self.logger.info(f"Total items obtenidos de MannCo Store: {len(all_items)}")
        return all_items

    def _fetch_page_data(self, skip: int) -> Optional[List[Dict]]:
        """
        Obtiene una página de datos usando el parámetro skip
        
        Args:
            skip: Número de items a saltar
            
        Returns:
            Lista de items formateados o None si no hay más datos
        """
        url = self.api_url_template.format(skip)

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0')
        req.add_header('Accept', 'application/json, text/plain, */*')
        req.add_header('Accept-Language', 'es-ES,es;q=0.9,en;q=0.8')

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read().decode('utf-8')
                data = orjson.loads(raw)

                if isinstance(data, list) and len(data) > 0:
                    formatted_items = []
                    for item in data:
                        formatted_item = {
                            'Item': item.get('name', ''),
                            'Price': self._transform_price(item.get('price', 0)),
                            'URL': self.store_url + (item.get('url', '') if item.get('url') else ""),
                            'Platform': 'ManncoStore'
                        }
                        formatted_items.append(formatted_item)

                    return formatted_items
                else:
                    return None

        except HTTPError as e:
            self.logger.error(f"HTTPError al obtener datos (skip={skip}): {e.code} - {e.reason}")
            return None
        except URLError as e:
            self.logger.error(f"URLError al obtener datos (skip={skip}): {e.reason}")
            return None
        except orjson.JSONDecodeError as e:
            self.logger.error(f"Error JSON en skip={skip}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error general en skip={skip}: {e}")
            return None

    def _transform_price(self, price) -> float:
        """
        Transforma el precio de entero a formato decimal
        
        Args:
            price: Precio en formato entero (ej: 1250 = 12.50)
            
        Returns:
            Precio en formato float
        """
        try:
            price_str = str(price)
            if len(price_str) > 2:
                return float(f"{price_str[:-2]}.{price_str[-2:]}")
            else:
                return float(f"0.{price_str.zfill(2)}")
        except (ValueError, TypeError):
            return 0.0

    def parse_response(self, response) -> List[Dict]:
        """
        Parsea la respuesta (mantenido por compatibilidad con BaseScraper)
        
        Args:
            response: Respuesta a parsear
            
        Returns:
            Lista de items parseados
        """
        try:
            if hasattr(response, 'json'):
                return response.json()
            else:
                return orjson.loads(response)
        except (orjson.JSONDecodeError, AttributeError) as e:
            self.logger.error(f"Error al parsear respuesta JSON: {e}")
            return []

    def save_data(self, data: List[Dict]) -> bool:
        """
        Guarda los datos en el archivo JSON específico
        
        Args:
            data: Lista de items a guardar
            
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        try:
            # Crear directorio data si no existe
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            
            # Ruta del archivo
            file_path = data_dir / "manncostore_data.json"
            
            # Guardar datos
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Datos guardados en: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error guardando datos: {e}")
            return False

    def run_once(self) -> List[Dict]:
        """
        Ejecuta el scraping una vez y guarda los datos
        
        Returns:
            Lista de items obtenidos
        """
        try:
            data = self.fetch_data()
            
            if data:
                self.save_data(data)
                self.logger.info(f"Scraping completado: {len(data)} items obtenidos y guardados")
            else:
                self.logger.warning("No se obtuvieron datos para guardar")
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error en run_once: {e}")
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
            # Buscar solo en los primeros items
            items = self._fetch_page_data(0)
            
            if items:
                for item in items:
                    if item['Item'] == item_name:
                        return item['Price']
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error obteniendo precio para {item_name}: {e}")
            return None


def main():
    """Función principal para testing"""
    scraper = ManncoStoreScraper()
    
    try:
        # Usar run_once() para guardar automáticamente
        data = scraper.run_once()
        print(f"Obtenidos y guardados {len(data)} items de ManncoStore")
        
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