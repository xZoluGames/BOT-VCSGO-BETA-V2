"""
Async Waxpeer Scraper - BOT-VCSGO-BETA-V2

Versión asíncrona del scraper de Waxpeer como ejemplo de migración.
Demuestra las mejoras de rendimiento con async/await.
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import orjson
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.async_base_scraper import AsyncBaseScraper
from core.exceptions import APIError, ParseError, ValidationError


class AsyncWaxpeerScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para Waxpeer
    
    Características:
    - Procesamiento paralelo de páginas
    - Rate limiting inteligente
    - Cache con TTL adaptativo
    - Validación robusta de datos
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        """
        Inicializa el scraper de Waxpeer
        
        Args:
            use_proxy: Si usar proxy (None = usar configuración)
        """
        # Configuración específica de Waxpeer
        custom_config = {
            'rate_limit': 120,  # Waxpeer permite más requests
            'burst_size': 20,
            'cache_ttl': 180,  # 3 minutos
            'timeout_seconds': 20,
            'max_retries': 3
        }
        
        super().__init__(
            platform_name='waxpeer',
            use_proxy=use_proxy,
            custom_config=custom_config
        )
        
        # URLs de la API - usando la misma URL que el scraper original
        self.api_url = 'https://api.waxpeer.com/v1/prices?game=csgo&minified=0&single=0'
        
        # Headers específicos para Waxpeer (igual que scraper original)
        self.custom_headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        self.logger.info("AsyncWaxpeerScraper inicializado")
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Ejecuta el scraping de Waxpeer con implementación robusta
        
        Returns:
            Lista de items con sus precios
        """
        try:
            self.logger.info("Iniciando scraping de Waxpeer")
            
            # Usar implementación directa más robusta
            response_data = await self._fetch_waxpeer_data()
            
            # Procesar la respuesta usando la misma lógica que el original
            processed_items = await self._parse_api_response(response_data)
            
            self.logger.info(f"Scraping completado: {len(processed_items)} items procesados")
            
            return processed_items
            
        except Exception as e:
            self.logger.error(f"Error en scraping: {e}")
            raise
    
    async def _fetch_waxpeer_data(self) -> Dict[str, Any]:
        """
        Fetch robusto específico para Waxpeer API
        """
        if not self.session:
            await self.setup()
            
        try:
            async with self.session.get(
                self.api_url,
                headers=self.custom_headers
            ) as response:
                if response.status != 200:
                    raise APIError(
                        self.platform_name,
                        status_code=response.status,
                        response_text=f"HTTP {response.status}",
                        url=self.api_url
                    )
                
                # Leer respuesta completa usando read() en lugar de text()
                content = await response.read()
                text = content.decode('utf-8')
                data = orjson.loads(text)
                
                return data
                
        except Exception as e:
            self.logger.error(f"Error fetching Waxpeer data: {e}")
            raise
    
    async def _parse_api_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parsea la respuesta de la API de Waxpeer (adaptado del scraper original)
        
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
                    # Obtener nombre y precio (usando min como en el original)
                    name = item.get('name')
                    price_raw = item.get('min', 0)
                    
                    if not name or not price_raw:
                        continue
                    
                    # Formatear precio - el original usa /1000, nosotros adaptamos
                    price = float(price_raw) / 1000.0
                    
                    # Crear item con formato estándar (adaptado para async)
                    formatted_item = {
                        'name': name,
                        'price': price,
                        'quantity': item.get('count', 0),
                        'platform': 'waxpeer',
                        'steam_price': item.get('steam_price', 0) / 1000.0 if item.get('steam_price') else None,
                        'image': item.get('img'),
                        'tradable': True,  # Asumir que todos son tradable por defecto
                        'waxpeer_url': f"https://waxpeer.com/es?sort=ASC&order=price&all=0&search={name.replace(' ', '%20').replace('|', '%7C')}",
                        'last_update': datetime.now().isoformat()
                    }
                    
                    # Validar item
                    if await self.validate_item(formatted_item):
                        items.append(formatted_item)
                    
                except Exception as e:
                    self.logger.warning(f"Error procesando item individual: {e}")
                    continue
            
            self.logger.info(f"Parseados {len(items)} items de Waxpeer")
            return items
            
        except Exception as e:
            self.logger.error(f"Error parseando respuesta de Waxpeer: {e}")
            return []

    
    async def validate_item(self, item: Dict[str, Any]) -> bool:
        """
        Validación específica para items de Waxpeer
        
        Args:
            item: Item a validar
            
        Returns:
            True si es válido
        """
        # Validación base
        if not await super().validate_item(item):
            return False
        
        # Validaciones específicas de Waxpeer
        if item.get('quantity', 0) < 0:
            return False
        
        # Validar URL de imagen
        if item.get('image') and not item['image'].startswith(('http://', 'https://')):
            return False
        
        # Validar descuento
        if 'discount' in item:
            discount = item['discount']
            if not isinstance(discount, (int, float)) or discount < -100 or discount > 100:
                return False
        
        return True


async def compare_performance():
    """
    Función para comparar rendimiento con versión síncrona
    """
    import time
    
    print("\n=== Comparación de Rendimiento: Waxpeer ===\n")
    
    # Test asíncrono
    print("🚀 Ejecutando versión ASÍNCRONA...")
    start_async = time.time()
    
    async with AsyncWaxpeerScraper(use_proxy=False) as scraper:
        items_async = await scraper.run()
    
    time_async = time.time() - start_async
    
    print(f"✅ Asíncrono completado:")
    print(f"   - Items: {len(items_async)}")
    print(f"   - Tiempo: {time_async:.2f}s")
    print(f"   - Métricas: {scraper.metrics.to_dict()}")
    
    # Comparar con versión síncrona (si existe)
    try:
        from scrapers.waxpeer_scraper import WaxpeerScraper
        
        print("\n🐌 Ejecutando versión SÍNCRONA...")
        start_sync = time.time()
        
        sync_scraper = WaxpeerScraper(use_proxy=False)
        items_sync = sync_scraper.scrape_market()
        
        time_sync = time.time() - start_sync
        
        print(f"✅ Síncrono completado:")
        print(f"   - Items: {len(items_sync)}")
        print(f"   - Tiempo: {time_sync:.2f}s")
        
        # Calcular mejora
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
    async with AsyncWaxpeerScraper(use_proxy=False) as scraper:
        items = await scraper.run()
        print(f"\n✅ Scraping completado: {len(items)} items")
        
        # Mostrar algunos items de ejemplo
        if items:
            print("\n📦 Primeros 5 items:")
            for item in items[:5]:
                print(f"  - {item['name']}: ${item['price']:.2f}")
    
    # Ejecutar comparación de rendimiento
    await compare_performance()


if __name__ == "__main__":
    asyncio.run(main())