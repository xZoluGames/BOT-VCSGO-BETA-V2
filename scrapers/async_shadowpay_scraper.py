"""
Async ShadowPay Scraper - BOT-VCSGO-BETA-V2

Versión asíncrona del scraper de ShadowPay.com con mejoras de rendimiento:
- API REST con autenticación Bearer token requerida
- Rate limiting inteligente
- Validación robusta de respuesta
- Manejo robusto de errores con reintentos
- Estadísticas de precios automáticas
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


class AsyncShadowpayScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para ShadowPay.com
    
    Características:
    - API REST con autenticación Bearer token requerida
    - Respuesta en formato {'data': [...]}
    - Rate limiting automático
    - Estadísticas de precios automáticas
    - Validación robusta de respuesta
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        """
        Inicializa el scraper de ShadowPay
        
        Args:
            use_proxy: Si usar proxy (None = usar configuración)
        """
        # Configuración específica de ShadowPay
        custom_config = {
            'rate_limit': 80,  # ShadowPay es conservador con rate limiting
            'burst_size': 10,
            'cache_ttl': 300,  # 5 minutos
            'timeout_seconds': 30,
            'max_retries': 3
        }
        
        super().__init__(
            platform_name='shadowpay',
            use_proxy=use_proxy,
            custom_config=custom_config
        )
        
        # URL de la API de ShadowPay
        self.api_url = 'https://api.shadowpay.com/api/v2/user/items/prices'
        
        # URL base para construir enlaces de items
        self.base_item_url = 'https://shadowpay.com/csgo-items?search='
        self.base_item_url_suffix = '&sort_column=price&sort_dir=asc'
        
        # Headers específicos para ShadowPay con Bearer token
        self.shadowpay_headers = {
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Agregar Authorization Bearer si hay API key
        if self.api_key:
            self.shadowpay_headers['Authorization'] = f'Bearer {self.api_key}'
        
        self.logger.info(
            f"AsyncShadowpayScraper inicializado - "
            f"API Key: {'Sí' if self.api_key else 'No'}"
        )
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Ejecuta el scraping de ShadowPay
        
        Returns:
            Lista de items con sus precios
        """
        try:
            if not self.api_key:
                self.logger.error("API key requerida para ShadowPay")
                raise APIError(self.platform_name, response_text="API key requerida")
            
            self.logger.info("Iniciando scraping de ShadowPay")
            
            # ShadowPay es simple: una sola petición API
            data = await self._fetch_shadowpay_data()
            
            if not data:
                self.logger.warning("No se obtuvieron datos de ShadowPay")
                return []
            
            # Verificar estructura esperada
            if not isinstance(data, dict) or 'data' not in data:
                self.logger.error("Estructura de respuesta inválida de ShadowPay")
                return []
            
            items_list = data['data']
            if not isinstance(items_list, list):
                self.logger.error(f"Campo 'data' no es una lista: {type(items_list)}")
                return []
            
            # Procesar y formatear items
            formatted_items = self._format_items(items_list)
            
            # Generar estadísticas de precios
            if formatted_items:
                self._log_price_statistics(formatted_items)
            
            self.logger.info(
                f"ShadowPay scraping completado - "
                f"Items raw: {len(items_list)}, "
                f"Items válidos: {len(formatted_items)}"
            )
            
            return formatted_items
            
        except Exception as e:
            self.logger.error(f"Error en scraping: {e}")
            raise
    
    async def _fetch_shadowpay_data(self) -> Optional[Dict]:
        """
        Obtiene datos de la API de ShadowPay
        
        Returns:
            Datos de la API o None si falla
        """
        if not self.session:
            await self.setup()
            
        try:
            self.logger.debug("Realizando petición a ShadowPay API")
            
            async with self.session.get(
                self.api_url,
                headers=self.shadowpay_headers
            ) as response:
                if response.status == 401:
                    self.logger.error("API key inválida o expirada para ShadowPay")
                    raise APIError(self.platform_name, response_text="API key inválida")
                elif response.status != 200:
                    self.logger.error(f"HTTP {response.status} en ShadowPay API")
                    raise APIError(self.platform_name, response_text=f"HTTP {response.status}")
                
                # Leer respuesta completa
                content = await response.read()
                
                if not content:
                    self.logger.error("Respuesta vacía de ShadowPay")
                    return None
                
                # Decodificar y parsear JSON
                text = content.decode('utf-8')
                data = orjson.loads(text)
                
                self.logger.debug(f"Respuesta de ShadowPay obtenida exitosamente")
                return data
                
        except Exception as e:
            self.logger.error(f"Error fetching ShadowPay data: {e}")
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
                name = item.get('steam_market_hash_name')
                price_value = item.get('price')
                
                # Validaciones básicas
                if not name or not isinstance(name, str):
                    continue
                    
                if price_value is None or not isinstance(price_value, (int, float)):
                    continue
                
                price = float(price_value)
                
                # Filtrar precios no válidos
                if price <= 0 or price > 50000:
                    continue
                
                # Crear URL del item
                item_url = (self.base_item_url + 
                           name.replace(' ', '%20').replace('|', '%7C') + 
                           self.base_item_url_suffix)
                
                # Crear item formateado
                formatted_item = {
                    'name': name.strip(),
                    'price': round(price, 2),
                    'platform': 'shadowpay',
                    'shadowpay_url': item_url,
                    'last_update': datetime.now().isoformat()
                }
                
                formatted_items.append(formatted_item)
                
            except Exception as e:
                self.logger.warning(f"Error procesando item de ShadowPay: {e}")
                continue
        
        # Ordenar por precio ascendente
        formatted_items.sort(key=lambda x: x['price'])
        
        self.logger.debug(
            f"ShadowPay formatting completado - "
            f"Procesados: {items_processed}, "
            f"Válidos: {len(formatted_items)}"
        )
        
        return formatted_items
    
    def _log_price_statistics(self, items: List[Dict]) -> None:
        """
        Genera y registra estadísticas de precios
        
        Args:
            items: Lista de items formateados
        """
        try:
            if not items:
                return
            
            prices = [item['price'] for item in items]
            total_items = len(items)
            avg_price = sum(prices) / total_items
            min_price = min(prices)
            max_price = max(prices)
            
            self.logger.info(
                f"ShadowPay estadísticas - "
                f"Items: {total_items}, "
                f"Precio promedio: ${avg_price:.2f}, "
                f"Rango: ${min_price:.2f}-${max_price:.2f}"
            )
            
        except Exception as e:
            self.logger.warning(f"Error calculando estadísticas de precios: {e}")
    
    async def validate_item(self, item: Dict[str, Any]) -> bool:
        """
        Validación específica para items de ShadowPay
        
        Args:
            item: Item a validar
            
        Returns:
            True si es válido
        """
        # Validación base
        if not await super().validate_item(item):
            return False
        
        try:
            # Validaciones específicas de ShadowPay
            price = float(item['price'])
            if price <= 0 or price > 50000:
                return False
            
            # Verificar que el nombre sea razonable
            name = item['name']
            if len(name.strip()) < 3 or len(name) > 200:
                return False
            
            return True
            
        except (ValueError, TypeError, KeyError):
            return False
    
    async def get_item_price(self, item_name: str) -> Optional[float]:
        """
        Obtiene el precio de un item específico
        
        Args:
            item_name: Nombre del item
            
        Returns:
            Precio del item o None si no se encuentra
        """
        try:
            items = await self.run()
            
            for item in items:
                if item['name'] == item_name:
                    return item['price']
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error obteniendo precio para {item_name}: {e}")
            return None


