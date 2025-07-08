"""
BitSkins Scraper - BOT-vCSGO-Beta V2

Scraper para BitSkins.com marketplace
Migrado desde OLD BASE y Beta, unificando funcionalidad de proxy/noproxy

Características:
- API REST de BitSkins con autenticación opcional
- Conversión de precios de milésimas a dólares
- Validación de respuesta y manejo de errores
- Soporte para API key (opcional, mejora límites)
- Configuración desde config manager
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional
import unicodedata

# Agregar el directorio padre al path para imports
sys.path.append(str(Path(__file__).parent.parent))

from core.base_scraper import BaseScraper
BITSKINS_URL = 'https://bitskins.com/es/market/cs2?search={%22order%22:[{%22field%22:%22price%22,%22order%22:%22ASC%22}],%22where%22:{%22skin_name%22:%22'
BITSKINS_URL2 = '%22}}'
class BitskinsScraper(BaseScraper):
    """
    Scraper para BitSkins.com
    
    BitSkins es un marketplace popular para CS:GO skins con API pública.
    Precios vienen en milésimas de dólar, necesitan conversión.
    """
    
    def __init__(self, use_proxy: Optional[bool] = None, config: Optional[Dict] = None):
        """
        Inicializa el scraper de BitSkins
        
        Args:
            use_proxy: Forzar uso de proxy (None = usar configuración)
            config: Configuración personalizada
        """
        super().__init__('bitskins', use_proxy, config=config)
        
        # URL de la API de BitSkins
        self.api_url = 'https://api.bitskins.com/market/insell/730'
        
        # Headers específicos para BitSkins
        self.bitskins_headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://bitskins.com/',
            'Origin': 'https://bitskins.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        self.logger.info(
            f"BitSkins scraper inicializado - "
            f"API: {self.api_url}, "
            f"API Key: {'Sí' if self.api_key else 'No'}"
        )
    
    def fetch_data(self) -> List[Dict]:
        """
        Obtiene datos de la API de BitSkins
        
        Returns:
            Lista de items con formato estándar
        """
        self.logger.info("Obteniendo datos de BitSkins...")
        
        try:
            # Realizar petición con headers específicos
            response = self.make_request(
                self.api_url,
                headers=self.bitskins_headers
            )
            
            if response:
                return self.parse_response(response)
            else:
                self.logger.error("No se pudo obtener respuesta de BitSkins")
                return []
                
        except Exception as e:
            self.logger.error(f"Error obteniendo datos de BitSkins: {e}")
            return []
    
    def parse_response(self, response) -> List[Dict]:
        """
        Parsea la respuesta de la API de BitSkins
        
        Args:
            response: Respuesta HTTP
            
        Returns:
            Lista de items parseados
        """
        try:
            # Verificar que la respuesta no esté vacía
            if not response.text or not response.text.strip():
                self.logger.error("Respuesta vacía de BitSkins")
                return []
            
            # Intentar parsear JSON
            try:
                data = response.json()
            except ValueError as e:
                self.logger.error(f"Error parseando JSON de BitSkins: {e}")
                self.logger.debug(f"Respuesta recibida: {response.text[:500]}...")
                return []
            
            # Verificar estructura esperada
            if not isinstance(data, dict):
                self.logger.error(f"Respuesta de BitSkins no es un diccionario: {type(data)}")
                return []
            
            # BitSkins tiene estructura: {'list': [...]}
            if 'list' not in data:
                self.logger.error(
                    f"No se encontró 'list' en respuesta de BitSkins. "
                    f"Claves disponibles: {list(data.keys())}"
                )
                return []
            
            items_list = data['list']
            if not isinstance(items_list, list):
                self.logger.error(f"Campo 'list' no es una lista: {type(items_list)}")
                return []
            
            # Parsear items
            items = []
            items_processed = 0
            items_valid = 0
            
            for item in items_list:
                items_processed += 1
                
                if not isinstance(item, dict):
                    continue
                
                name = item.get('name')
                price_min = item.get('price_min', 0)
                
                # Validar datos básicos
                if not name or not isinstance(name, str):
                    continue
                
                if not isinstance(price_min, (int, float)) or price_min <= 0:
                    continue
                
                # Convertir precio de milésimas a dólares
                # BitSkins devuelve precios en milésimas ($1.00 = 1000)
                try:
                    price_dollars = float(price_min) / 1000.0
                    
                    # Filtrar precios muy bajos o muy altos (probablemente errores)
                    if price_dollars < 0.01 or price_dollars > 50000:
                        continue
                    
                    # Crear item en formato estándar
                    processed_item = {
                        'Item': name.strip(),
                        'Price': round(price_dollars, 2),
                        'Platform': 'bitskins',
                        'URL': BITSKINS_URL+ name.replace(' ', '%20')+ BITSKINS_URL2,
                        'Stock': item.get('quantity', 0)  # Cantidad disponible
                    }
                    
                    items.append(processed_item)
                    items_valid += 1
                    
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Error convirtiendo precio para item '{name}': {e}")
                    continue
            
            # Estadísticas de parsing
            self.logger.info(
                f"BitSkins parsing completado - "
                f"Procesados: {items_processed}, "
                f"Válidos: {items_valid}, "
                f"Descartados: {items_processed - items_valid}"
            )
            
            if items_valid == 0:
                self.logger.warning("No se obtuvieron items válidos de BitSkins")
            
            return items
            
        except Exception as e:
            self.logger.error(f"Error parseando respuesta de BitSkins: {e}")
            self.logger.debug(f"Respuesta que causó error: {response.text[:1000] if hasattr(response, 'text') else 'No text'}")
            return []

    def validate_item(self, item: Dict) -> bool:
        """
        Validación específica para items de BitSkins
        
        Args:
            item: Item a validar
            
        Returns:
            True si el item es válido
        """
        # Validación base
        if not super().validate_item(item):
            return False
        
        # Validaciones específicas de BitSkins
        try:
            # Verificar que el precio esté en rango razonable
            price = float(item['Price'])
            if price < 0.01 or price > 50000:
                self.logger.warning(f"Precio fuera de rango en BitSkins: {price}")
                return False
            
            # Verificar que el nombre no esté vacío y sea razonable
            name = item['Item']
            if len(name.strip()) < 3 or len(name) > 200:
                self.logger.warning(f"Nombre de item inválido en BitSkins: '{name}'")
                return False
            
            # Verificar que tenga caracteres válidos (permitir ™, ♥, y otros símbolos comunes de CS:GO)
            
            return True
            
        except (ValueError, TypeError, KeyError) as e:
            self.logger.warning(f"Error validando item de BitSkins: {e}")
            return False
    
    def get_platform_info(self) -> Dict[str, str]:
        """
        Información sobre la plataforma BitSkins
        
        Returns:
            Información de la plataforma
        """
        return {
            'name': 'BitSkins',
            'url': 'https://bitskins.com',
            'api_url': self.api_url,
            'description': 'Marketplace popular para CS:GO skins',
            'currency': 'USD',
            'api_key_required': False,
            'api_key_improves_limits': True,
            'supported_games': ['CS:GO', 'CS2'],
            'notes': 'Precios en milésimas, conversión automática'
        }

def main():
    """Función principal para ejecutar el scraper individualmente"""
    scraper = BitskinsScraper()
    
    try:
        print("🔥 Iniciando BitSkins Scraper...")
        print(f"📊 Configuración: {scraper.get_platform_info()}")
        print("-" * 50)
        
        # Ejecutar una vez para testing
        data = scraper.run_once()
        
        if data:
            print(f"✅ Scraping exitoso: {len(data)} items obtenidos")
            print(f"📈 Estadísticas: {scraper.get_stats()}")
            
            # Mostrar algunos ejemplos
            print("\n🎮 Primeros 3 items:")
            for i, item in enumerate(data[:3]):
                print(f"  {i+1}. {item['Item']} - ${item['Price']}")
        else:
            print("❌ No se obtuvieron datos")
            
    except KeyboardInterrupt:
        print("\n⏹️  Detenido por el usuario")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("🔚 BitSkins Scraper finalizado")

if __name__ == "__main__":
    main()