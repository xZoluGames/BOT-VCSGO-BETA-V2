def main():
    """
    Función principal para ejecutar el scraper
    NUEVO: Carga automática de proxies desde proxy.txt con logs detallados
    """
    print("=== SkinOut Scraper V2.1 - Logs de Proxy Mejorados ===")
    print("Nuevas características:")
    print("- ✅ Carga automática desde BOT-VCSGO-BETA-V2/proxy.txt")
    print("- ✅ Logs detallados de uso de proxies en tiempo real")
    print("- ✅ Verificación de rotación de proxies en errores 429")
    print("- ✅ Monitoreo de workers y paralelización")
    print("- ✅ Estadísticas completas de conexiones proxy")
    
    # Configuración de proxy con carga automática
    use_proxy_input = input("\n¿Usar proxy? (Y/n): ").lower()
    use_proxy = use_proxy_input != 'n'  # Por defecto True
    
    # Mostrar información de carga de proxies
    if use_proxy:
        print("\n📂 Verificando archivo de proxies...")
        # Verificar si existe el archivo antes de crear el scraper
        current_file = Path(__file__)
        """
SkinOut Scraper - BOT-vCSGO-Beta V2 - Mejorado

Scraper migrado desde BOT-vCSGO-Beta para SkinOut.gg
- Migrado desde core/scrapers/skinout_scraper.py de BOT-vCSGO-Beta
- API-based usando endpoints paginados de SkinOut
- Cliente optimizado con soporte para paralelización
- Sistema de reintentos automáticos por página
- NUEVO: Proxy por defecto con 230k proxies disponibles
- NUEVO: Rate limiting inteligente sin proxy
- NUEVO: Reintentos indefinidos con backoff exponencial
"""

from typing import List, Dict, Optional
import sys
from pathlib import Path
import time
import random
import requests  # Importar requests para uso directo con proxies
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# Agregar el directorio core al path
sys.path.append(str(Path(__file__).parent.parent))

from core.base_scraper import BaseScraper


def cargar_proxies_desde_archivo() -> Optional[List[str]]:
    """
    Carga la lista de proxies desde BOT-VCSGO-BETA-V2/proxy.txt
    
    Returns:
        Lista de proxies o None si no se puede cargar
    """
    # Obtener la ruta del archivo actual
    current_file = Path(__file__)
    # Ir al directorio padre (BOT-VCSGO-BETA-V2)
    project_root = current_file.parent.parent
    proxy_file = project_root / "proxy.txt"
    
    try:
        if proxy_file.exists():
            with open(proxy_file, 'r', encoding='utf-8') as f:
                proxies = [line.strip() for line in f if line.strip()]
            return proxies
        else:
            print(f"❌ Archivo de proxies no encontrado: {proxy_file}")
            return None
    except Exception as e:
        print(f"❌ Error cargando proxies desde {proxy_file}: {e}")
        return None


