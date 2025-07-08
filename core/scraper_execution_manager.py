"""
Scraper Execution Manager - BOT-vCSGO-Beta V2

Gestor de ejecución de scrapers con soporte para:
- Ejecución en hilos separados
- Control de estado de scrapers
- Gestión de configuraciones
- Monitoreo en tiempo real
"""

import sys
import time
import threading
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future
from enum import Enum

# Agregar paths necesarios
sys.path.append(str(Path(__file__).parent.parent))

from core.logger import get_scraper_logger
from core.config_manager import get_config_manager

try:
    from core.base_scraper import BaseScraper
except ImportError:
    BaseScraper = None


class ScraperState(Enum):
    """Estados posibles de un scraper"""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    FINISHED = "finished"


class ScraperExecutionInfo:
    """Información de ejecución de un scraper"""
    
    def __init__(self, scraper_name: str, config: Dict[str, Any]):
        self.scraper_name = scraper_name
        self.config = config.copy()
        self.state = ScraperState.IDLE
        self.thread = None
        self.future = None
        self.start_time = None
        self.end_time = None
        self.error_message = None
        self.items_scraped = 0
        self.last_activity = None
        self.execution_count = 0
        self.lock = threading.Lock()
    
    def update_state(self, new_state: ScraperState, error_message: str = None):
        """Actualiza el estado del scraper"""
        with self.lock:
            old_state = self.state
            self.state = new_state
            self.last_activity = datetime.now()
            
            if new_state == ScraperState.STARTING:
                self.start_time = datetime.now()
                self.execution_count += 1
                self.error_message = None
                self.items_scraped = 0
            elif new_state in [ScraperState.STOPPED, ScraperState.FINISHED, ScraperState.ERROR]:
                self.end_time = datetime.now()
                if error_message:
                    self.error_message = error_message
    
    def get_runtime(self) -> Optional[float]:
        """Retorna el tiempo de ejecución en segundos"""
        if self.start_time:
            end_time = self.end_time or datetime.now()
            return (end_time - self.start_time).total_seconds()
        return None
    
    def get_info_dict(self) -> Dict[str, Any]:
        """Retorna información como diccionario"""
        return {
            "scraper_name": self.scraper_name,
            "state": self.state.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "runtime": self.get_runtime(),
            "items_scraped": self.items_scraped,
            "execution_count": self.execution_count,
            "error_message": self.error_message,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None
        }


