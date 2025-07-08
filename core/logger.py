"""
Sistema de logging unificado para BOT-vCSGO-Beta V2

Funcionalidades:
- Logging centralizado con configuración desde config manager
- Rotación automática de logs
- Diferentes niveles por scraper
- Formateo personalizado
- Logging tanto a consola como a archivo
- Filtros para información sensible
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import threading

from .config_manager import get_config_manager

class SensitiveDataFilter(logging.Filter):
    """
    Filtro para remover información sensible de los logs
    """
    
    SENSITIVE_PATTERNS = [
        'api_key', 'password', 'token', 'secret', 'auth',
        'bearer', 'authorization'
    ]
    
    def filter(self, record):
        """
        Filtra registros que contienen información sensible
        
        Args:
            record: Registro de log
            
        Returns:
            bool: True si el registro debe pasar
        """
        message = str(record.getMessage()).lower()
        
        # Verificar si contiene patrones sensibles
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in message:
                # Sanitizar el mensaje
                record.msg = self._sanitize_message(str(record.msg))
                break
        
        return True
    
    def _sanitize_message(self, message: str) -> str:
        """
        Sanitiza un mensaje reemplazando información sensible
        
        Args:
            message: Mensaje original
            
        Returns:
            Mensaje sanitizado
        """
        # Reemplazar patrones comunes de API keys
        import re
        
        # Patrones para diferentes tipos de tokens
        patterns = [
            (r'(api_key["\s]*[:=]["\s]*)[^"\s,}]+', r'\1[REDACTED]'),
            (r'(token["\s]*[:=]["\s]*)[^"\s,}]+', r'\1[REDACTED]'),
            (r'(bearer\s+)[^\s,}]+', r'\1[REDACTED]'),
            (r'(authorization["\s]*[:=]["\s]*)[^"\s,}]+', r'\1[REDACTED]'),
        ]
        
        sanitized = message
        for pattern, replacement in patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized

class ScraperLogger:
    """
    Logger específico para scrapers con configuración centralizada
    """
    
    def __init__(self, scraper_name: str, config_manager=None):
        """
        Inicializa el logger para un scraper específico
        
        Args:
            scraper_name: Nombre del scraper
            config_manager: Gestor de configuración (opcional)
        """
        self.scraper_name = scraper_name
        self.config_manager = config_manager or get_config_manager()
        
        # Obtener configuración de logging
        self.log_config = self.config_manager.get_logging_config()
        
        # Crear logger específico
        self.logger = logging.getLogger(f"scraper.{scraper_name}")
        
        # Configurar si no está configurado
        if not self.logger.handlers:
            self._setup_logger()
    
    def _setup_logger(self):
        """Configura el logger con handlers y formatters"""
        
        # Limpiar handlers existentes
        self.logger.handlers.clear()
        
        # Configurar nivel
        level = getattr(logging, self.log_config.get('level', 'INFO').upper())
        self.logger.setLevel(level)
        
        # Crear formatter
        formatter = logging.Formatter(
            self.log_config.get(
                'format', 
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        
        # Handler para consola (si está habilitado)
        if self.log_config.get('console_output', True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(level)
            
            # Agregar filtro de datos sensibles si está habilitado
            if self.log_config.get('sanitize_logs', True):
                console_handler.addFilter(SensitiveDataFilter())
            
            self.logger.addHandler(console_handler)
        
        # Handler para archivo (si está habilitado)
        if self.log_config.get('save_to_file', True):
            self._setup_file_handler(formatter, level)
        
        # Evitar propagación al root logger
        self.logger.propagate = False
    
    def _setup_file_handler(self, formatter, level):
        """
        Configura el handler de archivo con rotación
        
        Args:
            formatter: Formateador de logs
            level: Nivel de logging
        """
        # Crear directorio de logs si no existe
        logs_dir = Path(__file__).parent.parent / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # Archivo específico del scraper
        log_file = logs_dir / f"scraper_{self.scraper_name}.log"
        
        # Configuración de rotación
        rotation_config = self.log_config.get('rotation', {})
        
        if rotation_config.get('enabled', True):
            # Handler con rotación
            max_bytes = rotation_config.get('max_size_mb', 10) * 1024 * 1024
            backup_count = rotation_config.get('backup_count', 5)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
        else:
            # Handler simple
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
        
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        
        # Agregar filtro de datos sensibles
        if self.log_config.get('sanitize_logs', True):
            file_handler.addFilter(SensitiveDataFilter())
        
        self.logger.addHandler(file_handler)
    
    def get_logger(self) -> logging.Logger:
        """
        Obtiene el logger configurado
        
        Returns:
            Logger configurado
        """
        return self.logger

class UnifiedLogger:
    """
    Sistema de logging unificado para toda la aplicación
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Inicializa el sistema de logging unificado"""
        if hasattr(self, '_initialized'):
            return
        
        self.config_manager = get_config_manager()
        self.scraper_loggers: Dict[str, ScraperLogger] = {}
        self._setup_root_logger()
        self._initialized = True
    
    def _setup_root_logger(self):
        """Configura el logger raíz de la aplicación"""
        log_config = self.config_manager.get_logging_config()
        
        # Configurar logger raíz
        root_logger = logging.getLogger('bot_v2')
        root_logger.setLevel(getattr(logging, log_config.get('level', 'INFO').upper()))
        
        # Limpiar handlers existentes
        root_logger.handlers.clear()
        
        # Formatter
        formatter = logging.Formatter(
            log_config.get(
                'format',
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        
        # Handler de consola
        if log_config.get('console_output', True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.addFilter(SensitiveDataFilter())
            root_logger.addHandler(console_handler)
        
        # Handler de archivo principal
        if log_config.get('save_to_file', True):
            logs_dir = Path(__file__).parent.parent / "logs"
            logs_dir.mkdir(exist_ok=True)
            
            main_log_file = logs_dir / log_config.get('file_path', 'bot_v2.log').split('/')[-1]
            
            file_handler = logging.FileHandler(main_log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            file_handler.addFilter(SensitiveDataFilter())
            root_logger.addHandler(file_handler)
    
    def get_scraper_logger(self, scraper_name: str) -> logging.Logger:
        """
        Obtiene un logger específico para un scraper
        
        Args:
            scraper_name: Nombre del scraper
            
        Returns:
            Logger configurado para el scraper
        """
        if scraper_name not in self.scraper_loggers:
            self.scraper_loggers[scraper_name] = ScraperLogger(
                scraper_name, 
                self.config_manager
            )
        
        return self.scraper_loggers[scraper_name].get_logger()
    
    def get_main_logger(self) -> logging.Logger:
        """
        Obtiene el logger principal de la aplicación
        
        Returns:
            Logger principal
        """
        return logging.getLogger('bot_v2')
    
    def log_scraper_stats(self, scraper_name: str, stats: Dict[str, Any]):
        """
        Registra estadísticas de un scraper de forma estructurada
        
        Args:
            scraper_name: Nombre del scraper
            stats: Estadísticas del scraper
        """
        logger = self.get_scraper_logger(scraper_name)
        
        # Formatear estadísticas
        stats_msg = (
            f"Estadísticas - "
            f"Requests: {stats.get('requests_made', 0)}, "
            f"Fallos: {stats.get('requests_failed', 0)}, "
            f"Items: {stats.get('items_fetched', 0)}, "
            f"Éxito: {stats.get('success_rate', 0):.1f}%"
        )
        
        if stats.get('cache_hits', 0) > 0:
            stats_msg += f", Cache hits: {stats['cache_hits']}"
        
        logger.info(stats_msg)
    
    def log_performance_metrics(self, scraper_name: str, metrics: Dict[str, Any]):
        """
        Registra métricas de rendimiento
        
        Args:
            scraper_name: Nombre del scraper
            metrics: Métricas de rendimiento
        """
        logger = self.get_scraper_logger(scraper_name)
        
        perf_msg = (
            f"Rendimiento - "
            f"Tiempo respuesta: {metrics.get('response_time', 0):.2f}s, "
            f"Items/segundo: {metrics.get('items_per_second', 0):.2f}"
        )
        
        if metrics.get('memory_usage'):
            perf_msg += f", Memoria: {metrics['memory_usage']:.1f}MB"
        
        logger.debug(perf_msg)

# Instancia global singleton
_unified_logger = None

def get_unified_logger() -> UnifiedLogger:
    """
    Obtiene la instancia singleton del sistema de logging unificado
    
    Returns:
        Instancia de UnifiedLogger
    """
    global _unified_logger
    
    if _unified_logger is None:
        _unified_logger = UnifiedLogger()
    
    return _unified_logger

def get_scraper_logger(scraper_name: str) -> logging.Logger:
    """
    Función de conveniencia para obtener un logger de scraper
    
    Args:
        scraper_name: Nombre del scraper
        
    Returns:
        Logger configurado
    """
    return get_unified_logger().get_scraper_logger(scraper_name)

def get_main_logger() -> logging.Logger:
    """
    Función de conveniencia para obtener el logger principal
    
    Returns:
        Logger principal
    """
    return get_unified_logger().get_main_logger()