class SkinoutClient:
    """
    Cliente para SkinOut.gg (migrado desde BOT-vCSGO-Beta)
    
    Características mejoradas:
    - API endpoint: https://skinout.gg/api/market/items?page=N
    - Paginación automática
    - Sistema de reintentos indefinidos con backoff inteligente
    - Soporte para paralelización masiva con proxies (1000 workers)
    - Rate limiting inteligente sin proxy
    - Rotación automática de proxies en errores 429
    - NUEVO: Sistema de rotación de proxies del código original
    """
    
    def __init__(self, session, logger=None, use_proxy=True, max_workers=None, proxy_count=0, proxy_list=None):
        """
        Inicializa el cliente SkinOut
        
        Args:
            session: Sesión de requests del BaseScraper
            logger: Logger para registro de eventos
            use_proxy: Si usar proxy (por defecto True)
            max_workers: Número máximo de threads (auto-configurado según proxy)
            proxy_count: Número de proxies disponibles (para logs)
            proxy_list: Lista de proxies para rotación manual
        """
        self.session = session
        self.logger = logger
        self.use_proxy = use_proxy
        self.proxy_count = proxy_count
        
        # Sistema de rotación de proxies del código original
        self.proxy_list = proxy_list or []
        self.current_proxy_index = 0
        
        # Configuración según modo proxy
        if use_proxy:
            # Modo proxy: máxima velocidad
            self.max_workers = max_workers or 1000  # Masivo con 230k proxies
            self.retry_delay = 1  # Mínimo delay con proxy
            self.empty_pages_threshold = 5  # Más páginas para confirmar final
            self.batch_size = min(self.max_workers, 50)  # Lotes grandes
        else:
            # Modo sin proxy: conservador
            self.max_workers = max_workers or 3  # Muy limitado sin proxy
            self.retry_delay = 2  # Delay base más alto
            self.empty_pages_threshold = 3
            self.batch_size = 2  # Lotes pequeños
        
        # Headers específicos para SkinOut (del BOT-vCSGO-Beta original)
        self.session.headers.update({
            'Accept': 'application/json',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Origin': 'https://skinout.gg',
            'Referer': 'https://skinout.gg/'
        })
        
        if self.logger:
            mode = "PROXY" if use_proxy else "SIN PROXY"
            proxy_info = f" ({proxy_count:,} proxies cargados)" if use_proxy and proxy_count > 0 else ""
            self.logger.info(f"🔧 Cliente SkinOut inicializado en modo {mode}{proxy_info} - Workers: {self.max_workers}")
    
    def get_next_proxy(self):
        """
        Obtiene el siguiente proxy de la lista (rotación circular del código original)
        
        Returns:
            String del proxy en formato requerido por requests
        """
        if not self.proxy_list:
            return None
            
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        return proxy
    
    def log_proxy_usage(self, page, success=True, error_msg=None, current_proxy=None):
        """
        Log detallado del uso de proxies para monitoreo
        
        Args:
            page: Número de página
            success: Si la request fue exitosa
            error_msg: Mensaje de error si falló
            current_proxy: Proxy actual usado
        """
        if not self.logger:
            return
            
        if self.use_proxy:
            # Mostrar proxy actual (ocultar credenciales si las hay)
            proxy_display = "N/A"
            if current_proxy:
                if '@' in current_proxy:
                    proxy_display = current_proxy.split('@')[-1]  # Solo IP:puerto
                else:
                    proxy_display = current_proxy
            
            status = "✅ ÉXITO" if success else "❌ ERROR"
            if success:
                self.logger.debug(f"🌐 PROXY | Página {page} | {status} | Proxy: {proxy_display} | Índice: {self.current_proxy_index-1}/{len(self.proxy_list)}")
            else:
                self.logger.warning(f"🌐 PROXY | Página {page} | {status} | Proxy: {proxy_display} | Error: {error_msg}")
        else:
            status = "✅ ÉXITO" if success else "❌ ERROR"
            if success:
                self.logger.debug(f"🔗 DIRECTO | Página {page} | {status} | Sin proxy")
            else:
                self.logger.warning(f"🔗 DIRECTO | Página {page} | {status} | Error: {error_msg}")
    
    def obtener_datos_pagina(self, page):
        """
        Obtiene datos de una página específica con reintentos indefinidos
        Integra el sistema de rotación de proxies del código original
        
        Args:
            page: Número de página a obtener
            
        Returns:
            Tupla (page, items) - nunca retorna None (reintentos indefinidos)
        """
        retry_count = 0
        base_delay = self.retry_delay
        
        while True:  # Reintentos indefinidos (como el código original)
            current_proxy = None
            try:
                url = f"https://skinout.gg/api/market/items?page={page}"
                
                if self.logger and retry_count == 0:
                    self.logger.debug(f"📡 Fetching page {page} from SkinOut")
                
                # Configurar proxy si está habilitado (método del código original)
                if self.use_proxy and self.proxy_list:
                    current_proxy = self.get_next_proxy()
                    proxies = {"http": current_proxy, "https": current_proxy}
                    
                    # Headers específicos (del código original)
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'application/json',
                        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                        'Origin': 'https://skinout.gg',
                        'Referer': 'https://skinout.gg/'
                    }
                    
                    response = requests.get(
                        url,
                        proxies=proxies,
                        headers=headers,
                        timeout=15
                    )
                else:
                    # Sin proxy - usar la sesión normal
                    response = self.session.get(url, timeout=15)
                
                response.raise_for_status()
                json_data = response.json()
                def limpiar_texto(texto):
                    # Removemos los paréntesis y su contenido
                    texto = texto.replace("(", "").replace(")", "")

                    # Reemplazamos caracteres especiales y espacios con guiones
                    caracteres_especiales = ["|", " ", ".", ",", ";", ":", "!", "?", "'", '"', "™"]
                    for caracter in caracteres_especiales:
                        texto = texto.replace(caracter, "-")

                    # Eliminamos guiones múltiples si se generaron
                    while "--" in texto:
                        texto = texto.replace("--", "-")

                    # Eliminamos guiones al inicio y final si existen
                    texto = texto.strip("-")

                    return texto
                if json_data.get('success') and 'items' in json_data:
                    items = json_data['items']
                    # Formatear items (del BOT-vCSGO-Beta original)
                    formatted_items = []
                    for item in items:
                        try:
                            formatted_items.append({
                                'Item': item['market_hash_name'],
                                'Price': float(item['price']),
                                'Platform': 'SkinOut',
                                'URL': "https://skinout.gg/en/market/" + limpiar_texto(item['market_hash_name'])
                            })
                        except Exception as e:
                            if self.logger:
                                self.logger.warning(f"Error procesando item en página {page}: {e}")
                            continue
                    
                    # Log éxito con proxy
                    self.log_proxy_usage(page, success=True, current_proxy=current_proxy)
                    
                    # Éxito - resetear contador de reintentos si había errores previos
                    if retry_count > 0 and self.logger:
                        mode_info = f"con {'proxy' if self.use_proxy else 'conexión directa'}"
                        self.logger.info(f"✅ Página {page} exitosa después de {retry_count} reintentos {mode_info}")
                    
                    return page, formatted_items
                
                # Si la respuesta es exitosa pero no hay items
                if json_data.get('success'):
                    self.log_proxy_usage(page, success=True, current_proxy=current_proxy)
                    return page, []
                
                # Si no hay success, intentar de nuevo
                raise Exception(f"Respuesta sin success en página {page}")
                
            except Exception as e:
                retry_count += 1
                
                # Log error con proxy
                self.log_proxy_usage(page, success=False, error_msg=str(e), current_proxy=current_proxy)
                
                # Calcular delay según modo
                if self.use_proxy:
                    # Con proxy: delay fijo mínimo, rotar proxy automáticamente en cada error
                    delay = self.retry_delay
                    if "429" in str(e) or "too many" in str(e).lower():
                        if self.logger:
                            proxy_info = f"Rotando a proxy {self.current_proxy_index}/{len(self.proxy_list)}" if self.proxy_list else "sin proxies"
                            self.logger.warning(f"🚫 Error 429 en página {page} - {proxy_info}")
                        delay = 0.5  # Delay mínimo para rotar proxy
                    
                    # La rotación es automática en get_next_proxy() en el siguiente intento
                else:
                    # Sin proxy: backoff exponencial para rate limiting
                    if "429" in str(e) or "too many" in str(e).lower():
                        # Backoff exponencial más agresivo para 429
                        delay = min(base_delay * (2 ** min(retry_count-1, 8)), 300)  # Máximo 5 minutos
                    else:
                        # Otros errores: backoff más suave
                        delay = min(base_delay * (1.5 ** min(retry_count-1, 6)), 120)  # Máximo 2 minutos
                
                if self.logger:
                    mode_info = f"{'🌐 PROXY' if self.use_proxy else '🔗 DIRECTO'}"
                    proxy_status = f" (proxy {self.current_proxy_index}/{len(self.proxy_list)})" if self.use_proxy and self.proxy_list else ""
                    self.logger.warning(f"{mode_info} | Página {page} (intento {retry_count}){proxy_status}: {e}. Reintentando en {delay:.1f}s...")
                
                time.sleep(delay + random.uniform(0, 1))  # Añadir jitter aleatorio
    
    def obtener_todas_las_paginas(self, start_page=1, max_pages=None):
        """
        Obtiene todas las páginas usando paralelización optimizada según modo
        
        Args:
            start_page: Página inicial
            max_pages: Máximo número de páginas (None = sin límite)
            
        Returns:
            Lista completa de items de todas las páginas
        """
        all_items = []
        current_page = start_page
        empty_pages_count = 0
        
        # Límite automático según modo
        if max_pages is None:
            max_pages = 10000 if self.use_proxy else 200  # Más páginas con proxy
        
        mode_info = f"PROXY ({self.max_workers} workers)" if self.use_proxy else f"SIN PROXY ({self.max_workers} workers)"
        
        if self.logger:
            self.logger.info(f"Iniciando obtención masiva - Modo: {mode_info} - Páginas: {start_page} a {max_pages}")
        
        while current_page <= max_pages and empty_pages_count < self.empty_pages_threshold:
            # Crear lote de páginas a procesar
            pages_to_process = list(range(current_page, min(current_page + self.batch_size, max_pages + 1)))
            
            if self.logger:
                self.logger.info(f"Procesando lote: páginas {pages_to_process[0]}-{pages_to_process[-1]} ({len(pages_to_process)} páginas)")
            
            # Procesar lote con ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Enviar todas las páginas del lote
                future_to_page = {
                    executor.submit(self.obtener_datos_pagina, page): page 
                    for page in pages_to_process
                }
                
                # Recopilar resultados
                batch_items = 0
                for future in as_completed(future_to_page):
                    page = future_to_page[future]
                    try:
                        page_num, items = future.result()  # Nunca será None ahora
                        if items:
                            all_items.extend(items)
                            batch_items += len(items)
                            empty_pages_count = 0  # Resetear contador
                        else:
                            empty_pages_count += 1
                            if self.logger:
                                self.logger.debug(f"Página {page_num}: vacía ({empty_pages_count}/{self.empty_pages_threshold})")
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Error crítico procesando future de página {page}: {e}")
                        # No incrementar empty_pages_count por errores críticos
            
            if self.logger and batch_items > 0:
                self.logger.info(f"Lote completado: +{batch_items} items (Total: {len(all_items)})")
            
            current_page += self.batch_size
            
            # Pausa entre lotes según modo
            if current_page <= max_pages:
                pause = 0.5 if self.use_proxy else 3.0  # Pausa mínima con proxy
                time.sleep(pause)
        
        if empty_pages_count >= self.empty_pages_threshold:
            if self.logger:
                self.logger.info(f"Scraping finalizado: {empty_pages_count} páginas vacías consecutivas detectadas")
        
        return all_items


