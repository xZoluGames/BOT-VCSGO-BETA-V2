"""
Async BitSkins Scraper - BOT-VCSGO-BETA-V2

Versión asíncrona del scraper de BitSkins.com con mejoras de rendimiento:
- API REST con autenticación opcional
- Conversión automática de precios (milésimas a USD)
- Rate limiting inteligente
- Validación robusta de respuesta
- Manejo robusto de errores
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import orjson
import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from core.async_base_scraper import AsyncBaseScraper
from core.exceptions import APIError, ParseError, ValidationError


class AsyncBitskinsScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para BitSkins.com
    
    Características:
    - API REST con respuesta en formato {'list': [...]}
    - Conversión automática de precios (milésimas a USD)
    - Rate limiting automático
    - Filtrado de items válidos
    - Soporte para API key opcional
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        """
        Inicializa el scraper de BitSkins
        
        Args:
            use_proxy: Si usar proxy (None = usar configuración)
        """
        # Configuración específica de BitSkins
        custom_config = {
            'rate_limit': 100,  # BitSkins es moderadamente permisivo
            'burst_size': 15,
            'cache_ttl': 240,  # 4 minutos
            'timeout_seconds': 30,
            'max_retries': 3
        }
        
        super().__init__(
            platform_name='bitskins',
            use_proxy=use_proxy,
            custom_config=custom_config
        )
        
        # URL de la API de BitSkins
        self.api_url = 'https://api.bitskins.com/market/insell/730'
        
        # URL base para construir enlaces de items
        self.base_item_url = 'https://bitskins.com/es/market/cs2?search={%22order%22:[{%22field%22:%22price%22,%22order%22:%22ASC%22}],%22where%22:{%22skin_name%22:%22'
        self.base_item_url_suffix = '%22}}'
        
        # Headers específicos para BitSkins
        self.bitskins_headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://bitskins.com/',
            'Origin': 'https://bitskins.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Agregar API key si está disponible
        if self.api_key:
            self.bitskins_headers['Authorization'] = f'Bearer {self.api_key}'
        
        self.logger.info(
            f"AsyncBitskinsScraper inicializado - "
            f"API Key: {'Sí' if self.api_key else 'No'}"
        )
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Ejecuta el scraping de BitSkins
        
        Returns:
            Lista de items con sus precios
        """
        try:
            self.logger.info("Iniciando scraping de BitSkins")
            
            # BitSkins es simple: una sola petición API
            data = await self._fetch_bitskins_data()
            
            if not data:
                self.logger.warning("No se obtuvieron datos de BitSkins")
                return []
            
            # Verificar estructura esperada
            if not isinstance(data, dict) or 'list' not in data:
                self.logger.error("Estructura de respuesta inválida de BitSkins")
                return []
            
            items_list = data['list']
            if not isinstance(items_list, list):
                self.logger.error(f"Campo 'list' no es una lista: {type(items_list)}")
                return []
            
            # Procesar y formatear items
            formatted_items = self._format_items(items_list)
            
            self.logger.info(
                f"BitSkins scraping completado - "
                f"Items raw: {len(items_list)}, "
                f"Items válidos: {len(formatted_items)}"
            )
            
            return formatted_items
            
        except Exception as e:
            self.logger.error(f"Error en scraping: {e}")
            raise
    
    async def _fetch_bitskins_data(self) -> Optional[Dict]:
        """
        Obtiene datos de la API de BitSkins
        
        Returns:
            Datos de la API o None si falla
        """
        if not self.session:
            await self.setup()
            
        try:
            self.logger.debug("Realizando petición a BitSkins API")
            
            async with self.session.get(
                self.api_url,
                headers=self.bitskins_headers
            ) as response:
                if response.status != 200:
                    self.logger.error(f"HTTP {response.status} en BitSkins API")
                    raise APIError(self.platform_name, response_text=f"HTTP {response.status}")
                
                # Leer respuesta completa
                content = await response.read()
                
                if not content:
                    self.logger.error("Respuesta vacía de BitSkins")
                    return None
                
                # Decodificar y parsear JSON
                text = content.decode('utf-8')
                data = orjson.loads(text)
                
                self.logger.debug(f"Respuesta de BitSkins obtenida exitosamente")
                return data
                
        except Exception as e:
            self.logger.error(f"Error fetching BitSkins data: {e}")
            return None
    
    def _format_items(self, items_data: List[Dict]) -> List[Dict]:
        """
        Formatea items al formato estándar del sistema asíncrono
        
        Args:
            items_data: Lista de items raw de la API
            
        Returns:
            Lista de items en formato estándar
        """
        formatted_items = []
        items_processed = 0
        
        for item in items_data:
            items_processed += 1
            
            try:
                # Validar que sea un diccionario
                if not isinstance(item, dict):
                    continue
                
                # Obtener datos básicos
                name = item.get('name')
                price_min = item.get('price_min', 0)
                quantity = item.get('quantity', 0)
                
                # Validaciones básicas
                if not name or not isinstance(name, str):
                    continue
                    
                if not isinstance(price_min, (int, float)) or price_min <= 0:
                    continue
                
                # Convertir precio de milésimas a dólares
                # BitSkins devuelve precios en milésimas ($1.00 = 1000)
                price_dollars = float(price_min) / 1000.0
                
                # Filtrar precios muy bajos o muy altos
                if price_dollars < 0.01 or price_dollars > 50000:
                    continue
                
                # Crear URL del item
                item_url = self.base_item_url + name.replace(' ', '%20') + self.base_item_url_suffix
                
                # Crear item formateado
                formatted_item = {
                    'name': name.strip(),
                    'price': round(price_dollars, 2),
                    'platform': 'bitskins',
                    'quantity': max(0, quantity),  # Asegurar que quantity >= 0
                    'bitskins_url': item_url,
                    'original_price_millis': price_min,  # Conservar precio original
                    'last_update': datetime.now().isoformat()
                }
                
                formatted_items.append(formatted_item)
                
            except Exception as e:
                self.logger.warning(f"Error procesando item de BitSkins: {e}")
                continue
        
        # Ordenar por precio ascendente
        formatted_items.sort(key=lambda x: x['price'])
        
        self.logger.debug(
            f"BitSkins formatting completado - "
            f"Procesados: {items_processed}, "
            f"Válidos: {len(formatted_items)}"
        )
        
        return formatted_items
    
    async def validate_item(self, item: Dict[str, Any]) -> bool:
        """
        Validación específica para items de BitSkins
        
        Args:
            item: Item a validar
            
        Returns:
            True si es válido
        """
        # Validación base
        if not await super().validate_item(item):
            return False
        
        try:
            # Validaciones específicas de BitSkins
            price = float(item['price'])
            if price < 0.01 or price > 50000:
                return False
            
            # Verificar que el nombre sea razonable
            name = item['name']
            if len(name.strip()) < 3 or len(name) > 200:
                return False
            
            quantity = item.get('quantity', 0)
            if quantity < 0:  # Permitir 0 pero no negativos
                return False
            
            return True
            
        except (ValueError, TypeError, KeyError):
            return False