async def compare_performance():
    """
    Función para comparar rendimiento con versión síncrona
    """
    import time
    
    print("\n=== Comparación de Rendimiento: ShadowPay ===\n")
    
    # Test asíncrono
    print("🚀 Ejecutando versión ASÍNCRONA...")
    start_async = time.time()
    
    async with AsyncShadowpayScraper(use_proxy=False) as scraper:
        items_async = await scraper.run()
    
    time_async = time.time() - start_async
    
    print(f"✅ Asíncrono completado:")
    print(f"   - Items: {len(items_async)}")
    print(f"   - Tiempo: {time_async:.2f}s")
    print(f"   - Métricas: {scraper.metrics.to_dict()}")
    
    # Comparar con versión síncrona (si existe)
    try:
        from scrapers.shadowpay_scraper import ShadowPayScraper
        
        print("\n🐌 Ejecutando versión SÍNCRONA...")
        start_sync = time.time()
        
        sync_scraper = ShadowPayScraper(use_proxy=False)
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
    async with AsyncShadowpayScraper(use_proxy=False) as scraper:
        items = await scraper.run()
        print(f"\n✅ Scraping completado: {len(items)} items")
        
        # Mostrar algunos items de ejemplo
        if items:
            print("\n📦 Primeros 5 items:")
            for item in items[:5]:
                print(f"  - {item['name']}: ${item['price']:.2f}")
            
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