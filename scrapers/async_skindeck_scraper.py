"""
SkinDeck Async Scraper - BOT-vCSGO-Beta V2
Obtiene precios de SkinDeck.com - marketplace con API que requiere autenticación
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.async_base_scraper import AsyncBaseScraper


class AsyncSkinDeckScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para SkinDeck.com
    Marketplace con API que requiere Bearer token de autenticación
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        # Configuración específica para SkinDeck
        self.custom_config = {
            'rate_limit': 5,      # Moderado para API autenticada
            'burst_size': 2,      # 2 requests por burst
            'cache_ttl': 300,     # 5 minutos
            'timeout_seconds': 30, # Timeout estándar
            'max_retries': 3,
            'max_concurrent': 3   # Concurrencia moderada
        }
        
        super().__init__(
            platform_name="skindeck",
            use_proxy=use_proxy,
            custom_config=self.custom_config
        )
        
        # URLs y endpoints
        self.api_url = "https://api.skindeck.com/client/market"
        self.base_url = "https://skindeck.com/sell?tab=withdraw"
        self.per_page = 100000  # Máximo items por página
        self.max_pages = 10     # Límite de páginas
        
        # Headers específicos para SkinDeck con autenticación
        self.skindeck_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Referer': 'https://api.skindeck.com/',
            'Authorization': f'Bearer {self.api_key}' if self.api_key else None
        }
        
        # Remover Authorization si no hay API key
        if not self.api_key:
            del self.skindeck_headers['Authorization']
        
        self.logger.info(f"AsyncSkinDeckScraper inicializado (API key: {'Sí' if self.api_key else 'No'})")
        if self.api_key:
            self.logger.info(f"Token (primeros 20 chars): {self.api_key[:20]}...")
    
    async def _get_page_data(self, page: int) -> List[Dict[str, Any]]:
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
            async with self.session.get(
                self.api_url,
                params=params,
                headers=self.skindeck_headers,
                timeout=aiohttp.ClientTimeout(total=self.custom_config['timeout_seconds'])
            ) as response:
                
                self.logger.info(f"Response status: {response.status} para página {page}")
                
                if response.status == 401:
                    self.logger.error("Error 401: Token de autenticación inválido o expirado")
                    return []
                elif response.status == 403:
                    self.logger.error("Error 403: Acceso denegado - verificar permisos del token")
                    return []
                elif response.status != 200:
                    self.logger.error(f"Error HTTP {response.status} al obtener página {page}")
                    return []
                
                # Parsear respuesta JSON
                data = await response.json()
                
                # Verificar que la respuesta sea exitosa
                if not data.get("success", False):
                    self.logger.error(f"API de SkinDeck reportó error para página {page}: {data}")
                    return []
                
                # Obtener items del array
                raw_items = data.get("items", [])
                if not raw_items:
                    self.logger.warning(f"No se encontraron items en página {page}")
                    return []
                
                self.logger.info(f"Recibidos {len(raw_items)} items de página {page}")
                
                # Procesar items
                items = []
                processed_count = 0
                skipped_count = 0
                
                for item in raw_items:
                    processed_count += 1
                    
                    try:
                        if not isinstance(item, dict):
                            skipped_count += 1
                            continue
                        
                        # Verificar que el item tenga offer (estructura crítica)
                        offer = item.get('offer')
                        if not offer:
                            skipped_count += 1
                            continue
                        
                        # Extraer datos del item
                        item_name = item.get("market_hash_name")
                        price_value = offer.get("price")
                        
                        if not item_name or price_value is None:
                            skipped_count += 1
                            continue
                        
                        # Convertir precio a float
                        price = float(price_value)
                        
                        # Solo incluir items con precio válido
                        if price > 0:
                            parsed_item = {
                                'name': item_name,
                                'price': round(price, 2),
                                'platform': 'SkinDeck',
                                'url': self.base_url
                            }
                            items.append(parsed_item)
                        else:
                            skipped_count += 1
                            
                    except (ValueError, TypeError, KeyError) as e:
                        skipped_count += 1
                        continue
                
                self.logger.info(f"Página {page}: {len(raw_items)} raw -> {len(items)} válidos (skipped: {skipped_count})")
                return items
                
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout al obtener página {page}")
            return []
        except Exception as e:
            self.logger.error(f"Error obteniendo página {page}: {e}")
            return []
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Método principal de scraping que implementa la interfaz AsyncBaseScraper
        
        Returns:
            Lista de items scrapeados
        """
        return await self.fetch_data()
    
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Obtiene datos de SkinDeck API con paginación
        
        Returns:
            Lista de items con precios
        """
        self.logger.info("Iniciando scraping asíncrono de SkinDeck...")
        
        # Verificar autenticación
        if not self.api_key:
            self.logger.error("SkinDeck requiere API key para autenticación")
            self.logger.info("Configurar API key en el archivo de configuración")
            return []
        
        all_items = []
        
        try:
            # Obtener datos de múltiples páginas
            for page in range(1, self.max_pages + 1):
                items = await self._get_page_data(page)
                
                if items:
                    all_items.extend(items)
                    self.logger.info(f"Total acumulado: {len(all_items)} items")
                    
                    # Rate limiting entre páginas
                    await asyncio.sleep(0.5)
                else:
                    # Si no hay items en esta página, probablemente no hay más páginas
                    self.logger.info(f"No hay más items en página {page}, finalizando paginación")
                    break
            
            if all_items:
                # Obtener estadísticas
                total_items = len(all_items)
                avg_price = sum(item['price'] for item in all_items) / total_items
                min_price = min(item['price'] for item in all_items)
                max_price = max(item['price'] for item in all_items)
                
                self.logger.info(
                    f"SkinDeck scraping completado: {total_items} items "
                    f"(precio promedio: ${avg_price:.2f}, rango: ${min_price:.2f}-${max_price:.2f})"
                )
            else:
                self.logger.warning("No se obtuvieron items de SkinDeck")
                if not self.api_key:
                    self.logger.info("NOTA: SkinDeck requiere API key válida para acceder a los datos")
            
            return all_items
            
        except Exception as e:
            self.logger.error(f"Error en fetch_data de SkinDeck: {e}")
            return []
    
    async def get_item_price(self, item_name: str) -> Optional[float]:
        """
        Obtiene el precio de un item específico
        
        Args:
            item_name: Nombre del item
            
        Returns:
            Precio del item o None si no se encuentra
        """
        try:
            # Buscar solo en la primera página
            items = await self._get_page_data(1)
            
            if items:
                for item in items:
                    if item['name'] == item_name:
                        return item['price']
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error obteniendo precio para {item_name}: {e}")
            return None


async def main():
    """Función principal para testing"""
    import logging
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Ejecutar scraper
    async with AsyncSkinDeckScraper(use_proxy=False) as scraper:
        items = await scraper.run()
        
        print(f"Obtenidos {len(items)} items de SkinDeck")
        
        # Mostrar algunos ejemplos
        if items:
            print("\nEjemplos de precios obtenidos:")
            for item in items[:5]:
                print(f"- {item['name']}: ${item['price']:.2f}")
        else:
            print("\nNOTA: SkinDeck requiere API key válida para obtener datos")
            print("Configurar en el archivo de configuración del scraper")
        
        # Mostrar estadísticas finales
        try:
            metrics = scraper.get_metrics()
            print(f"\nMétricas finales:")
            print(f"- Requests realizados: {metrics.requests_made}")
            print(f"- Items procesados: {metrics.total_items_scraped}")
            print(f"- Tiempo total: {metrics.total_time:.2f}s")
        except AttributeError:
            print("\nMétricas no disponibles en esta versión")


if __name__ == "__main__":
    asyncio.run(main())