class SkinoutScraper(BaseScraper):
    """
    Scraper para SkinOut.gg - Migrado desde BOT-vCSGO-Beta V2 Mejorado
    
    Mejoras V2.1:
    - Proxy por defecto (True) con soporte masivo para 230k proxies
    - Rate limiting inteligente sin proxy con backoff exponencial
    - Reintentos indefinidos con rotación automática de proxy
    - Paralelización masiva (1000 workers) con proxy
    - Mode conservador sin proxy (3 workers)
    - Detección inteligente de errores 429 y manejo específico
    """
    
    def __init__(self, use_proxy: bool = True, proxy_list: Optional[List[str]] = None):
        """
        Inicializa el scraper de SkinOut
        
        Args:
            use_proxy: Si usar proxy (POR DEFECTO True)
            proxy_list: Lista de proxies a usar (se carga automáticamente desde proxy.txt)
        """
        # Cargar proxies automáticamente si no se proporcionan
        if proxy_list is None and use_proxy:
            print("📂 Cargando proxies desde BOT-VCSGO-BETA-V2/proxy.txt...")
            proxy_list = cargar_proxies_desde_archivo()
            
            if proxy_list:
                print(f"✅ Proxies cargados exitosamente: {len(proxy_list):,} proxies disponibles")
            else:
                print("⚠️ No se pudieron cargar proxies. Continuando sin proxy...")
                use_proxy = False
        
        # Configuración específica según modo proxy
        if use_proxy and proxy_list:
            config = {
                'timeout': 15,
                'max_retries': 999,  # Reintentos indefinidos
                'retry_delay': 1,    # Mínimo con proxy
                'interval': 60,      # Menor intervalo con proxy
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Encoding': 'gzip, deflate, br'
                }
            }
        else:
            # Sin proxy o sin lista de proxies
            use_proxy = False
            proxy_list = None
            config = {
                'timeout': 15,
                'max_retries': 999,  # Reintentos indefinidos también
                'retry_delay': 2,    # Mayor delay base sin proxy
                'interval': 300,     # Intervalo más largo sin proxy
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Encoding': 'gzip, deflate, br'
                }
            }
        
        super().__init__('skinout', use_proxy, proxy_list, config)
        
        # Contar proxies para logs
        proxy_count = len(proxy_list) if proxy_list else 0
        
        # Inicializar cliente SkinOut usando la sesión del BaseScraper
        self.client = SkinoutClient(
            self.session, 
            logger=self.logger, 
            use_proxy=use_proxy,
            proxy_count=proxy_count,
            proxy_list=proxy_list  # Pasar la lista para rotación manual
        )
        
        mode_info = "PROXY" if use_proxy else "SIN PROXY"
        self.logger.info(f"🚀 SkinOut scraper V2.1 inicializado en modo {mode_info}")
        
        if use_proxy and proxy_list:
            self.logger.info(f"🌐 Sistema de proxies configurado: {len(proxy_list):,} proxies cargados desde proxy.txt")
            # Log de muestra de proxies (primeros 3, sin mostrar credenciales completas)
            sample_proxies = []
            for proxy in proxy_list[:3]:
                # Ocultar credenciales si las hay
                if '@' in proxy:
                    proxy_clean = proxy.split('@')[-1]  # Solo IP:puerto
                else:
                    proxy_clean = proxy
                sample_proxies.append(proxy_clean)
            self.logger.info(f"🔍 Muestra de proxies: {', '.join(sample_proxies)}...")
        else:
            self.logger.info("🔗 Modo conexión directa - Sin proxies")
    
    def parse_response(self, response) -> List[Dict]:
        """
        Método requerido por BaseScraper - no usado directamente en SkinOut
        """
        return []
    
    def fetch_data(self) -> List[Dict]:
        """
        Obtiene datos de SkinOut usando paginación paralela optimizada
        
        Mejoras V2.1:
        - Paralelización masiva con proxy (1000 workers)
        - Rate limiting inteligente sin proxy (3 workers)
        - Reintentos indefinidos con backoff exponencial
        - Rotación automática de proxies en errores 429
        - NUEVO: Logs detallados del uso de proxies
        
        Returns:
            Lista completa de items del marketplace
        """
        proxy_count = len(self.proxy_list) if self.proxy_list else 0
        mode_info = f"PROXY ({proxy_count:,} proxies)" if self.client.use_proxy else "SIN PROXY (rate limited)"
        self.logger.info(f"🎯 Iniciando scraping masivo de SkinOut - Modo: {mode_info}")
        
        # Log sobre API key
        if self.api_key:
            self.logger.info("🔑 Usando API key de SkinOut para autenticación")
        
        # Log inicial de configuración de proxy
        if self.client.use_proxy and proxy_count > 0:
            self.logger.info(f"🌐 Configuración de proxy activa:")
            self.logger.info(f"   📊 Total proxies: {proxy_count:,}")
            self.logger.info(f"   🚀 Workers: {self.client.max_workers}")
            self.logger.info(f"   📦 Tamaño de lote: {self.client.batch_size}")
            self.logger.info(f"   ⏱️ Delay entre reintentos: {self.client.retry_delay}s")
        else:
            self.logger.info(f"🔗 Configuración sin proxy:")
            self.logger.info(f"   🐌 Workers limitados: {self.client.max_workers}")
            self.logger.info(f"   📦 Tamaño de lote: {self.client.batch_size}")
            self.logger.info(f"   ⏱️ Delay base: {self.client.retry_delay}s (con backoff exponencial)")
        
        try:
            # Obtener todas las páginas usando el cliente optimizado
            all_items = self.client.obtener_todas_las_paginas(
                start_page=1,
                max_pages=None  # Sin límite, se detiene por páginas vacías
            )
            
            if all_items:
                self.logger.info(f"✅ Scraping completado exitosamente. Total items: {len(all_items):,}")
                
                # Log final de estadísticas de proxy si aplica
                if self.client.use_proxy:
                    self.logger.info(f"🌐 Estadísticas finales de proxy:")
                    self.logger.info(f"   📡 Requests completadas usando {proxy_count:,} proxies disponibles")
                    self.logger.info(f"   ⚡ Modo paralelo masivo con {self.client.max_workers} workers")
            else:
                self.logger.warning("⚠️ No se obtuvieron items en esta ejecución")
            
            return all_items
            
        except Exception as e:
            self.logger.error(f"❌ Error crítico en fetch_data de SkinOut: {e}")
            return []


