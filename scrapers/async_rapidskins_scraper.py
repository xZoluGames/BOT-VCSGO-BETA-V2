"""
RapidSkins Async Scraper - BOT-vCSGO-Beta V2
Obtiene precios de RapidSkins.com - simplificado para async sin Selenium
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
from pathlib import Path
import re
sys.path.append(str(Path(__file__).parent.parent))
from core.async_base_scraper import AsyncBaseScraper


class AsyncRapidskinsScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para RapidSkins.com
    Versión simplificada sin Selenium que intenta usar API directa
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        # Configuración específica para RapidSkins
        self.custom_config = {
            'rate_limit': 3,      # Conservador para evitar detección
            'burst_size': 1,      # 1 request por burst
            'cache_ttl': 300,     # 5 minutos
            'timeout_seconds': 30, # Timeout estándar
            'max_retries': 3,
            'max_concurrent': 2   # Concurrencia muy baja
        }
        
        super().__init__(
            platform_name="rapidskins",
            use_proxy=use_proxy,
            custom_config=self.custom_config
        )
        
        # URLs y endpoints
        self.base_url = "https://rapidskins.com/"
        self.market_url = "https://rapidskins.com/market"
        
        # Headers específicos para RapidSkins
        self.rapidskins_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://rapidskins.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-CH-UA': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': '"Windows"'
        }
        
        self.logger.info("AsyncRapidskinsScraper inicializado (versión simplificada sin Selenium)")
    
    async def _get_market_page(self) -> Optional[str]:
        """
        Obtiene la página principal del market para extraer datos
        
        Returns:
            HTML de la página o None si falla
        """
        try:
            async with self.session.get(
                self.market_url,
                headers=self.rapidskins_headers,
                timeout=aiohttp.ClientTimeout(total=self.custom_config['timeout_seconds'])
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    self.logger.info(f"Página de market obtenida exitosamente ({len(html)} chars)")
                    return html
                else:
                    self.logger.error(f"Error HTTP {response.status} al obtener página de market")
                    return None
                    
        except asyncio.TimeoutError:
            self.logger.error("Timeout al obtener página de market")
            return None
        except Exception as e:
            self.logger.error(f"Error obteniendo página de market: {e}")
            return None
    
    async def _parse_items_from_html(self, html: str) -> List[Dict[str, Any]]:
        """
        Extrae items del HTML de la página
        
        Args:
            html: HTML de la página de market
            
        Returns:
            Lista de items formateados
        """
        items = []
        
        try:
            # Buscar patrones de items en el HTML
            # RapidSkins típicamente usa clases como 'item', 'trade-item', etc.
            
            # Patrón para encontrar nombres de items (ejemplo)
            item_name_pattern = r'<div[^>]*class="[^"]*item[^"]*"[^>]*>.*?title="([^"]+)"'
            item_names = re.findall(item_name_pattern, html, re.DOTALL | re.IGNORECASE)
            
            # Patrón para encontrar precios (ejemplo)
            price_pattern = r'<span[^>]*class="[^"]*price[^"]*"[^>]*>\$?([\d.,]+)'
            prices = re.findall(price_pattern, html, re.IGNORECASE)
            
            # Si no encuentra con los patrones básicos, intentar otros
            if not item_names:
                # Intentar patrón alternativo
                item_name_pattern = r'data-name="([^"]+)"'
                item_names = re.findall(item_name_pattern, html)
            
            if not prices:
                # Intentar patrón alternativo para precios
                price_pattern = r'data-price="([\d.,]+)"'
                prices = re.findall(price_pattern, html)
            
            # Combinar nombres y precios
            min_length = min(len(item_names), len(prices))
            
            for i in range(min_length):
                try:
                    name = item_names[i].strip()
                    price_str = prices[i].replace(',', '').replace('$', '')
                    price = float(price_str)
                    
                    if name and price > 0:
                        item = {
                            'Item': name,
                            'Price': price,
                            'Platform': 'RapidSkins',
                            'URL': self.market_url
                        }
                        items.append(item)
                        
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Error procesando item {i}: {e}")
                    continue
            
            self.logger.info(f"Extraídos {len(items)} items del HTML")
            
            # Si no se encontraron items, intentar métodos alternativos
            if not items:
                self.logger.warning("No se encontraron items con patrones HTML estándar")
                # Aquí se podrían agregar más patrones específicos
                
        except Exception as e:
            self.logger.error(f"Error parseando HTML: {e}")
        
        return items
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Método principal de scraping que implementa la interfaz AsyncBaseScraper
        
        Returns:
            Lista de items scrapeados
        """
        return await self.fetch_data()
    
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Obtiene datos de RapidSkins usando requests HTTP simples
        
        Returns:
            Lista de items con precios
        """
        self.logger.info("Iniciando scraping asíncrono de RapidSkins (método simplificado)...")
        
        try:
            # Obtener página principal
            html = await self._get_market_page()
            
            if not html:
                self.logger.error("No se pudo obtener la página de market")
                return []
            
            # Extraer items del HTML
            items = await self._parse_items_from_html(html)
            
            if items:
                # Obtener estadísticas
                total_items = len(items)
                avg_price = sum(item['Price'] for item in items) / total_items
                min_price = min(item['Price'] for item in items)
                max_price = max(item['Price'] for item in items)
                
                self.logger.info(
                    f"RapidSkins scraping completado: {total_items} items "
                    f"(precio promedio: ${avg_price:.2f}, rango: ${min_price:.2f}-${max_price:.2f})"
                )
            else:
                self.logger.warning("No se encontraron items en RapidSkins")
                self.logger.info("NOTA: RapidSkins puede requerir JavaScript o autenticación")
                self.logger.info("Considera usar el scraper sync con Selenium para mejores resultados")
            
            return items
            
        except Exception as e:
            self.logger.error(f"Error en fetch_data de RapidSkins: {e}")
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
            items = await self.fetch_data()
            
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
    async with AsyncRapidskinsScraper(use_proxy=False) as scraper:
        items = await scraper.run()
        
        print(f"Obtenidos {len(items)} items de RapidSkins")
        
        # Mostrar algunos ejemplos
        if items:
            print("\nEjemplos de precios obtenidos:")
            for item in items[:5]:
                print(f"- {item['Item']}: ${item['Price']:.2f}")
        else:
            print("\nNOTA: RapidSkins puede requerir JavaScript dinámico o autenticación")
            print("Para mejores resultados, usar el scraper sync con Selenium + Tampermonkey")
        
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