"""
ConfigManager - Sistema de gestión de configuración SEGURO para BOT-vCSGO-Beta V2

Mejoras de seguridad:
- Todas las claves API se cargan desde variables de entorno
- Soporte para archivo .env en desarrollo
- Validación de claves antes de uso
- Sin exposición de secretos en logs
"""

import os
import json
import orjson
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from functools import lru_cache
from dotenv import load_dotenv  # Necesitarás instalar: pip install python-dotenv

class SecureConfigManager:
    """
    Gestor centralizado de configuración SEGURO para BOT-vCSGO-Beta V2
    
    Prioridad de configuración:
    1. Variables de entorno
    2. Archivo .env (solo desarrollo)
    3. Archivos JSON (sin secretos)
    """
    
    def __init__(self, config_dir: Optional[Path] = None, env_file: Optional[str] = None):
        """
        Inicializa el gestor de configuración seguro
        
        Args:
            config_dir: Directorio de configuración (None = auto-detectar)
            env_file: Archivo .env opcional para desarrollo
        """
        self.logger = logging.getLogger("secure_config_manager")
        
        # Cargar variables de entorno desde archivo .env si existe
        if env_file and Path(env_file).exists():
            load_dotenv(env_file)
            self.logger.info(f"Variables de entorno cargadas desde {env_file}")
        else:
            # Buscar .env en el directorio raíz del proyecto
            root_env = Path(__file__).parent.parent / ".env"
            if root_env.exists():
                load_dotenv(root_env)
                self.logger.info("Variables de entorno cargadas desde .env")
        
        # Detectar directorio de configuración
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "config"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Archivos de configuración (sin secretos)
        self.settings_file = self.config_dir / "settings.json"
        self.scrapers_file = self.config_dir / "scrapers.json"
        self.api_keys_template_file = self.config_dir / "api_keys.template.json"
        
        # Cache de configuraciones
        self._settings = None
        self._scrapers = None
        self._api_keys = None
        
        # Validar que no exista el archivo inseguro
        self._check_insecure_files()
        
        self.logger.info(f"SecureConfigManager inicializado con directorio: {self.config_dir}")
    
    def _check_insecure_files(self):
        """Verifica y advierte sobre archivos inseguros"""
        insecure_file = self.config_dir / "api_keys.json"
        if insecure_file.exists():
            self.logger.warning("⚠️ ADVERTENCIA: Encontrado api_keys.json con claves expuestas!")
            self.logger.warning("⚠️ Por favor, elimina este archivo y usa variables de entorno")
            
            # Crear archivo template si no existe
            if not self.api_keys_template_file.exists():
                self._create_api_keys_template()
    
    def _create_api_keys_template(self):
        """Crea un archivo template para documentar las claves necesarias"""
        template = {
            "_instructions": {
                "description": "Este es un archivo TEMPLATE. NO pongas claves reales aquí.",
                "setup": "Configura las claves usando variables de entorno o archivo .env",
                "example_env": [
                    "export WAXPEER_API_KEY=tu_clave_aqui",
                    "export EMPIRE_API_KEY=tu_clave_aqui",
                    "export SHADOWPAY_API_KEY=tu_clave_aqui",
                    "export RUSTSKINS_API_KEY=tu_clave_aqui",
                    "export OCULUS_AUTH_TOKEN=tu_token_aqui",
                    "export OCULUS_ORDER_TOKEN=tu_token_aqui"
                ]
            },
            "platforms": {
                "waxpeer": {"env_var": "WAXPEER_API_KEY", "required": False},
                "empire": {"env_var": "EMPIRE_API_KEY", "required": True},
                "shadowpay": {"env_var": "SHADOWPAY_API_KEY", "required": False},
                "rustskins": {"env_var": "RUSTSKINS_API_KEY", "required": False},
                "skinport": {"env_var": "SKINPORT_API_KEY", "required": False},
                "csdeals": {"env_var": "CSDEALS_API_KEY", "required": False},
                "bitskins": {"env_var": "BITSKINS_API_KEY", "required": False},
                "cstrade": {"env_var": "CSTRADE_API_KEY", "required": False},
                "marketcsgo": {"env_var": "MARKETCSGO_API_KEY", "required": False},
                "tradeit": {"env_var": "TRADEIT_API_KEY", "required": False}
            },
            "proxy": {
                "oculus_auth": {"env_var": "OCULUS_AUTH_TOKEN", "required": True},
                "oculus_order": {"env_var": "OCULUS_ORDER_TOKEN", "required": True}
            }
        }
        
        with open(self.api_keys_template_file, 'wb') as f:
            f.write(orjson.dumps(template, option=orjson.OPT_INDENT_2))
        
        self.logger.info(f"Archivo template creado: {self.api_keys_template_file}")
    
    @lru_cache(maxsize=1)
    def get_api_keys(self) -> Dict[str, Any]:
        """
        Obtiene las claves API del sistema de forma SEGURA
        
        Returns:
            Diccionario con claves API desde variables de entorno
        """
        if self._api_keys is None:
            self._api_keys = self._load_api_keys_from_env()
            
        return self._api_keys
    
    def _load_api_keys_from_env(self) -> Dict[str, Any]:
        """Carga todas las claves API desde variables de entorno"""
        api_keys = {}
        
        # Mapeo de plataformas a variables de entorno
        platform_env_mapping = {
            'waxpeer': 'WAXPEER_API_KEY',
            'empire': 'EMPIRE_API_KEY',
            'shadowpay': 'SHADOWPAY_API_KEY',
            'rustskins': 'RUSTSKINS_API_KEY',
            'skinport': 'SKINPORT_API_KEY',
            'csdeals': 'CSDEALS_API_KEY',
            'bitskins': 'BITSKINS_API_KEY',
            'cstrade': 'CSTRADE_API_KEY',
            'marketcsgo': 'MARKETCSGO_API_KEY',
            'tradeit': 'TRADEIT_API_KEY',
            'steamout': 'STEAMOUT_API_KEY',
            'lisskins': 'LISSKINS_API_KEY',
            'white': 'WHITE_API_KEY'
        }
        
        # Cargar claves de plataformas
        for platform, env_var in platform_env_mapping.items():
            api_key = os.getenv(env_var)
            if api_key:
                api_keys[platform] = {
                    'api_key': api_key,
                    'type': 'bearer',  # Por defecto
                    'active': True
                }
                self.logger.debug(f"Clave API cargada para {platform} desde {env_var}")
        
        # Configuración especial para proxy Oculus
        oculus_auth = os.getenv('OCULUS_AUTH_TOKEN')
        oculus_order = os.getenv('OCULUS_ORDER_TOKEN')
        
        if oculus_auth and oculus_order:
            api_keys['_proxy_config'] = {
                'oculus_auth_token': oculus_auth,
                'oculus_order_token': oculus_order,
                'whitelist_ip': os.getenv('OCULUS_WHITELIST_IP', '').split(',') if os.getenv('OCULUS_WHITELIST_IP') else []
            }
            self.logger.debug("Configuración de proxy Oculus cargada")
        
        # Validar claves requeridas
        required_keys = ['empire']  # Empire es requerida según tu config
        missing_keys = [key for key in required_keys if key not in api_keys]
        
        if missing_keys:
            self.logger.warning(f"⚠️ Claves API requeridas faltantes: {missing_keys}")
            self.logger.warning("Configura las variables de entorno necesarias")
        
        return api_keys
    
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
        
        if platform_lower in api_keys:
            key_config = api_keys[platform_lower]
            if isinstance(key_config, dict):
                return key_config.get('api_key')
            return key_config
        
        return None
    
    def get_proxy_config(self) -> Dict[str, Any]:
        """
        Obtiene la configuración de proxy de forma segura
        
        Returns:
            Configuración de proxy con credenciales desde env
        """
        api_keys = self.get_api_keys()
        proxy_config = api_keys.get('_proxy_config', {})
        
        # Combinar con configuración de settings si existe
        settings = self.get_settings()
        base_proxy_config = settings.get('proxy', {})
        
        # Sobrescribir con valores seguros
        base_proxy_config.update({
            'oculus_auth_token': proxy_config.get('oculus_auth_token'),
            'oculus_order_token': proxy_config.get('oculus_order_token'),
            'whitelist_ip': proxy_config.get('whitelist_ip', [])
        })
        
        return base_proxy_config
    
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
        
        config = scrapers_config.get(platform_lower, {})
        global_settings = scrapers_config.get('global_settings', {})
        
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
    
    def _load_json_config(self, file_path: Path, default_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Carga un archivo de configuración JSON
        
        Args:
            file_path: Ruta del archivo
            default_config: Configuración por defecto
            
        Returns:
            Configuración cargada o por defecto
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
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Retorna la configuración por defecto del sistema"""
        return {
            "project": {
                "name": "BOT-vCSGO-Beta V2",
                "version": "2.0.0",
                "description": "Scraper simplificado de CS:GO para uso personal",
                "author": "ZoluGames",
                "environment": "development"
            },
            "scrapers": {
                "default_interval": 60,
                "default_timeout": 30,
                "default_retries": 5,
                "use_proxy_by_default": False,
                "parallel_execution": False
            },
            "cache": {
                "enabled": True,
                "memory_limit_items": 1000,
                "default_ttl_seconds": 300
            },
            "proxy": {
                "enabled": False,
                "rotation_enabled": True,
                "timeout": 10,
                "max_retries": 3
            },
            "logging": {
                "level": "INFO",
                "save_to_file": True,
                "console_output": True
            }
        }
    
    def _get_default_scrapers(self) -> Dict[str, Any]:
        """Retorna la configuración por defecto de scrapers"""
        return {
            "global_settings": {
                "enabled": True,
                "use_proxy": False,
                "timeout_seconds": 30,
                "max_retries": 5
            },
            "waxpeer": {
                "enabled": True,
                "api_url": "https://api.waxpeer.com/v1/prices",
                "priority": "high"
            },
            "empire": {
                "enabled": True,
                "api_url": "https://csgoempire.com/api/v2/trading/items",
                "priority": "high",
                "required_api_key": True
            }
        }

# Singleton instance
_config_manager_instance = None

def get_config_manager() -> SecureConfigManager:
    """
    Obtiene la instancia singleton del config manager
    
    Returns:
        Instancia de SecureConfigManager
    """
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = SecureConfigManager()
    return _config_manager_instance