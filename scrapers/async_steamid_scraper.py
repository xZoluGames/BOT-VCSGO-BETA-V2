"""
SteamID Async Scraper - BOT-vCSGO-Beta V2
Obtiene nameids de Steam Community Market de forma asíncrona
"""

import asyncio
import aiohttp
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
import json
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.async_base_scraper import AsyncBaseScraper


class AsyncSteamIDScraper(AsyncBaseScraper):
    """
    Scraper asíncrono para obtener nameids de Steam Community Market
    Procesa items de steam_listing_data.json para obtener nameids faltantes
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        # Configuración específica para SteamID
        self.custom_config = {
            'rate_limit': 10,     # Conservador para Steam
            'burst_size': 3,      # Pequeños bursts
            'cache_ttl': 600,     # 10 minutos
            'timeout_seconds': 30, # Timeout alto para Steam
            'max_retries': 5,
            'max_concurrent': 5   # Muy limitado para Steam
        }
        
        super().__init__(
            platform_name="steamid",
            use_proxy=use_proxy,
            custom_config=self.custom_config
        )
        
        # URL base para Steam Community Market
        self.base_url = "https://steamcommunity.com/market/listings/730/{}"
        
        # Headers específicos para Steam
        self.steam_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        self.logger.info("AsyncSteamIDScraper inicializado con configuración conservadora para Steam")
    
    def _extract_nameid_from_html(self, html_content: str, item_name: str) -> Optional[str]:
        """
        Extrae nameid del HTML de Steam usando patrones mejorados
        
        Args:
            html_content: Contenido HTML de la página de Steam
            item_name: Nombre del item para logging
            
        Returns:
            Nameid extraído o None si no se encuentra
        """
        try:
            # Patrones mejorados para mejor extracción
            patterns = [
                r'Market_LoadOrderSpread\(\s*(\d+)\s*\)',
                r'g_rgAssets\[730\]\[2\]\[(\d+)\]',
                r'"nameid":(\d+)',
                r'nameid=(\d+)',
                r'Market_LoadOrderSpread\\(\\s*(\\d+)\\s*\\)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html_content)
                if match:
                    nameid = match.group(1)
                    self.logger.debug(f"Nameid encontrado para {item_name}: {nameid}")
                    return nameid
            
            self.logger.warning(f"No se pudo extraer nameid para {item_name}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error extrayendo nameid para {item_name}: {e}")
            return None
    
    async def _process_item(self, item_name: str) -> Optional[Dict[str, Any]]:
        """
        Procesa un item individual para obtener su nameid
        
        Args:
            item_name: Nombre del item
            
        Returns:
            Dict con name, id y timestamp o None si falla
        """
        try:
            # Formatear URL
            from urllib.parse import quote
            url = self.base_url.format(quote(item_name))
            
            async with self.session.get(
                url,
                headers=self.steam_headers,
                timeout=aiohttp.ClientTimeout(total=self.custom_config['timeout_seconds'])
            ) as response:
                
                if response.status == 200:
                    html_content = await response.text()
                    nameid = self._extract_nameid_from_html(html_content, item_name)
                    
                    if nameid:
                        return {
                            'name': item_name,
                            'id': nameid,
                            'last_updated': datetime.now().timestamp()
                        }
                    else:
                        self.logger.warning(f"No se encontró nameid en HTML para {item_name}")
                        return None
                else:
                    self.logger.error(f"Error HTTP {response.status} para {item_name}")
                    return None
                    
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout al obtener nameid para {item_name}")
            return None
        except Exception as e:
            self.logger.error(f"Error procesando {item_name}: {e}")
            return None
    
    async def _load_existing_nameids(self) -> List[Dict[str, Any]]:
        """
        Carga nameids existentes del archivo
        
        Returns:
            Lista de nameids existentes
        """
        # Usar PathManager para obtener ruta de datos
        data_dir = self.path_manager.data_dir
        nameids_file = data_dir / 'item_nameids.json'
        existing_nameids = []
        
        if nameids_file.exists():
            try:
                with open(nameids_file, 'r', encoding='utf-8') as f:
                    existing_nameids = json.load(f)
                self.logger.info(f"Cargados {len(existing_nameids)} nameids existentes")
            except Exception as e:
                self.logger.error(f"Error cargando nameids existentes: {e}")
        else:
            self.logger.info("No hay archivo de nameids existente, comenzando desde cero")
        
        return existing_nameids
    
    async def _load_steam_listing_items(self) -> List[str]:
        """
        Carga items del archivo steam_listing_data.json
        
        Returns:
            Lista de nombres de items únicos
        """
        # Usar PathManager para obtener ruta de datos
        data_dir = self.path_manager.data_dir
        listing_file = data_dir / 'steam_listing_data.json'
        
        if not listing_file.exists():
            self.logger.error("steam_listing_data.json no encontrado - ejecutar steam_listing scraper primero")
            return []
        
        try:
            with open(listing_file, 'r', encoding='utf-8') as f:
                listing_data = json.load(f)
            
            # Extraer nombres únicos de items
            item_names = set()
            for item in listing_data:
                if isinstance(item, dict) and 'Item' in item:
                    item_names.add(item['Item'])
            
            item_names_list = list(item_names)
            self.logger.info(f"Cargados {len(item_names_list)} items únicos de steam_listing_data.json")
            return item_names_list
            
        except Exception as e:
            self.logger.error(f"Error cargando steam_listing_data.json: {e}")
            return []
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Método principal de scraping que implementa la interfaz AsyncBaseScraper
        
        Returns:
            Lista de nameids actualizados
        """
        return await self.fetch_data()
    
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Obtiene nameids comparando con listing existente
        
        Returns:
            Lista actualizada de nameids
        """
        self.logger.info("🚀 Iniciando obtención de nameids de Steam Community Market...")
        
        # Cargar datos existentes
        existing_nameids = await self._load_existing_nameids()
        steam_items = await self._load_steam_listing_items()
        
        if not steam_items:
            self.logger.error("No se pudieron cargar items de steam_listing_data.json")
            return existing_nameids
        
        # Crear dict de nameids existentes para búsqueda rápida
        existing_dict = {item['name']: item for item in existing_nameids}
        
        # Identificar items que necesitan nameids
        items_to_process = []
        for item_name in steam_items:
            if item_name not in existing_dict:
                items_to_process.append(item_name)
        
        self.logger.info(f"📊 Items en steam listing: {len(steam_items)}")
        self.logger.info(f"💾 Nameids existentes: {len(existing_nameids)}")
        self.logger.info(f"🆕 Items nuevos a procesar: {len(items_to_process)}")
        
        if not items_to_process:
            self.logger.info("✅ No hay items nuevos que procesar")
            return existing_nameids
        
        # Procesar items nuevos con concurrencia limitada
        semaphore = asyncio.Semaphore(self.custom_config['max_concurrent'])
        
        async def process_with_semaphore(item_name):
            async with semaphore:
                result = await self._process_item(item_name)
                # Rate limiting entre requests
                await asyncio.sleep(1.0 / self.custom_config['rate_limit'])
                return result
        
        self.logger.info(f"🔄 Procesando {len(items_to_process)} items con {self.custom_config['max_concurrent']} workers...")
        
        # Crear todas las tareas
        tasks = [process_with_semaphore(item_name) for item_name in items_to_process]
        
        # Ejecutar con progreso
        new_nameids = []
        completed = 0
        
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                if result:
                    new_nameids.append(result)
                
                completed += 1
                if completed % 10 == 0 or completed == len(tasks):
                    self.logger.info(f"📈 Progreso: {completed}/{len(tasks)} items procesados, {len(new_nameids)} nameids obtenidos")
                    
            except Exception as e:
                self.logger.error(f"Error en tarea: {e}")
                completed += 1
        
        # Combinar nameids existentes con nuevos
        # Mantener existentes que aún están en la lista de Steam
        updated_nameids = [item for item in existing_nameids if item['name'] in steam_items]
        updated_nameids.extend(new_nameids)
        
        self.logger.info(f"✅ Scraping completado: {len(new_nameids)} nameids nuevos obtenidos")
        self.logger.info(f"📊 Total nameids: {len(updated_nameids)} items")
        
        return updated_nameids
    
    async def get_item_nameid(self, item_name: str) -> Optional[str]:
        """
        Obtiene el nameid de un item específico
        
        Args:
            item_name: Nombre del item
            
        Returns:
            Nameid del item o None si no se encuentra
        """
        try:
            result = await self._process_item(item_name)
            return result['id'] if result else None
            
        except Exception as e:
            self.logger.error(f"Error obteniendo nameid para {item_name}: {e}")
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
    async with AsyncSteamIDScraper(use_proxy=False) as scraper:
        nameids = await scraper.run()
        
        print(f"Obtenidos {len(nameids)} nameids de Steam")
        
        # Mostrar algunos ejemplos
        if nameids:
            print("\nEjemplos de nameids obtenidos:")
            for item in nameids[-5:]:  # Últimos 5 (los más recientes)
                print(f"- {item['name']}: nameid={item.get('id', 'N/A')}")
        else:
            print("\nNOTA: Asegúrate de que existe steam_listing_data.json")
        
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