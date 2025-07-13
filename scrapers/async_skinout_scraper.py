"""
SkinOut Async Scraper - BOT-vCSGO-Beta V2
Obtiene precios de SkinOut.gg - marketplace con API paginada
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.async_base_scraper import AsyncBaseScraper


class AsyncSkinOutScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para SkinOut.gg
    Marketplace con API paginada
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        # Configuración específica para SkinOut
        self.custom_config = {
            'rate_limit': 5,      # Moderado para API paginada
            'burst_size': 2,      # 2 requests por burst
            'cache_ttl': 300,     # 5 minutos
            'timeout_seconds': 15, # Timeout más rápido
            'max_retries': 5,
            'max_concurrent': 3   # Concurrencia baja para evitar sobrecarga
        }
        
        super().__init__(
            platform_name="skinout",
            use_proxy=use_proxy,
            custom_config=self.custom_config
        )
        
        # URLs y endpoints
        self.api_url = "https://skinout.gg/api/market/items"
        self.base_url = "https://skinout.gg/"
        self.max_pages = 100  # Límite para evitar bucles infinitos
        
        # Headers específicos para SkinOut
        self.skinout_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://skinout.gg/',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        
        self.logger.info("AsyncSkinOutScraper inicializado con configuración para paginación")
    
    async def _get_page_data(self, page: int) -> List[Dict[str, Any]]:
        """
        Obtiene datos de una página específica
        
        Args:
            page: Número de página
            
        Returns:
            Lista de items de la página
        """
        params = {'page': page}
        
        try:
            async with self.session.get(
                self.api_url,
                params=params,
                headers=self.skinout_headers,
                timeout=aiohttp.ClientTimeout(total=self.custom_config['timeout_seconds'])
            ) as response:
                
                self.logger.info(f"Response status: {response.status} para página {page}")
                
                if response.status == 429:
                    self.logger.warning(f"Rate limit (429) en página {page} - pausando")
                    await asyncio.sleep(5)
                    return []
                elif response.status != 200:
                    self.logger.error(f"Error HTTP {response.status} al obtener página {page}")
                    return []
                
                # Parsear respuesta JSON
                data = await response.json()
                
                # SkinOut puede tener diferentes estructuras de respuesta
                # Intentar diferentes formatos comunes
                items_list = []
                
                if isinstance(data, dict):
                    # Formato típico: {"items": [...], "total": N}
                    items_list = data.get('items', data.get('data', []))
                elif isinstance(data, list):
                    # Formato directo: [item1, item2, ...]
                    items_list = data
                
                if not items_list:
                    self.logger.warning(f"No se encontraron items en página {page}")
                    return []
                
                self.logger.info(f"Recibidos {len(items_list)} items de página {page}")
                
                # Procesar items
                processed_items = []
                
                for item in items_list:
                    try:
                        if not isinstance(item, dict):
                            continue
                        
                        # Extraer datos del item (campos comunes en marketplaces)
                        item_name = (item.get('name') or 
                                   item.get('market_hash_name') or 
                                   item.get('item_name') or 
                                   item.get('title', ''))
                        
                        price_value = (item.get('price') or 
                                     item.get('current_price') or 
                                     item.get('sell_price') or 
                                     item.get('value', 0))
                        
                        if not item_name or price_value is None:
                            continue
                        
                        # Convertir precio a float
                        try:
                            price = float(price_value)
                        except (ValueError, TypeError):
                            continue
                        
                        # Solo incluir items con precio válido
                        if price > 0:
                            processed_item = {
                                'Item': item_name,
                                'Price': round(price, 2),
                                'Platform': 'SkinOut',
                                'URL': self.base_url
                            }
                            processed_items.append(processed_item)
                            
                    except (ValueError, TypeError, KeyError) as e:
                        self.logger.warning(f"Error procesando item de SkinOut: {e}")
                        continue
                
                self.logger.info(f"Página {page}: {len(items_list)} raw -> {len(processed_items)} válidos")
                return processed_items
                
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
        Obtiene datos de SkinOut API con paginación
        
        Returns:
            Lista de items con precios
        """
        self.logger.info("Iniciando scraping asíncrono de SkinOut con paginación...")
        
        all_items = []
        
        try:
            # Obtener datos de múltiples páginas
            for page in range(1, self.max_pages + 1):
                items = await self._get_page_data(page)
                
                if items:
                    all_items.extend(items)
                    self.logger.info(f"Total acumulado: {len(all_items)} items")
                    
                    # Rate limiting entre páginas
                    await asyncio.sleep(1)
                else:
                    # Si no hay items en esta página, intentar algunas páginas más
                    # antes de finalizar (puede haber páginas vacías esporádicas)
                    consecutive_empty = 0
                    for check_page in range(page, min(page + 3, self.max_pages + 1)):
                        check_items = await self._get_page_data(check_page)
                        if not check_items:
                            consecutive_empty += 1
                        else:
                            all_items.extend(check_items)
                            break
                    
                    if consecutive_empty >= 3:
                        self.logger.info(f"No hay más items después de página {page}, finalizando paginación")
                        break
            
            if all_items:
                # Obtener estadísticas
                total_items = len(all_items)
                avg_price = sum(item['Price'] for item in all_items) / total_items
                min_price = min(item['Price'] for item in all_items)
                max_price = max(item['Price'] for item in all_items)
                
                self.logger.info(
                    f"SkinOut scraping completado: {total_items} items "
                    f"(precio promedio: ${avg_price:.2f}, rango: ${min_price:.2f}-${max_price:.2f})"
                )
            else:
                self.logger.warning("No se obtuvieron items de SkinOut")
                self.logger.info("NOTA: SkinOut puede requerir autenticación o tener rate limiting estricto")
            
            return all_items
            
        except Exception as e:
            self.logger.error(f"Error en fetch_data de SkinOut: {e}")
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
                    if item['Item'] == item_name:
                        return item['Price']
            
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
    async with AsyncSkinOutScraper(use_proxy=False) as scraper:
        items = await scraper.run()
        
        print(f"Obtenidos {len(items)} items de SkinOut")
        
        # Mostrar algunos ejemplos
        if items:
            print("\nEjemplos de precios obtenidos:")
            for item in items[:5]:
                print(f"- {item['Item']}: ${item['Price']:.2f}")
        else:
            print("\nNOTA: SkinOut puede requerir autenticación o usar rate limiting estricto")
            print("Para mejores resultados, considerar usar el scraper sync con proxies")
        
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