class ScraperExecutionManager:
    """
    Manager principal para la ejecución de scrapers
    
    Características:
    - Ejecución concurrente de múltiples scrapers
    - Control de estado en tiempo real
    - Gestión de configuraciones dinámicas
    - Sistema de callbacks para UI
    - Manejo de errores robusto
    """
    
    def __init__(self, max_concurrent_scrapers: int = 8):
        self.logger = get_scraper_logger("ScraperExecutionManager")
        self.config_manager = get_config_manager()
        
        # Estado interno
        self.scrapers_info: Dict[str, ScraperExecutionInfo] = {}
        self.scrapers_instances: Dict[str, Any] = {}  # Instancias activas de scrapers
        
        # Thread pool para ejecución
        self.max_concurrent = max_concurrent_scrapers
        self.thread_pool = ThreadPoolExecutor(max_workers=max_concurrent_scrapers, thread_name_prefix="ScraperExec")
        
        # Callbacks para notificaciones
        self.state_change_callbacks: List[Callable] = []
        self.progress_callbacks: List[Callable] = []
        
        # Directorio de scrapers
        self.scrapers_dir = Path(__file__).parent.parent / "scrapers"
        
        # Lock para thread safety
        self.manager_lock = threading.Lock()
        
        self.logger.info(f"ScraperExecutionManager inicializado con {max_concurrent_scrapers} workers máximos")
    
    def add_state_change_callback(self, callback: Callable[[str, ScraperState, Optional[str]], None]):
        """Agrega callback para cambios de estado"""
        self.state_change_callbacks.append(callback)
    
    def add_progress_callback(self, callback: Callable[[str, int], None]):
        """Agrega callback para progreso"""
        self.progress_callbacks.append(callback)
    
    def _notify_state_change(self, scraper_name: str, new_state: ScraperState, error_message: str = None):
        """Notifica cambio de estado a callbacks"""
        for callback in self.state_change_callbacks:
            try:
                callback(scraper_name, new_state, error_message)
            except Exception as e:
                self.logger.error(f"Error en callback de estado: {e}")
    
    def _notify_progress(self, scraper_name: str, items_count: int):
        """Notifica progreso a callbacks"""
        for callback in self.progress_callbacks:
            try:
                callback(scraper_name, items_count)
            except Exception as e:
                self.logger.error(f"Error en callback de progreso: {e}")
    
    def _load_scraper_class(self, scraper_name: str) -> Optional[type]:
        """Carga dinámicamente la clase del scraper"""
        try:
            scraper_file = self.scrapers_dir / f"{scraper_name}.py"
            if not scraper_file.exists():
                self.logger.error(f"Archivo de scraper no encontrado: {scraper_file}")
                return None
            
            # Importar módulo dinámicamente
            spec = importlib.util.spec_from_file_location(scraper_name, scraper_file)
            if spec is None or spec.loader is None:
                self.logger.error(f"No se pudo cargar el spec para {scraper_name}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Buscar clase del scraper (típicamente PlatformScraper)
            scraper_class_name = f"{scraper_name.replace('_scraper', '').title()}Scraper"
            
            # Buscar por nombres comunes
            possible_names = [
                scraper_class_name,
                f"{scraper_name.replace('_scraper', '').title()}",
                "Scraper",
                "MainScraper"
            ]
            
            for class_name in possible_names:
                if hasattr(module, class_name):
                    scraper_class = getattr(module, class_name)
                    self.logger.info(f"Clase del scraper encontrada: {class_name} para {scraper_name}")
                    return scraper_class
            
            # Buscar cualquier clase que herede de BaseScraper
            if BaseScraper:
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, BaseScraper) and 
                        attr != BaseScraper):
                        self.logger.info(f"Clase del scraper encontrada por herencia: {attr_name} para {scraper_name}")
                        return attr
            
            self.logger.error(f"No se encontró clase de scraper válida en {scraper_name}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error cargando scraper {scraper_name}: {e}")
            return None
    
    def _create_scraper_instance(self, scraper_name: str, config: Dict[str, Any]) -> Optional[Any]:
        """Crea una instancia del scraper"""
        try:
            scraper_class = self._load_scraper_class(scraper_name)
            if not scraper_class:
                return None
            
            # Parámetros básicos para inicialización
            init_params = {
                'use_proxy': config.get('use_proxy', False),
                'timeout': config.get('timeout', 30),
                'max_retries': config.get('max_retries', 3)
            }
            
            # Crear instancia
            instance = scraper_class(**init_params)
            
            # Configurar parámetros adicionales si el scraper los soporta
            if hasattr(instance, 'set_request_delay'):
                instance.set_request_delay(config.get('request_delay', 1.0))
            
            if hasattr(instance, 'set_user_agent') and config.get('user_agent'):
                instance.set_user_agent(config.get('user_agent'))
            
            if hasattr(instance, 'set_headers') and config.get('headers'):
                instance.set_headers(config.get('headers'))
            
            return instance
            
        except Exception as e:
            self.logger.error(f"Error creando instancia de {scraper_name}: {e}")
            return None
    
    def _execute_scraper_worker(self, scraper_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Worker que ejecuta un scraper en un hilo separado"""
        execution_info = self.scrapers_info[scraper_name]
        
        try:
            # Cambiar estado a STARTING
            execution_info.update_state(ScraperState.STARTING)
            self._notify_state_change(scraper_name, ScraperState.STARTING)
            
            # Crear instancia del scraper
            scraper_instance = self._create_scraper_instance(scraper_name, config)
            if not scraper_instance:
                raise Exception(f"No se pudo crear instancia de {scraper_name}")
            
            # Guardar instancia
            with self.manager_lock:
                self.scrapers_instances[scraper_name] = scraper_instance
            
            # Cambiar estado a RUNNING
            execution_info.update_state(ScraperState.RUNNING)
            self._notify_state_change(scraper_name, ScraperState.RUNNING)
            
            # Ejecutar scraper
            if hasattr(scraper_instance, 'scrape'):
                # Método estándar de scraping
                result = scraper_instance.scrape()
            elif hasattr(scraper_instance, 'run'):
                # Método alternativo
                result = scraper_instance.run()
            elif hasattr(scraper_instance, 'execute'):
                # Otro método alternativo
                result = scraper_instance.execute()
            else:
                raise Exception(f"Scraper {scraper_name} no tiene método de ejecución conocido")
            
            # Actualizar progreso si hay resultados
            if isinstance(result, (list, dict)):
                items_count = len(result) if isinstance(result, list) else 1
                execution_info.items_scraped = items_count
                self._notify_progress(scraper_name, items_count)
            
            # Estado final
            execution_info.update_state(ScraperState.FINISHED)
            self._notify_state_change(scraper_name, ScraperState.FINISHED)
            
            return {
                'status': 'success',
                'result': result,
                'items_count': execution_info.items_scraped
            }
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error ejecutando {scraper_name}: {error_msg}")
            
            execution_info.update_state(ScraperState.ERROR, error_msg)
            self._notify_state_change(scraper_name, ScraperState.ERROR, error_msg)
            
            return {
                'status': 'error',
                'error': error_msg
            }
        
        finally:
            # Limpiar instancia
            with self.manager_lock:
                if scraper_name in self.scrapers_instances:
                    del self.scrapers_instances[scraper_name]
    
    def start_scraper(self, scraper_name: str, config: Dict[str, Any]) -> bool:
        """
        Inicia un scraper con la configuración dada
        
        Args:
            scraper_name: Nombre del scraper
            config: Configuración para el scraper
            
        Returns:
            True si se inició correctamente
        """
        try:
            with self.manager_lock:
                # Verificar si ya está ejecutándose
                if scraper_name in self.scrapers_info:
                    current_state = self.scrapers_info[scraper_name].state
                    if current_state in [ScraperState.RUNNING, ScraperState.STARTING]:
                        self.logger.warning(f"Scraper {scraper_name} ya está ejecutándose")
                        return False
                
                # Crear info de ejecución
                self.scrapers_info[scraper_name] = ScraperExecutionInfo(scraper_name, config)
                
                # Verificar si está habilitado
                if not config.get('enabled', True):
                    self.logger.info(f"Scraper {scraper_name} está deshabilitado")
                    return False
                
                # Enviar a thread pool
                future = self.thread_pool.submit(self._execute_scraper_worker, scraper_name, config)
                self.scrapers_info[scraper_name].future = future
                
                self.logger.info(f"Scraper {scraper_name} enviado a ejecución")
                return True
                
        except Exception as e:
            self.logger.error(f"Error iniciando scraper {scraper_name}: {e}")
            return False
    
    def stop_scraper(self, scraper_name: str) -> bool:
        """
        Detiene un scraper en ejecución
        
        Args:
            scraper_name: Nombre del scraper
            
        Returns:
            True si se detuvo correctamente
        """
        try:
            with self.manager_lock:
                if scraper_name not in self.scrapers_info:
                    self.logger.warning(f"Scraper {scraper_name} no está registrado")
                    return False
                
                execution_info = self.scrapers_info[scraper_name]
                
                # Verificar estado
                if execution_info.state not in [ScraperState.RUNNING, ScraperState.STARTING]:
                    self.logger.warning(f"Scraper {scraper_name} no está ejecutándose")
                    return False
                
                # Cambiar estado
                execution_info.update_state(ScraperState.STOPPING)
                self._notify_state_change(scraper_name, ScraperState.STOPPING)
                
                # Intentar detener la instancia si tiene método stop
                if scraper_name in self.scrapers_instances:
                    instance = self.scrapers_instances[scraper_name]
                    if hasattr(instance, 'stop'):
                        instance.stop()
                    elif hasattr(instance, 'shutdown'):
                        instance.shutdown()
                
                # Cancelar future si es posible
                if execution_info.future and not execution_info.future.done():
                    execution_info.future.cancel()
                
                # Actualizar estado final
                execution_info.update_state(ScraperState.STOPPED)
                self._notify_state_change(scraper_name, ScraperState.STOPPED)
                
                self.logger.info(f"Scraper {scraper_name} detenido")
                return True
                
        except Exception as e:
            self.logger.error(f"Error deteniendo scraper {scraper_name}: {e}")
            return False
    
    def get_scraper_state(self, scraper_name: str) -> Optional[ScraperState]:
        """Retorna el estado actual de un scraper"""
        if scraper_name in self.scrapers_info:
            return self.scrapers_info[scraper_name].state
        return None
    
    def get_scraper_info(self, scraper_name: str) -> Optional[Dict[str, Any]]:
        """Retorna información completa de un scraper"""
        if scraper_name in self.scrapers_info:
            return self.scrapers_info[scraper_name].get_info_dict()
        return None
    
    def get_all_scrapers_info(self) -> Dict[str, Dict[str, Any]]:
        """Retorna información de todos los scrapers"""
        return {
            name: info.get_info_dict()
            for name, info in self.scrapers_info.items()
        }
    
    def get_running_scrapers(self) -> List[str]:
        """Retorna lista de scrapers actualmente ejecutándose"""
        return [
            name for name, info in self.scrapers_info.items()
            if info.state == ScraperState.RUNNING
        ]
    
    def stop_all_scrapers(self) -> int:
        """Detiene todos los scrapers en ejecución"""
        running_scrapers = self.get_running_scrapers()
        stopped_count = 0
        
        for scraper_name in running_scrapers:
            if self.stop_scraper(scraper_name):
                stopped_count += 1
        
        self.logger.info(f"Detenidos {stopped_count} de {len(running_scrapers)} scrapers")
        return stopped_count
    
    def cleanup(self):
        """Limpia recursos del manager"""
        try:
            self.stop_all_scrapers()
            self.thread_pool.shutdown(wait=True, timeout=30)
            self.scrapers_info.clear()
            self.scrapers_instances.clear()
            self.logger.info("ScraperExecutionManager limpiado correctamente")
        except Exception as e:
            self.logger.error(f"Error en cleanup: {e}")


# Instancia global
_scraper_execution_manager = None


def get_scraper_execution_manager(max_concurrent: int = 8) -> ScraperExecutionManager:
    """Retorna instancia global del manager"""
    global _scraper_execution_manager
    if _scraper_execution_manager is None:
        _scraper_execution_manager = ScraperExecutionManager(max_concurrent)
    return _scraper_execution_manager