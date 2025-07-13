"""
Async Skinport Scraper - BOT-VCSGO-BETA-V2

Versión asíncrona del scraper de Skinport.com con mejoras de rendimiento:
- API-based para máximo rendimiento
- Rate limiting inteligente
- Soporte Brotli compression
- Filtrado de items con cantidad > 0
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


class AsyncSkinportScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para Skinport.com
    
    Características:
    - API simple con response directa
    - Rate limiting automático
    - Filtrado por cantidad > 0
    - Soporte para compression Brotli
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        """
        Inicializa el scraper de Skinport
        
        Args:
            use_proxy: Si usar proxy (None = usar configuración)
        """
        # Configuración específica de Skinport
        custom_config = {
            'rate_limit': 120,  # Skinport es muy permisivo, 120 req/min
            'burst_size': 20,
            'cache_ttl': 180,  # 3 minutos
            'timeout_seconds': 30,
            'max_retries': 3
        }
        
        super().__init__(
            platform_name='skinport',
            use_proxy=use_proxy,
            custom_config=custom_config
        )
        
        # URL de la API de Skinport (USD por defecto)
        self.api_url = 'https://api.skinport.com/v1/items?app_id=730&currency=USD'
        
        # Headers específicos para Skinport con soporte Brotli
        self.skinport_headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'br, gzip, deflate',  # Soporte Brotli
            'Accept-Language': 'en-US,en;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        self.logger.info(f"AsyncSkinportScraper inicializado")
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Ejecuta el scraping de Skinport
        
        Returns:
            Lista de items con sus precios
        """
        try:
            self.logger.info("Iniciando scraping de Skinport")
            
            # Skinport es simple: una sola petición API
            data = await self._fetch_skinport_data()
            
            if not data:
                self.logger.warning("No se obtuvieron datos de Skinport")
                return []
            
            # Procesar y formatear items
            formatted_items = self._format_items(data)
            
            # Filtrar solo items con cantidad > 0
            available_items = [item for item in formatted_items if item.get('quantity', 0) > 0]
            
            self.logger.info(
                f"Skinport scraping completado - "
                f"Total: {len(formatted_items)}, "
                f"Disponibles: {len(available_items)}"
            )
            
            return available_items
            
        except Exception as e:
            self.logger.error(f"Error en scraping: {e}")
            raise
    
    async def _fetch_skinport_data(self) -> Optional[List[Dict]]:
        """
        Obtiene datos de la API de Skinport
        
        Returns:
            Lista de items de la API o None si falla
        """
        if not self.session:
            await self.setup()
            
        try:
            self.logger.debug("Realizando petición a Skinport API")
            
            async with self.session.get(
                self.api_url,
                headers=self.skinport_headers
            ) as response:
                if response.status != 200:
                    self.logger.error(f"HTTP {response.status} en Skinport API")
                    raise APIError(self.platform_name, response_text=f"HTTP {response.status}")
                
                # Log del encoding usado si está disponible
                content_encoding = response.headers.get('content-encoding', 'none')
                self.logger.debug(f"Content-Encoding recibido: {content_encoding}")
                
                # Leer respuesta completa
                content = await response.read()
                
                if not content:
                    self.logger.error("Respuesta vacía de Skinport")
                    return None
                
                # Decodificar y parsear JSON
                text = content.decode('utf-8')
                data = orjson.loads(text)
                
                # Skinport devuelve una lista directamente
                if not isinstance(data, list):
                    self.logger.error(f"Formato inesperado en respuesta de Skinport: {type(data)}")
                    return None
                
                self.logger.debug(f"Obtenidos {len(data)} items raw de Skinport")
                return data
                
        except Exception as e:
            self.logger.error(f"Error fetching Skinport data: {e}")
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
        
        for item in items_data:
            try:
                # Obtener datos básicos
                name = item.get('market_hash_name')
                price = item.get('min_price')
                quantity = item.get('quantity', 0)
                url = item.get('item_page')
                
                # Validaciones básicas
                if not name or not isinstance(name, str):
                    continue
                    
                if price is None or not isinstance(price, (int, float)):
                    continue
                
                price = float(price)
                if price <= 0:
                    continue
                
                # Crear item formateado
                formatted_item = {
                    'name': name.strip(),
                    'price': round(price, 2),
                    'platform': 'skinport',
                    'quantity': max(0, quantity),  # Asegurar que quantity >= 0
                    'skinport_url': url or f"https://skinport.com/item/{name.replace(' ', '-').lower()}",
                    'last_update': datetime.now().isoformat()
                }
                
                formatted_items.append(formatted_item)
                
            except Exception as e:
                self.logger.warning(f"Error procesando item de Skinport: {e}")
                continue
        
        # Ordenar por precio ascendente
        formatted_items.sort(key=lambda x: x['price'])
        
        self.logger.debug(f"Formateados {len(formatted_items)} items de Skinport")
        return formatted_items
    
    async def validate_item(self, item: Dict[str, Any]) -> bool:
        """
        Validación específica para items de Skinport
        
        Args:
            item: Item a validar
            
        Returns:
            True si es válido
        """
        # Validación base
        if not await super().validate_item(item):
            return False
        
        try:
            # Validaciones específicas de Skinport
            price = float(item['price'])
            if price <= 0 or price > 50000:  # Precio razonable
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
    
    print("\n=== Comparación de Rendimiento: Skinport ===\n")
    
    # Test asíncrono
    print("🚀 Ejecutando versión ASÍNCRONA...")
    start_async = time.time()
    
    async with AsyncSkinportScraper(use_proxy=False) as scraper:
        items_async = await scraper.run()
    
    time_async = time.time() - start_async
    
    print(f"✅ Asíncrono completado:")
    print(f"   - Items: {len(items_async)}")
    print(f"   - Tiempo: {time_async:.2f}s")
    print(f"   - Métricas: {scraper.metrics.to_dict()}")
    
    # Comparar con versión síncrona (si existe)
    try:
        from scrapers.skinport_scraper import SkinportScraper
        
        print("\n🐌 Ejecutando versión SÍNCRONA...")
        start_sync = time.time()
        
        sync_scraper = SkinportScraper(use_proxy=False)
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
    async with AsyncSkinportScraper(use_proxy=False) as scraper:
        items = await scraper.run()
        print(f"\n✅ Scraping completado: {len(items)} items")
        
        # Filtrar solo items disponibles (cantidad > 0)
        available_items = [item for item in items if item.get('quantity', 0) > 0]
        print(f"📦 Items disponibles: {len(available_items)}")
        
        # Mostrar algunos items de ejemplo
        if available_items:
            print("\n📦 Primeros 5 items disponibles:")
            for item in available_items[:5]:
                print(f"  - {item['name']}: ${item['price']:.2f} (Stock: {item['quantity']})")
    
    # Ejecutar comparación de rendimiento
    await compare_performance()


if __name__ == "__main__":
    asyncio.run(main())