async def compare_performance():
    """
    Función para comparar rendimiento con versión síncrona
    """
    import time
    
    print("\n=== Comparación de Rendimiento: BitSkins ===\n")
    
    # Test asíncrono
    print("🚀 Ejecutando versión ASÍNCRONA...")
    start_async = time.time()
    
    async with AsyncBitskinsScraper(use_proxy=False) as scraper:
        items_async = await scraper.run()
    
    time_async = time.time() - start_async
    
    print(f"✅ Asíncrono completado:")
    print(f"   - Items: {len(items_async)}")
    print(f"   - Tiempo: {time_async:.2f}s")
    print(f"   - Métricas: {scraper.metrics.to_dict()}")
    
    # Comparar con versión síncrona (si existe)
    try:
        from scrapers.bitskins_scraper import BitskinsScraper
        
        print("\n🐌 Ejecutando versión SÍNCRONA...")
        start_sync = time.time()
        
        sync_scraper = BitskinsScraper(use_proxy=False)
        items_sync = sync_scraper.fetch_data()
        
        time_sync = time.time() - start_sync
        
        print(f"✅ Síncrono completado:")
        print(f"   - Items: {len(items_sync)}")
        print(f"   - Tiempo: {time_sync:.2f}s")
        
        # Calcular mejora
        if time_sync > 0:
            improvement = ((time_sync - time_async) / time_sync) * 100
            speedup = time_sync / time_async
            
            print(f"\n📊 RESULTADOS:")
            print(f"   - Mejora: {improvement:.1f}%")
            print(f"   - Speedup: {speedup:.1f}x más rápido")
            print(f"   - Tiempo ahorrado: {time_sync - time_async:.2f}s")
        
    except ImportError:
        print("\n⚠️  No se pudo importar la versión síncrona para comparar")
    except Exception as e:
        print(f"\n❌ Error en comparación: {e}")


async def main():
    """Función principal para testing"""
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Ejecutar scraper
    async with AsyncBitskinsScraper(use_proxy=False) as scraper:
        items = await scraper.run()
        print(f"\n✅ Scraping completado: {len(items)} items")
        
        # Mostrar algunos items de ejemplo
        if items:
            print("\n📦 Primeros 5 items:")
            for item in items[:5]:
                print(f"  - {item['name']}: ${item['price']:.2f} (Stock: {item['quantity']})")
            
            # Mostrar estadísticas de precios
            prices = [item['price'] for item in items]
            print(f"\n📊 Estadísticas de precios:")
            print(f"  - Precio mínimo: ${min(prices):.2f}")
            print(f"  - Precio máximo: ${max(prices):.2f}")
            print(f"  - Precio promedio: ${sum(prices)/len(prices):.2f}")
    
    # Ejecutar comparación de rendimiento
    await compare_performance()


if __name__ == "__main__":
    asyncio.run(main())