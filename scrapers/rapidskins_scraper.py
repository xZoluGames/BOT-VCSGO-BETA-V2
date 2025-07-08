"""
RapidSkins Scraper - BOT-vCSGO-Beta V2

Scraper completo migrado desde BOT-vCSGO-Beta para RapidSkins.com
- Migrado desde core/scrapers/rapidskins_scraper.py de BOT-vCSGO-Beta
- Usa Selenium + ChromeDriver con perfil personalizado
- Integración con Tampermonkey para extracción automática
- Guardado automático en \data\rapidskins_data.json
"""

from typing import List, Dict, Optional
import sys
from pathlib import Path
import time
import json
import os
from datetime import datetime

# Agregar el directorio core al path
sys.path.append(str(Path(__file__).parent.parent))

from core.base_scraper import BaseScraper

# Importar dependencias de Selenium (requeridas)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, JavascriptException
    import orjson
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class RapidskinsScraper(BaseScraper):
    """
    Scraper para RapidSkins.com - Migrado desde BOT-vCSGO-Beta
    
    Características migradas del BOT-vCSGO-Beta:
    - Selenium + ChromeDriver con perfil personalizado
    - Integración con Tampermonkey para extracción automática
    - URL: https://rapidskins.com/market
    - Sistema de espera hasta completar extracción
    - Headers específicos para evitar detección
    - Timeouts configurables y reintentos
    - Guardado automático en \data\rapidskins_data.json
    
    Mejoras en V2:
    - Usa BaseScraper V2 con todas las optimizaciones
    - Cache automático
    - Profitability engine integrado
    - Manejo de errores mejorado
    - Sin dependencia de API RustSkins
    """
    
    def __init__(self, use_proxy: bool = False, proxy_list: Optional[List[str]] = None):
        """
        Inicializa el scraper de RapidSkins
        
        Args:
            use_proxy: Si usar proxy o no
            proxy_list: Lista de proxies a usar
        """
        if not SELENIUM_AVAILABLE:
            raise ImportError("RapidSkins requiere Selenium. Instalar con: pip install selenium")
        
        # Configuración específica para RapidSkins
        config = {
            'timeout': 30,
            'max_retries': 3,
            'retry_delay': 3,
            'interval': 120,  # Más tiempo por ser complejo
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/html, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://rapidskins.com/',
                'Origin': 'https://rapidskins.com'
            }
        }
        
        # Inicializar con nombre de plataforma pero sin API key
        super().__init__('rapidskins', use_proxy, proxy_list, config)
        
        # Suprimir el uso de API key
        self.api_key = None
        
        self.rapidskins_url = 'https://rapidskins.com/market'
        
        # Configuración del perfil de Chrome (adaptado de BOT-vCSGO-Beta)
        self.chrome_profile_path = r"C:\Users\Zolu\AppData\Local\Google\Chrome\User Data\Profile_Selenium"
        
        # Configurar directorio de datos en la raíz del proyecto
        # Obtener el directorio raíz del proyecto (dos niveles arriba de scrapers/)
        project_root = Path(__file__).parent.parent
        self.data_dir = project_root / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.output_file = self.data_dir / "rapidskins_data.json"
        
        self.logger.info("RapidSkins scraper inicializado con Selenium + ChromeDriver")
        self.logger.info("Configuración migrada desde BOT-vCSGO-Beta")
        self.logger.info(f"Datos se guardarán en: {self.output_file}")
    
    def _configure_chromedriver(self):
        """
        Configura y retorna una instancia de ChromeDriver con el perfil especificado
        Migrado desde BOT-vCSGO-Beta
        """
        chrome_options = Options()
        
        # Configurar el perfil de usuario (mantener la configuración del scraper original)
        chrome_options.add_argument(f"--user-data-dir={self.chrome_profile_path}")
        
        # Opciones adicionales para optimización (del scraper original)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Configuración para reducir el uso de memoria (del scraper original)
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        
        # Deshabilitar las notificaciones (del scraper original)
        prefs = {
            "profile.default_content_setting_values.notifications": 2
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Configuración adicional para evitar detección (del scraper original)
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=400,200")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            # Configurar timeouts (del scraper original)
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)
            
            self.logger.info("ChromeDriver configurado exitosamente con perfil personalizado")
            return driver
        except Exception as e:
            self.logger.error(f"Error al iniciar ChromeDriver: {e}")
            return None
    
    def _navigate_to_rapidskins(self, driver, max_retries: int = 3):
        """
        Navega a RapidSkins con reintentos
        Migrado desde BOT-vCSGO-Beta
        """
        for attempt in range(max_retries):
            try:
                driver.get(self.rapidskins_url)
                
                # Esperar hasta que la página se cargue
                wait = WebDriverWait(driver, 20)
                
                try:
                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "items-wrapper")))
                    self.logger.info("Página de market cargada correctamente")
                    return
                except:
                    # Si no encuentra items-wrapper, intentar con otros elementos
                    try:
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "trade")))
                        self.logger.info("Página cargada (encontrado elemento trade)")
                        return
                    except:
                        pass
                
                # Verificar si llegamos a la página correcta
                if "rapidskins.com" in driver.current_url:
                    self.logger.info("Navegación exitosa a RapidSkins")
                    return
                    
            except TimeoutException:
                self.logger.warning(f"Timeout en intento {attempt + 1} de {max_retries}")
                if attempt < max_retries - 1:
                    self.logger.info("Reintentando...")
                    time.sleep(2)
                else:
                    raise Exception("No se pudo cargar la página después de varios intentos")
            except Exception as e:
                self.logger.error(f"Error al navegar: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise
    
    def _wait_for_tampermonkey_completion(self, driver, timeout: int = 300) -> bool:
        """
        Espera hasta que el script de Tampermonkey haya completado la extracción
        Migrado desde BOT-vCSGO-Beta
        """
        self.logger.info("Esperando que Tampermonkey complete la extracción...")
        
        start_time = time.time()
        check_interval = 2  # Verificar cada 2 segundos
        
        while time.time() - start_time < timeout:
            try:
                # Verificar si la extracción está completa
                extraction_status = driver.execute_script("""
                    if (window.getRapidSkinsData) {
                        const data = window.getRapidSkinsData();
                        return {
                            completed: data.completed,
                            totalItems: data.totalItems,
                            hasData: data.data && data.data.length > 0
                        };
                    }
                    return { completed: false, totalItems: 0, hasData: false };
                """)
                
                if extraction_status['completed'] and extraction_status['hasData']:
                    self.logger.info(f"Extracción completada. Items encontrados: {extraction_status['totalItems']}")
                    return True
                
                # Mostrar progreso
                current_items = extraction_status['totalItems']
                if current_items > 0:
                    self.logger.info(f"Items procesados hasta ahora: {current_items}")
                
                time.sleep(check_interval)
                
            except JavascriptException:
                # El script de Tampermonkey aún no ha cargado
                self.logger.debug("Esperando que se cargue el script de Tampermonkey...")
                time.sleep(check_interval)
            except Exception as e:
                self.logger.warning(f"Error al verificar estado: {e}")
                time.sleep(check_interval)
        
        return False
    
    def _get_tampermonkey_data(self, driver) -> List[Dict]:
        """
        Obtiene los datos extraídos por el script de Tampermonkey
        Migrado desde BOT-vCSGO-Beta
        """
        try:
            # Intentar obtener los datos usando la función global
            data = driver.execute_script("""
                if (window.exportRapidSkinsJSON) {
                    return window.exportRapidSkinsJSON();
                } else if (window.rapidskins_scraped_data) {
                    return JSON.stringify(window.rapidskins_scraped_data, null, 2);
                }
                return null;
            """)
            
            if data:
                if isinstance(data, str):
                    return orjson.loads(data)
                else:
                    return data
            else:
                self.logger.warning("No se encontraron datos en window.rapidskins_scraped_data")
                return []
                
        except Exception as e:
            self.logger.error(f"Error al obtener datos: {e}")
            return []
    
    def _save_data_to_file(self, data: List[Dict]) -> bool:
        """
        Guarda los datos extraídos en el archivo JSON especificado
        
        Args:
            data: Lista de items a guardar
        
        Returns:
            True si se guardó exitosamente, False en caso contrario
        """
        try:
            # Crear estructura de datos con metadata
            output_data = {
                "timestamp": datetime.now().isoformat(),
                "platform": "RapidSkins",
                "url": self.rapidskins_url,
                "total_items": len(data),
                "items": data
            }
            
            # Guardar en archivo
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Datos guardados exitosamente en: {self.output_file}")
            self.logger.info(f"Total de items guardados: {len(data)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error al guardar datos en archivo: {e}")
            return False
    
    def parse_response(self, response) -> List[Dict]:
        """
        No se usa en RapidSkins, el parsing se hace en fetch_data
        """
        pass
    
    def fetch_data(self) -> List[Dict]:
        """
        Obtiene datos de RapidSkins usando ChromeDriver y Tampermonkey
        Migrado completamente desde BOT-vCSGO-Beta
        
        Returns:
            Lista de items obtenidos
        """
        self.logger.info("Obteniendo datos de RapidSkins usando ChromeDriver...")

        
        driver = None
        try:
            # Iniciar ChromeDriver
            self.logger.info("Iniciando ChromeDriver con perfil personalizado...")
            driver = self._configure_chromedriver()
            
            if not driver:
                self.logger.error("No se pudo iniciar ChromeDriver")
                return []
            
            # Esperar estabilización
            time.sleep(3)
            
            # Navegar a RapidSkins
            self.logger.info(f"Navegando a {self.rapidskins_url}...")
            self._navigate_to_rapidskins(driver)
            
            # Esperar que Tampermonkey se cargue
            self.logger.info("Esperando que se cargue Tampermonkey...")
            time.sleep(5)
            
            # Esperar extracción completa
            if self._wait_for_tampermonkey_completion(driver):
                # Obtener datos extraídos
                self.logger.info("Obteniendo datos extraídos...")
                items = self._get_tampermonkey_data(driver)
                
                if items:
                    # Formatear para el sistema
                    unique_items = {}
                    for item in items:
                        item_name = item.get("Item", "")
                        if item_name not in unique_items:
                            unique_items[item_name] = {
                                "Item": item_name,
                                "Price": float(item.get("Price", 0)),
                                "Platform": "RapidSkins",
                                "URL": "https://rapidskins.com/market"
                            }

                    formatted_items = list(unique_items.values())
                    
                    self.logger.info(f"Total items obtenidos: {len(formatted_items)}")
                    
                    # Guardar datos en archivo
                    if self._save_data_to_file(formatted_items):
                        self.logger.info("✅ Datos guardados exitosamente")
                    else:
                        self.logger.warning("⚠️ Error al guardar datos en archivo")
                    
                    return formatted_items
                else:
                    self.logger.warning("No se obtuvieron datos del script de Tampermonkey")
                    return []
            else:
                self.logger.error("Timeout: El script de Tampermonkey no completó la extracción")
                return []
                
        except Exception as e:
            self.logger.error(f"Error general en RapidSkins: {e}")
            return []
        
        finally:
            # Cerrar navegador
            if driver:
                self.logger.info("Cerrando ChromeDriver...")
                try:
                    driver.quit()
                except:
                    pass
                time.sleep(2)


def main():
    """
    Función principal para ejecutar el scraper
    """
    # Crear y ejecutar scraper
    scraper = RapidskinsScraper(use_proxy=False)
    
    try:
        # Ejecutar una vez para prueba
        print("=== Ejecutando RapidSkins Scraper V2 (con Selenium + ChromeDriver) ===")
        print("NOTA: Funcionalidad completa migrada desde BOT-vCSGO-Beta")
        print("NOTA: Sin uso de API RustSkins - datos se guardan en \\data\\rapidskins_data.json")
        
        data = scraper.run_once()
        
        print(f"\n✅ Scraper completado:")
        print(f"   - Items obtenidos: {len(data)}")
        print(f"   - Archivo guardado: {scraper.output_file}")
        print(f"   - Estadísticas: {scraper.get_stats()}")
        
        if data:
            print(f"\n📋 Primeros 3 items:")
            for item in data[:3]:
                print(f"   - {item['Item']}: ${item['Price']}")
                
        else:
            print("\n⚠️  No se obtuvieron datos")
            print("   Verificar que Tampermonkey esté instalado y configurado en el perfil de Chrome")
        
        # Opción para ejecutar en bucle
        if data:
            run_forever = input("\n¿Ejecutar en bucle infinito? (y/N): ").lower() == 'y'
            if run_forever:
                print("Iniciando bucle infinito... (Ctrl+C para detener)")
                scraper.run_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        # Limpiar recursos
        scraper.session.close()


if __name__ == "__main__":
    main()