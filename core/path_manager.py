"""
Path Manager - BOT-vCSGO-Beta V2
Sistema centralizado para gestión de rutas sin hardcoding

Características:
- Detección automática de rutas
- Configuración via variables de entorno
- Soporte para múltiples sistemas operativos
- Sin rutas hardcodeadas de usuario
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import platform
import logging


class PathManager:
    """
    Gestor centralizado de rutas para BOT-vCSGO-Beta V2
    
    Elimina el hardcoding de rutas específicas del usuario.
    Todas las rutas se determinan dinámicamente o desde variables de entorno.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("PathManager")
        self.system = platform.system()
        self.is_wsl = self._detect_wsl()
        
        # Detectar raíz del proyecto
        self.project_root = self._find_project_root()
        
        # Cargar configuración de rutas
        self._load_path_config()
        
        # Crear directorios necesarios
        self._ensure_directories()
        
        self.logger.info(f"PathManager inicializado")
        self.logger.info(f"  Sistema: {self.system} {'(WSL)' if self.is_wsl else ''}")
        self.logger.info(f"  Proyecto: {self.project_root}")
    
    def _detect_wsl(self) -> bool:
        """Detecta si estamos ejecutando en WSL"""
        if self.system != "Linux":
            return False
        
        try:
            with open("/proc/version", "r") as f:
                return "microsoft" in f.read().lower()
        except:
            return False
    
    def _find_project_root(self) -> Path:
        """
        Encuentra la raíz del proyecto buscando hacia arriba
        
        Returns:
            Path a la raíz del proyecto
        """
        # Empezar desde el directorio actual o el archivo ejecutado
        if hasattr(sys, 'argv') and sys.argv and sys.argv[0]:
            current = Path(sys.argv[0]).resolve().parent
        else:
            current = Path.cwd()
        
        # Buscar hacia arriba hasta encontrar marcadores del proyecto
        markers = ['config', 'core', 'scrapers', '.git', 'requirements.txt']
        
        while current != current.parent:
            # Verificar si tiene los marcadores necesarios
            if any((current / marker).exists() for marker in markers[:3]):
                return current
            current = current.parent
        
        # Fallback al directorio actual
        return Path.cwd()
    
    def _load_path_config(self):
        """Carga configuración de rutas desde variables de entorno"""
        # Directorio de datos
        self.data_dir = Path(os.getenv('BOT_DATA_PATH', str(self.project_root / 'data')))
        
        # Directorio de cache
        self.cache_dir = Path(os.getenv('BOT_CACHE_PATH', str(self.data_dir / 'cache')))
        
        # Directorio de logs
        self.logs_dir = Path(os.getenv('BOT_LOG_PATH', str(self.project_root / 'logs')))
        
        # Directorio de configuración
        self.config_dir = Path(os.getenv('BOT_CONFIG_PATH', str(self.project_root / 'config')))
        
        # Cache de imágenes - puede estar en ubicación externa
        image_cache_env = os.getenv('IMAGE_CACHE_PATH')
        if image_cache_env:
            self.image_cache_dir = Path(image_cache_env)
        else:
            # Buscar cache externo existente
            self.image_cache_dir = self._find_external_image_cache()
        
        # Chrome profile para Selenium (si se necesita)
        self.chrome_profile = self._get_chrome_profile_path()
    
    def _find_external_image_cache(self) -> Path:
        """
        Busca un cache de imágenes externo existente
        
        Returns:
            Path al cache de imágenes
        """
        # Posibles ubicaciones del cache externo (relativas al proyecto)
        possible_locations = [
            self.project_root.parent / "csgo ico cache" / "images",
            self.project_root.parent / "csgo_ico_cache" / "images",
            self.project_root.parent / "cache" / "images",
            self.cache_dir / "images"  # Fallback al cache interno
        ]
        
        # Buscar la primera que exista
        for location in possible_locations:
            if location.exists() and location.is_dir():
                self.logger.info(f"Cache de imágenes encontrado: {location}")
                return location
        
        # Si no existe ninguna, usar el cache interno
        return self.cache_dir / "images"
    
    def _get_chrome_profile_path(self) -> Optional[Path]:
        """
        Obtiene la ruta del perfil de Chrome para Selenium
        
        Returns:
            Path al perfil de Chrome o None
        """
        # Primero verificar variable de entorno
        env_profile = os.getenv('CHROME_PROFILE_PATH')
        if env_profile:
            return Path(env_profile)
        
        # Detectar según el sistema operativo
        home = Path.home()
        
        if self.system == "Windows" or self.is_wsl:
            # Windows o WSL
            possible_profiles = [
                home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Profile_Selenium",
                home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default",
            ]
            
            # En WSL, intentar acceder a la ruta de Windows
            if self.is_wsl:
                win_user = os.getenv('WINDOWS_USER', home.name)
                win_profiles = [
                    Path(f"/mnt/c/Users/{win_user}/AppData/Local/Google/Chrome/User Data/Profile_Selenium"),
                    Path(f"/mnt/c/Users/{win_user}/AppData/Local/Google/Chrome/User Data/Default"),
                ]
                possible_profiles = win_profiles + possible_profiles
        
        elif self.system == "Darwin":  # macOS
            possible_profiles = [
                home / "Library" / "Application Support" / "Google" / "Chrome" / "Profile_Selenium",
                home / "Library" / "Application Support" / "Google" / "Chrome" / "Default",
            ]
        
        else:  # Linux
            possible_profiles = [
                home / ".config" / "google-chrome" / "Profile_Selenium",
                home / ".config" / "google-chrome" / "Default",
            ]
        
        # Buscar el primero que exista
        for profile in possible_profiles:
            if profile.exists():
                return profile
        
        return None
    
    def _ensure_directories(self):
        """Crea los directorios necesarios si no existen"""
        directories = [
            self.data_dir,
            self.cache_dir,
            self.logs_dir,
            self.config_dir,
            self.cache_dir / "data",
            self.cache_dir / "images",
            self.cache_dir / "icons"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_data_file(self, filename: str) -> Path:
        """
        Obtiene la ruta completa para un archivo de datos
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            Path completo al archivo
        """
        return self.data_dir / filename
    
    def get_cache_file(self, filename: str, subfolder: str = "data") -> Path:
        """
        Obtiene la ruta completa para un archivo de cache
        
        Args:
            filename: Nombre del archivo
            subfolder: Subcarpeta dentro del cache
            
        Returns:
            Path completo al archivo
        """
        return self.cache_dir / subfolder / filename
    
    def get_image_path(self, image_name: str) -> Path:
        """
        Obtiene la ruta completa para una imagen del cache
        
        Args:
            image_name: Nombre de la imagen
            
        Returns:
            Path completo a la imagen
        """
        return self.image_cache_dir / image_name
    
    def get_log_file(self, filename: str) -> Path:
        """
        Obtiene la ruta completa para un archivo de log
        
        Args:
            filename: Nombre del archivo de log
            
        Returns:
            Path completo al archivo
        """
        return self.logs_dir / filename
    
    def get_config_file(self, filename: str) -> Path:
        """
        Obtiene la ruta completa para un archivo de configuración
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            Path completo al archivo
        """
        return self.config_dir / filename
    
    def get_chrome_profile(self) -> Optional[str]:
        """
        Obtiene la ruta del perfil de Chrome como string
        
        Returns:
            Ruta del perfil o None
        """
        if self.chrome_profile:
            return str(self.chrome_profile)
        return None
    
    def resolve_path(self, path_str: str) -> Path:
        """
        Resuelve una ruta relativa o absoluta
        
        Args:
            path_str: Ruta como string
            
        Returns:
            Path resuelto
        """
        path = Path(path_str)
        
        # Si es absoluta, devolverla
        if path.is_absolute():
            return path
        
        # Si es relativa, resolverla desde el proyecto
        return self.project_root / path
    
    def get_paths_info(self) -> Dict[str, str]:
        """
        Obtiene información de todas las rutas configuradas
        
        Returns:
            Diccionario con información de rutas
        """
        return {
            "project_root": str(self.project_root),
            "data_dir": str(self.data_dir),
            "cache_dir": str(self.cache_dir),
            "logs_dir": str(self.logs_dir),
            "config_dir": str(self.config_dir),
            "image_cache_dir": str(self.image_cache_dir),
            "chrome_profile": str(self.chrome_profile) if self.chrome_profile else "No configurado",
            "system": self.system,
            "is_wsl": self.is_wsl
        }
    
    def print_paths_info(self):
        """Imprime información de rutas para debugging"""
        print("\n=== Configuración de Rutas ===")
        info = self.get_paths_info()
        for key, value in info.items():
            print(f"{key:20}: {value}")
        print("=" * 40 + "\n")


# Singleton instance
_path_manager_instance = None

def get_path_manager() -> PathManager:
    """
    Obtiene la instancia singleton del path manager
    
    Returns:
        Instancia de PathManager
    """
    global _path_manager_instance
    if _path_manager_instance is None:
        _path_manager_instance = PathManager()
    return _path_manager_instance


# Funciones de conveniencia
def get_data_path(filename: str) -> Path:
    """Obtiene ruta de archivo de datos"""
    return get_path_manager().get_data_file(filename)

def get_cache_path(filename: str, subfolder: str = "data") -> Path:
    """Obtiene ruta de archivo de cache"""
    return get_path_manager().get_cache_file(filename, subfolder)

def get_image_path(image_name: str) -> Path:
    """Obtiene ruta de imagen"""
    return get_path_manager().get_image_path(image_name)

def get_log_path(filename: str) -> Path:
    """Obtiene ruta de archivo de log"""
    return get_path_manager().get_log_file(filename)

def get_config_path(filename: str) -> Path:
    """Obtiene ruta de archivo de configuración"""
    return get_path_manager().get_config_file(filename)

def get_project_root() -> Path:
    """Obtiene la raíz del proyecto"""
    return get_path_manager().project_root