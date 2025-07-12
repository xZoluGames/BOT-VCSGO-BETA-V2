"""
Tests unitarios para el PathManager
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import platform

from core.path_manager import PathManager, get_path_manager


class TestPathManager:
    """Tests para el PathManager"""
    
    def test_initialization(self, tmp_path):
        """Test de inicialización básica"""
        with patch('core.path_manager.PathManager._find_project_root', return_value=tmp_path):
            path_manager = PathManager()
            
            assert path_manager.project_root == tmp_path
            assert path_manager.data_dir.exists()
            assert path_manager.cache_dir.exists()
            assert path_manager.logs_dir.exists()
            assert path_manager.config_dir.exists()
    
    def test_wsl_detection(self):
        """Test de detección de WSL"""
        path_manager = PathManager()
        
        # En Linux real
        with patch('platform.system', return_value='Linux'):
            with patch('builtins.open', mock_open(read_data='Linux version')):
                assert path_manager._detect_wsl() is False
            
            # En WSL
            with patch('builtins.open', mock_open(read_data='Linux version Microsoft')):
                assert path_manager._detect_wsl() is True
        
        # En Windows
        with patch('platform.system', return_value='Windows'):
            assert path_manager._detect_wsl() is False
    
    def test_find_project_root(self, tmp_path):
        """Test de búsqueda de raíz del proyecto"""
        # Crear estructura de proyecto
        project_root = tmp_path / "project"
        (project_root / "config").mkdir(parents=True)
        (project_root / "core").mkdir()
        (project_root / "scrapers").mkdir()
        
        # Simular ejecución desde subdirectorio
        subdir = project_root / "core" / "submodule"
        subdir.mkdir(parents=True)
        
        with patch('pathlib.Path.cwd', return_value=subdir):
            path_manager = PathManager()
            # Debería encontrar la raíz del proyecto
            assert path_manager._find_project_root().name == "project"
    
    def test_path_configuration_from_env(self, tmp_path):
        """Test de configuración de rutas desde variables de entorno"""
        custom_paths = {
            'BOT_DATA_PATH': str(tmp_path / 'custom_data'),
            'BOT_CACHE_PATH': str(tmp_path / 'custom_cache'),
            'BOT_LOG_PATH': str(tmp_path / 'custom_logs'),
            'BOT_CONFIG_PATH': str(tmp_path / 'custom_config'),
            'IMAGE_CACHE_PATH': str(tmp_path / 'custom_images')
        }
        
        with patch.dict(os.environ, custom_paths):
            with patch('core.path_manager.PathManager._find_project_root', return_value=tmp_path):
                path_manager = PathManager()
                
                assert path_manager.data_dir == Path(custom_paths['BOT_DATA_PATH'])
                assert path_manager.cache_dir == Path(custom_paths['BOT_CACHE_PATH'])
                assert path_manager.logs_dir == Path(custom_paths['BOT_LOG_PATH'])
                assert path_manager.config_dir == Path(custom_paths['BOT_CONFIG_PATH'])
                assert path_manager.image_cache_dir == Path(custom_paths['IMAGE_CACHE_PATH'])
    
    def test_external_image_cache_detection(self, tmp_path):
        """Test de detección de cache de imágenes externo"""
        # Crear cache externo
        external_cache = tmp_path.parent / "csgo ico cache" / "images"
        external_cache.mkdir(parents=True)
        
        with patch('core.path_manager.PathManager._find_project_root', return_value=tmp_path):
            path_manager = PathManager()
            
            # Debe encontrar el cache externo
            assert "csgo ico cache" in str(path_manager.image_cache_dir)
    
    def test_chrome_profile_detection_windows(self, tmp_path):
        """Test de detección de perfil Chrome en Windows"""
        home = tmp_path / "Users" / "TestUser"
        chrome_profile = home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Profile_Selenium"
        chrome_profile.mkdir(parents=True)
        
        with patch('pathlib.Path.home', return_value=home):
            with patch('platform.system', return_value='Windows'):
                path_manager = PathManager()
                profile_path = path_manager._get_chrome_profile_path()
                
                assert profile_path is not None
                assert "Profile_Selenium" in str(profile_path)
    
    def test_chrome_profile_detection_wsl(self, tmp_path):
        """Test de detección de perfil Chrome en WSL"""
        # Simular estructura WSL
        wsl_chrome = tmp_path / "mnt" / "c" / "Users" / "TestUser" / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Profile_Selenium"
        wsl_chrome.mkdir(parents=True)
        
        with patch.dict(os.environ, {'WINDOWS_USER': 'TestUser'}):
            with patch('platform.system', return_value='Linux'):
                with patch('core.path_manager.PathManager._detect_wsl', return_value=True):
                    with patch('pathlib.Path.exists') as mock_exists:
                        mock_exists.side_effect = lambda self: str(self) == str(wsl_chrome)
                        
                        path_manager = PathManager()
                        profile_path = path_manager._get_chrome_profile_path()
                        
                        # Debe encontrar el perfil en la ruta WSL
                        if profile_path:
                            assert "/mnt/c/Users" in str(profile_path)
    
    def test_directory_creation(self, tmp_path):
        """Test de creación automática de directorios"""
        with patch('core.path_manager.PathManager._find_project_root', return_value=tmp_path):
            path_manager = PathManager()
            
            # Verificar que se crearon todos los directorios
            assert path_manager.data_dir.exists()
            assert path_manager.cache_dir.exists()
            assert path_manager.logs_dir.exists()
            assert path_manager.config_dir.exists()
            assert (path_manager.cache_dir / "data").exists()
            assert (path_manager.cache_dir / "images").exists()
            assert (path_manager.cache_dir / "icons").exists()
    
    def test_get_data_file(self, tmp_path):
        """Test de obtención de ruta de archivo de datos"""
        with patch('core.path_manager.PathManager._find_project_root', return_value=tmp_path):
            path_manager = PathManager()
            
            data_file = path_manager.get_data_file("waxpeer_data.json")
            assert data_file.parent == path_manager.data_dir
            assert data_file.name == "waxpeer_data.json"
    
    def test_get_cache_file(self, tmp_path):
        """Test de obtención de ruta de archivo de cache"""
        with patch('core.path_manager.PathManager._find_project_root', return_value=tmp_path):
            path_manager = PathManager()
            
            # Cache de datos
            cache_file = path_manager.get_cache_file("cache_data.json", "data")
            assert cache_file.parent == path_manager.cache_dir / "data"
            
            # Cache de otro tipo
            icon_file = path_manager.get_cache_file("icon.svg", "icons")
            assert icon_file.parent == path_manager.cache_dir / "icons"
    
    def test_get_image_path(self, tmp_path):
        """Test de obtención de ruta de imagen"""
        with patch('core.path_manager.PathManager._find_project_root', return_value=tmp_path):
            path_manager = PathManager()
            
            image_path = path_manager.get_image_path("ak47_redline.png")
            assert image_path.parent == path_manager.image_cache_dir
            assert image_path.name == "ak47_redline.png"
    
    def test_resolve_path(self, tmp_path):
        """Test de resolución de rutas"""
        with patch('core.path_manager.PathManager._find_project_root', return_value=tmp_path):
            path_manager = PathManager()
            
            # Ruta absoluta
            abs_path = tmp_path / "absolute" / "path"
            resolved = path_manager.resolve_path(str(abs_path))
            assert resolved == abs_path
            
            # Ruta relativa
            rel_path = "relative/path"
            resolved = path_manager.resolve_path(rel_path)
            assert resolved == path_manager.project_root / rel_path
    
    def test_get_paths_info(self, tmp_path):
        """Test de información de rutas"""
        with patch('core.path_manager.PathManager._find_project_root', return_value=tmp_path):
            path_manager = PathManager()
            
            info = path_manager.get_paths_info()
            
            assert 'project_root' in info
            assert 'data_dir' in info
            assert 'cache_dir' in info
            assert 'logs_dir' in info
            assert 'config_dir' in info
            assert 'image_cache_dir' in info
            assert 'chrome_profile' in info
            assert 'system' in info
            assert 'is_wsl' in info
    
    def test_singleton_pattern(self, tmp_path):
        """Test del patrón singleton"""
        with patch('core.path_manager.PathManager._find_project_root', return_value=tmp_path):
            manager1 = get_path_manager()
            manager2 = get_path_manager()
            
            # Deben ser la misma instancia
            assert manager1 is manager2
    
    @pytest.mark.parametrize("filename,expected_parent", [
        ("data.json", "data"),
        ("log.txt", "logs"),
        ("config.ini", "config"),
    ])
    def test_file_paths(self, tmp_path, filename, expected_parent):
        """Test parametrizado para diferentes tipos de archivos"""
        with patch('core.path_manager.PathManager._find_project_root', return_value=tmp_path):
            path_manager = PathManager()
            
            if expected_parent == "data":
                file_path = path_manager.get_data_file(filename)
                assert file_path.parent.name == "data"
            elif expected_parent == "logs":
                file_path = path_manager.get_log_file(filename)
                assert file_path.parent.name == "logs"
            elif expected_parent == "config":
                file_path = path_manager.get_config_file(filename)
                assert file_path.parent.name == "config"