def main():
    """
    Función principal para ejecutar el scraper
    NUEVO: Proxy por defecto con opción de desactivar
    """
    print("=== SkinOut Scraper V2.1 - Modo Proxy por Defecto ===")
    print("Cambios principales:")
    print("- ✅ Proxy activado por defecto (230k proxies disponibles)")
    print("- ✅ Paralelización masiva: 1000 workers con proxy / 3 sin proxy")
    print("- ✅ Reintentos indefinidos con backoff inteligente")
    print("- ✅ Rotación automática de proxies en errores 429")
    print("- ✅ Rate limiting inteligente sin proxy")
    
    # Configuración de proxy
    use_proxy_input = input("\n¿Usar proxy? (Y/n): ").lower()
    use_proxy = use_proxy_input != 'n'  # Por defecto True
    
    # Crear scraper
    scraper = SkinoutScraper(use_proxy=use_proxy)
    
    try:
        print(f"\n🚀 Ejecutando SkinOut Scraper V2.1...")
        mode = "PROXY (masivo)" if use_proxy else "SIN PROXY (limitado)"
        print(f"📡 Modo: {mode}")
        
        # Ejecutar una vez para prueba
        start_time = time.time()
        data = scraper.run_once()
        end_time = time.time()
        
        print(f"\n✅ Scraper completado en {end_time - start_time:.1f} segundos:")
        print(f"   📊 Items obtenidos: {len(data):,}")
        print(f"   📈 Estadísticas: {scraper.get_stats()}")
        
        if data:
            print(f"\n📋 Muestra de items (primeros 5):")
            for i, item in enumerate(data[:5], 1):
                print(f"   {i}. {item['Item']}: ${item['Price']}")
                
            # Mostrar rentabilidad si está disponible
            profitable_items = [item for item in data if item.get('is_profitable', False)]
            if profitable_items:
                print(f"\n💰 Items rentables encontrados: {len(profitable_items)}")
                for i, item in enumerate(profitable_items[:3], 1):
                    profit_info = f"Ganancia: {item.get('profit_margin', 0):.1f}%" if item.get('profit_margin') else "Ganancia: calculando..."
                    print(f"   {i}. {item['Item']}: ${item['Price']} → ${item.get('sell_price', 'N/A')} ({profit_info})")
        
        # Opción para ejecutar en bucle
        run_forever = input("\n🔄 ¿Ejecutar en bucle continuo? (y/N): ").lower() == 'y'
        if run_forever:
            print("🔁 Iniciando bucle infinito... (Ctrl+C para detener)")
            interval = 60 if use_proxy else 300  # Intervalo según modo
            print(f"⏱️ Intervalo entre ejecuciones: {interval} segundos")
            scraper.run_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Limpiar recursos
        print("\n🧹 Cerrando conexiones...")
        scraper.session.close()
        print("✅ Limpieza completada")


if __name__ == "__main__":
    main()