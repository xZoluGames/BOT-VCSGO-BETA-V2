"""
ConfigManager - Sistema de gestión de configuración para BOT-vCSGO-Beta V2

Funcionalidades:
- Carga configuraciones desde archivos JSON
- Soporte para variables de entorno
- Configuraciones por scraper
- Gestión de API keys
- Valores por defecto robustos
- Validación de configuraciones
"""

import os
import json
import orjson
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from functools import lru_cache

class ConfigManager:
    """
    Gestor centralizado de configuración para BOT-vCSGO-Beta V2
    
    Maneja la carga y validación de configuraciones desde:
    - config/settings.json (configuración principal)
    - config/scrapers.json (configuración de scrapers)
    - config/api_keys.json (claves API)
    - Variables de entorno (sobrescribe archivos)
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Inicializa el gestor de configuración
        
        Args:
            config_dir: Directorio de configuración (None = auto-detectar)
        """
        self.logger = logging.getLogger("config_manager")
        
        # Detectar directorio de configuración
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "config"
        
        self.config_dir = Path(config_dir)
        
        # Asegurar que existe el directorio
        self.config_dir.mkdir(exist_ok=True)
        
        # Archivos de configuración
        self.settings_file = self.config_dir / "settings.json"
        self.scrapers_file = self.config_dir / "scrapers.json"
        self.api_keys_file = self.config_dir / "api_keys.json"
        
        # Cache de configuraciones
        self._settings = None
        self._scrapers = None
        self._api_keys = None
        
        self.logger.info(f"ConfigManager inicializado con directorio: {self.config_dir}")
    
    @lru_cache(maxsize=1)
    def get_settings(self) -> Dict[str, Any]:
        """
        Obtiene la configuración principal del sistema
        
        Returns:
            Diccionario con configuración principal
        """
        if self._settings is None:
            self._settings = self._load_json_config(
                self.settings_file,
                self._get_default_settings()
            )
            
            # Aplicar overrides de variables de entorno
            self._apply_env_overrides(self._settings)
            
        return self._settings
    
    @lru_cache(maxsize=1)
    def get_scrapers_config(self) -> Dict[str, Any]:
        """
        Obtiene la configuración de scrapers
        
        Returns:
            Diccionario con configuración de scrapers
        """
        if self._scrapers is None:
            self._scrapers = self._load_json_config(
                self.scrapers_file,
                self._get_default_scrapers()
            )
            
        return self._scrapers
    
    @lru_cache(maxsize=1)
    def get_api_keys(self) -> Dict[str, Any]:
        """
        Obtiene las claves API del sistema
        
        Returns:
            Diccionario con claves API
        """
        if self._api_keys is None:
            self._api_keys = self._load_json_config(
                self.api_keys_file,
                self._get_default_api_keys()
            )
            
            # Aplicar claves desde variables de entorno
            self._apply_api_key_env_overrides(self._api_keys)
            
        return self._api_keys
    
    def get_scraper_config(self, platform: str) -> Dict[str, Any]:
        """
        Obtiene la configuración específica de un scraper
        
        Args:
            platform: Nombre de la plataforma
            
        Returns:
            Configuración del scraper con valores por defecto
        """
        scrapers_config = self.get_scrapers_config()
        platform_lower = platform.lower()
        
        # Obtener configuración específica o usar valores por defecto
        config = scrapers_config.get(platform_lower, {})
        
        # Aplicar configuración global si existe
        global_settings = scrapers_config.get('global_settings', {})
        
        # Mergear con valores por defecto
        default_config = {
            'enabled': True,
            'interval_seconds': 60,
            'timeout_seconds': 30,
            'max_retries': 5,
            'use_proxy': False,
            'priority': 'medium',
            'headers': {},
            'api_url': '',
            'description': f'Scraper para {platform}'
        }
        
        # Mergear configuraciones (prioridad: específica > global > default)
        final_config = {**default_config, **global_settings, **config}
        
        return final_config
    
    def get_api_key(self, platform: str) -> Optional[str]:
        """
        Obtiene la clave API para una plataforma específica
        
        Args:
            platform: Nombre de la plataforma
            
        Returns:
            Clave API o None si no existe
        """
        api_keys = self.get_api_keys()
        platform_lower = platform.lower()
        
        # Buscar en configuración
        if platform_lower in api_keys:
            key_config = api_keys[platform_lower]
            if isinstance(key_config, dict):
                return key_config.get('api_key')
            return key_config
        
        # Buscar en variables de entorno
        env_var = f"BOT_API_KEY_{platform.upper()}"
        return os.getenv(env_var)
    
    def get_proxy_config(self) -> Dict[str, Any]:
        """
        Obtiene la configuración de proxy
        
        Returns:
            Configuración de proxy
        """
        settings = self.get_settings()
        return settings.get('proxy', {})
    
    def get_cache_config(self) -> Dict[str, Any]:
        """
        Obtiene la configuración de caché
        
        Returns:
            Configuración de caché
        """
        settings = self.get_settings()
        return settings.get('cache', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Obtiene la configuración de logging
        
        Returns:
            Configuración de logging
        """
        settings = self.get_settings()
        return settings.get('logging', {})
    
    def is_scraper_enabled(self, platform: str) -> bool:
        """
        Verifica si un scraper está habilitado
        
        Args:
            platform: Nombre de la plataforma
            
        Returns:
            True si el scraper está habilitado
        """
        config = self.get_scraper_config(platform)
        return config.get('enabled', True)
    
    def get_scraper_groups(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene los grupos de scrapers definidos
        
        Returns:
            Diccionario con grupos de scrapers
        """
        scrapers_config = self.get_scrapers_config()
        return scrapers_config.get('groups', {})
    
    def get_scrapers_in_group(self, group_name: str) -> List[str]:
        """
        Obtiene la lista de scrapers en un grupo específico
        
        Args:
            group_name: Nombre del grupo
            
        Returns:
            Lista de nombres de scrapers
        """
        groups = self.get_scraper_groups()
        if group_name in groups:
            return groups[group_name].get('scrapers', [])
        return []
    
    def load_proxy_list(self) -> List[str]:
        """
        Carga la lista de proxies desde archivo
        
        Returns:
            Lista de proxies
        """
        proxy_config = self.get_proxy_config()
        proxy_file = proxy_config.get('file_path', 'proxy.txt')
        
        # Buscar archivo de proxy
        proxy_path = self.config_dir.parent / proxy_file
        
        if not proxy_path.exists():
            # Buscar en directorio raíz
            proxy_path = self.config_dir.parent / proxy_file
            
        if not proxy_path.exists():
            self.logger.warning(f"Archivo de proxy no encontrado: {proxy_file}")
            return []
        
        try:
            with open(proxy_path, 'r', encoding='utf-8') as f:
                proxies = [
                    line.strip() 
                    for line in f 
                    if line.strip() and not line.startswith('#')
                ]
            
            self.logger.info(f"Cargados {len(proxies)} proxies desde {proxy_file}")
            return proxies
            
        except Exception as e:
            self.logger.error(f"Error cargando proxies: {e}")
            return []
    
    def _load_json_config(self, file_path: Path, default_config: Dict) -> Dict[str, Any]:
        """
        Carga un archivo de configuración JSON con valores por defecto
        
        Args:
            file_path: Ruta del archivo
            default_config: Configuración por defecto
            
        Returns:
            Configuración cargada
        """
        try:
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    config = orjson.loads(f.read())
                    self.logger.info(f"Configuración cargada desde {file_path}")
                    return config
            else:
                # Crear archivo con configuración por defecto
                self._save_json_config(file_path, default_config)
                self.logger.info(f"Archivo de configuración creado: {file_path}")
                return default_config
                
        except Exception as e:
            self.logger.error(f"Error cargando configuración {file_path}: {e}")
            return default_config
    
    def _save_json_config(self, file_path: Path, config: Dict[str, Any]):
        """
        Guarda un archivo de configuración JSON
        
        Args:
            file_path: Ruta del archivo
            config: Configuración a guardar
        """
        try:
            with open(file_path, 'wb') as f:
                f.write(orjson.dumps(config, option=orjson.OPT_INDENT_2))
        except Exception as e:
            self.logger.error(f"Error guardando configuración {file_path}: {e}")
    
    def _apply_env_overrides(self, settings: Dict[str, Any]):
        """
        Aplica overrides desde variables de entorno
        
        Args:
            settings: Configuración a modificar
        """
        # Proxy
        if os.getenv('BOT_USE_PROXY'):
            settings['proxy']['enabled'] = os.getenv('BOT_USE_PROXY').lower() == 'true'
        
        # Logging level
        if os.getenv('BOT_LOG_LEVEL'):
            settings['logging']['level'] = os.getenv('BOT_LOG_LEVEL')
        
        # Cache
        if os.getenv('BOT_CACHE_ENABLED'):
            settings['cache']['enabled'] = os.getenv('BOT_CACHE_ENABLED').lower() == 'true'
        
        # Database
        if os.getenv('BOT_DATABASE_ENABLED'):
            settings['database']['enabled'] = os.getenv('BOT_DATABASE_ENABLED').lower() == 'true'
    
    def _apply_api_key_env_overrides(self, api_keys: Dict[str, Any]):
        """
        Aplica claves API desde variables de entorno
        
        Args:
            api_keys: Configuración de API keys a modificar
        """
        # Buscar todas las variables de entorno que empiecen con BOT_API_KEY_
        for env_var in os.environ:
            if env_var.startswith('BOT_API_KEY_'):
                platform = env_var.replace('BOT_API_KEY_', '').lower()
                api_key = os.getenv(env_var)
                
                if api_key:
                    api_keys[platform] = {
                        'api_key': api_key,
                        'type': 'bearer',
                        'source': 'environment'
                    }
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Retorna la configuración por defecto del sistema"""
        # Si existe el archivo actual, lo mantenemos como base
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'rb') as f:
                    return orjson.loads(f.read())
            except:
                pass
        
        # Configuración por defecto básica
        return {
            "project": {
                "name": "BOT-vCSGO-Beta V2",
                "version": "2.0.0",
                "description": "Scraper mejorado de CS:GO",
                "author": "ZoluGames",
                "environment": "development"
            },
            "proxy": {
                "enabled": False,
                "rotation_enabled": True,
                "timeout": 10,
                "max_retries": 3,
                "file_path": "proxy.txt",
                "validation_enabled": True
            },
            "cache": {
                "enabled": True,
                "memory_limit_items": 1000,
                "default_ttl_seconds": 300
            },
            "logging": {
                "level": "INFO",
                "save_to_file": True,
                "file_path": "logs/bot_v2.log",
                "console_output": True
            }
        }
    
    def _get_default_scrapers(self) -> Dict[str, Any]:
        """Retorna la configuración por defecto de scrapers"""
        # Si existe el archivo actual, lo mantenemos
        if self.scrapers_file.exists():
            try:
                with open(self.scrapers_file, 'rb') as f:
                    return orjson.loads(f.read())
            except:
                pass
        
        return {
            "waxpeer": {
                "enabled": True,
                "api_url": "https://api.waxpeer.com/v1/prices?game=csgo&minified=0",
                "interval_seconds": 60,
                "priority": "high"
            },
            "skinport": {
                "enabled": True,
                "api_url": "https://api.skinport.com/v1/items?app_id=730&currency=USD",
                "interval_seconds": 60,
                "priority": "high"
            },
            "csdeals": {
                "enabled": True,
                "api_url": "https://cs.deals/API/IPricing/GetLowestPrices/v1?appid=730",
                "interval_seconds": 60,
                "priority": "medium"
            }
        }
    
    def _get_default_api_keys(self) -> Dict[str, Any]:
        """Retorna la configuración por defecto de API keys"""
        return {
            "waxpeer": {
                "api_key": "",
                "type": "bearer",
                "required": False,
                "description": "API key para Waxpeer (opcional)"
            },
            "skinport": {
                "api_key": "",
                "type": "bearer", 
                "required": False,
                "description": "API key para Skinport (opcional)"
            },
            "csdeals": {
                "api_key": "",
                "type": "bearer",
                "required": False,
                "description": "API key para CS.deals (opcional)"
            }
        }
    
    def reload_config(self):
        """Recarga todas las configuraciones desde archivos"""
        self._settings = None
        self._scrapers = None
        self._api_keys = None
        
        # Limpiar cache
        self.get_settings.cache_clear()
        self.get_scrapers_config.cache_clear()
        self.get_api_keys.cache_clear()
        
        self.logger.info("Configuraciones recargadas")


# Instancia global singleton
_config_manager = None

def get_config_manager(config_dir: Optional[Path] = None) -> ConfigManager:
    """
    Obtiene la instancia singleton del gestor de configuración
    
    Args:
        config_dir: Directorio de configuración (solo primera vez)
        
    Returns:
        Instancia de ConfigManager
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir)
    
    return _config_manager