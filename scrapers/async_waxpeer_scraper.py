"""
Async Waxpeer Scraper - BOT-VCSGO-BETA-V2

Versión asíncrona del scraper de Waxpeer como ejemplo de migración.
Demuestra las mejoras de rendimiento con async/await.
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

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
        
        # URLs de la API
        self.base_url = "https://api.waxpeer.com/v1"
        self.prices_endpoint = f"{self.base_url}/prices"
        
        # Configuración de paginación
        self.items_per_page = 100
        self.max_pages = 50  # Límite de seguridad
        
        self.logger.info("AsyncWaxpeerScraper inicializado")
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Ejecuta el scraping de Waxpeer
        
        Returns:
            Lista de items con sus precios
        """
        try:
            # Verificar API key
            if not self.api_key:
                self.logger.warning("No API key configurada para Waxpeer, usando modo público")
            
            # Obtener todos los items en paralelo
            all_items = await self._fetch_all_items()
            
            # Procesar y validar items
            processed_items = await self._process_items(all_items)
            
            self.logger.info(f"Scraping completado: {len(processed_items)} items procesados")
            
            return processed_items
            
        except Exception as e:
            self.logger.error(f"Error en scraping: {e}")
            raise
    
    async def _fetch_all_items(self) -> List[Dict[str, Any]]:
        """Obtiene todos los items disponibles"""
        # Primero, obtener el total de items
        first_page = await self._fetch_page(0)
        
        if not first_page:
            raise APIError(self.platform_name, response_text="No se pudo obtener la primera página")
        
        total_items = first_page.get('count', 0)
        items = first_page.get('items', [])
        
        if total_items == 0:
            return items
        
        # Calcular páginas necesarias
        total_pages = min(
            (total_items + self.items_per_page - 1) // self.items_per_page,
            self.max_pages
        )
        
        self.logger.info(f"Total items: {total_items}, páginas a procesar: {total_pages}")
        
        # Si hay más páginas, obtenerlas en paralelo
        if total_pages > 1:
            # Crear tareas para las páginas restantes
            tasks = []
            for page in range(1, total_pages):
                task = asyncio.create_task(self._fetch_page(page))
                tasks.append(task)
            
            # Ejecutar en paralelo con límite de concurrencia
            # Para evitar saturar la API, procesamos en lotes
            batch_size = 5
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i + batch_size]
                results = await asyncio.gather(*batch, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        self.logger.error(f"Error obteniendo página: {result}")
                        continue
                    
                    if result and 'items' in result:
                        items.extend(result['items'])
                
                # Pequeña pausa entre lotes para ser respetuosos con la API
                if i + batch_size < len(tasks):
                    await asyncio.sleep(0.5)
        
        return items
    
    async def _fetch_page(self, page: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene una página específica de items
        
        Args:
            page: Número de página (0-based)
            
        Returns:
            Datos de la página o None si falla
        """
        try:
            # Parámetros de la petición
            params = {
                'game': 'csgo',
                'offset': page * self.items_per_page,
                'limit': self.items_per_page
            }
            
            # Headers con API key si está disponible
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            # Realizar petición
            data = await self.fetch_json(
                self.prices_endpoint,
                params=params,
                headers=headers
            )
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error obteniendo página {page}: {e}")
            return None
    
    async def _process_items(self, raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Procesa y valida los items obtenidos
        
        Args:
            raw_items: Items crudos de la API
            
        Returns:
            Lista de items procesados y validados
        """
        processed_items = []
        
        # Procesar items en paralelo usando asyncio
        tasks = []
        for item in raw_items:
            task = asyncio.create_task(self._process_single_item(item))
            tasks.append(task)
        
        # Ejecutar todas las tareas
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrar resultados válidos
        for result in results:
            if isinstance(result, Exception):
                self.logger.debug(f"Error procesando item: {result}")
                continue
            
            if result is not None:
                processed_items.append(result)
        
        # Ordenar por precio descendente
        processed_items.sort(key=lambda x: x.get('price', 0), reverse=True)
        
        return processed_items
    
    async def _process_single_item(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Procesa un item individual
        
        Args:
            raw_item: Item crudo de la API
            
        Returns:
            Item procesado o None si no es válido
        """
        try:
            # Extraer datos necesarios
            name = raw_item.get('name', '').strip()
            if not name:
                return None
            
            # Precio en centavos, convertir a dólares
            price_cents = raw_item.get('price')
            if price_cents is None:
                return None
            
            price = price_cents / 100.0
            
            # Validar precio
            if price <= 0:
                return None
            
            # Construir item procesado
            processed_item = {
                'name': name,
                'price': price,
                'quantity': raw_item.get('count', 0),
                'steam_price': raw_item.get('steam_price', 0) / 100.0 if raw_item.get('steam_price') else None,
                'discount': raw_item.get('discount', 0),
                'tradable': raw_item.get('tradable', True),
                'image': raw_item.get('img'),
                'steam_id': raw_item.get('steam_id'),
                'waxpeer_url': f"https://waxpeer.com/csgo/{raw_item.get('name', '').replace(' ', '-')}",
                'last_update': datetime.now().isoformat()
            }
            
            # Información adicional si está disponible
            if 'float' in raw_item:
                processed_item['float_value'] = raw_item['float']
            
            if 'phase' in raw_item:
                processed_item['phase'] = raw_item['phase']
            
            if 'stickers' in raw_item and raw_item['stickers']:
                processed_item['stickers'] = self._process_stickers(raw_item['stickers'])
            
            # Validar item completo
            if await self.validate_item(processed_item):
                return processed_item
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error procesando item: {e}")
            return None
    
    def _process_stickers(self, stickers: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Procesa información de stickers"""
        processed_stickers = []
        
        for sticker in stickers:
            if isinstance(sticker, dict) and 'name' in sticker:
                processed_stickers.append({
                    'name': sticker.get('name', ''),
                    'price': sticker.get('price', 0) / 100.0 if sticker.get('price') else 0,
                    'image': sticker.get('img', '')
                })
        
        return processed_stickers
    
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