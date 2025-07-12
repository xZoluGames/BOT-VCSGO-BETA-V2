"""
Tests unitarios para el SecureConfigManager
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, mock_open
import orjson

from core.config_manager import SecureConfigManager, get_config_manager


class TestSecureConfigManager:
    """Tests para el SecureConfigManager"""
    
    def test_initialization(self, mock_env_vars, mock_config_dir):
        """Test de inicialización básica"""
        config_manager = SecureConfigManager(config_dir=mock_config_dir)
        
        assert config_manager.config_dir == mock_config_dir
        assert config_manager.settings_file.exists()
        assert config_manager.scrapers_file.exists()
    
    def test_load_api_keys_from_env(self, mock_env_vars):
        """Test de carga de API keys desde variables de entorno"""
        config_manager = SecureConfigManager()
        api_keys = config_manager.get_api_keys()
        
        # Verificar que se cargaron las claves
        assert 'waxpeer' in api_keys
        assert api_keys['waxpeer']['api_key'] == 'test_waxpeer_key_12345'
        assert 'empire' in api_keys
        assert api_keys['empire']['api_key'] == 'test_empire_key_67890'
        
        # Verificar configuración de proxy
        assert '_proxy_config' in api_keys
        assert api_keys['_proxy_config']['oculus_auth_token'] == 'test_oculus_auth_12345'
    
    def test_get_api_key_specific(self, mock_env_vars):
        """Test de obtención de API key específica"""
        config_manager = SecureConfigManager()
        
        # Clave existente
        waxpeer_key = config_manager.get_api_key('waxpeer')
        assert waxpeer_key == 'test_waxpeer_key_12345'
        
        # Clave no existente
        nonexistent_key = config_manager.get_api_key('nonexistent')
        assert nonexistent_key is None
    
    def test_get_proxy_config(self, mock_env_vars, mock_config_dir):
        """Test de obtención de configuración de proxy"""
        config_manager = SecureConfigManager(config_dir=mock_config_dir)
        proxy_config = config_manager.get_proxy_config()
        
        assert 'oculus_auth_token' in proxy_config
        assert proxy_config['oculus_auth_token'] == 'test_oculus_auth_12345'
        assert 'oculus_order_token' in proxy_config
        assert proxy_config['oculus_order_token'] == 'test_oculus_order_67890'
    
    def test_get_settings(self, mock_env_vars, mock_config_dir):
        """Test de carga de configuración general"""
        config_manager = SecureConfigManager(config_dir=mock_config_dir)
        settings = config_manager.get_settings()
        
        assert 'project' in settings
        assert settings['project']['name'] == 'BOT-vCSGO-Beta V2 Test'
        assert settings['project']['environment'] == 'testing'
        
        assert 'scrapers' in settings
        assert settings['scrapers']['default_timeout'] == 10
    
    def test_get_scraper_config(self, mock_env_vars, mock_config_dir):
        """Test de configuración específica de scraper"""
        config_manager = SecureConfigManager(config_dir=mock_config_dir)
        
        # Scraper configurado
        waxpeer_config = config_manager.get_scraper_config('waxpeer')
        assert waxpeer_config['enabled'] is True
        assert waxpeer_config['api_url'] == 'https://api.waxpeer.com/v1/prices'
        assert waxpeer_config['priority'] == 'high'
        
        # Scraper no configurado (debe usar defaults)
        unknown_config = config_manager.get_scraper_config('unknown')
        assert unknown_config['enabled'] is True  # Default
        assert unknown_config['timeout_seconds'] == 10  # From global_settings
    
    def test_env_overrides(self, mock_config_dir):
        """Test de overrides desde variables de entorno"""
        with patch.dict(os.environ, {
            'BOT_USE_PROXY': 'true',
            'BOT_LOG_LEVEL': 'ERROR',
            'BOT_CACHE_ENABLED': 'false'
        }):
            config_manager = SecureConfigManager(config_dir=mock_config_dir)
            settings = config_manager.get_settings()
            
            # Los overrides deben aplicarse
            assert settings['proxy']['enabled'] is True
            assert settings['logging']['level'] == 'ERROR'
            assert settings['cache']['enabled'] is False
    
    def test_missing_required_keys(self):
        """Test cuando faltan claves requeridas"""
        with patch.dict(os.environ, {}, clear=True):
            config_manager = SecureConfigManager()
            api_keys = config_manager.get_api_keys()
            
            # No debe haber claves si no hay variables de entorno
            assert 'empire' not in api_keys
            assert '_proxy_config' not in api_keys
    
    def test_api_keys_template_creation(self, tmp_path):
        """Test de creación de template de API keys"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        # Crear archivo api_keys.json inseguro
        insecure_file = config_dir / "api_keys.json"
        with open(insecure_file, 'w') as f:
            f.write('{"waxpeer": {"api_key": "real_key_12345"}}')
        
        config_manager = SecureConfigManager(config_dir=config_dir)
        
        # Debe crear el template
        template_file = config_dir / "api_keys.template.json"
        assert template_file.exists()
        
        # Verificar contenido del template
        with open(template_file, 'rb') as f:
            template_data = orjson.loads(f.read())
        
        assert '_instructions' in template_data
        assert 'platforms' in template_data
        assert 'waxpeer' in template_data['platforms']
    
    def test_singleton_pattern(self, mock_env_vars):
        """Test del patrón singleton"""
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        # Deben ser la misma instancia
        assert manager1 is manager2
    
    def test_cache_behavior(self, mock_env_vars, mock_config_dir):
        """Test del comportamiento de caché"""
        config_manager = SecureConfigManager(config_dir=mock_config_dir)
        
        # Primera llamada
        settings1 = config_manager.get_settings()
        
        # Modificar el archivo
        settings_file = mock_config_dir / "settings.json"
        new_settings = orjson.loads(settings_file.read_bytes())
        new_settings['project']['name'] = 'Modified Name'
        with open(settings_file, 'wb') as f:
            f.write(orjson.dumps(new_settings))
        
        # Segunda llamada (debe devolver el caché)
        settings2 = config_manager.get_settings()
        assert settings2['project']['name'] == 'BOT-vCSGO-Beta V2 Test'
        
        # Las referencias deben ser las mismas (caché)
        assert settings1 is settings2
    
    @pytest.mark.parametrize("platform,expected_key", [
        ('waxpeer', 'test_waxpeer_key_12345'),
        ('empire', 'test_empire_key_67890'),
        ('shadowpay', 'test_shadow_key_abcde'),
        ('rustskins', 'test_rust_key_fghij'),
    ])
    def test_platform_keys(self, mock_env_vars, platform, expected_key):
        """Test parametrizado para diferentes plataformas"""
        config_manager = SecureConfigManager()
        api_key = config_manager.get_api_key(platform)
        assert api_key == expected_key
    
    def test_error_handling_corrupted_json(self, tmp_path):
        """Test de manejo de errores con JSON corrupto"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        # Crear archivo JSON corrupto
        settings_file = config_dir / "settings.json"
        with open(settings_file, 'w') as f:
            f.write('{"invalid": json content}')
        
        config_manager = SecureConfigManager(config_dir=config_dir)
        settings = config_manager.get_settings()
        
        # Debe devolver configuración por defecto
        assert 'project' in settings
        assert settings['project']['name'] == 'BOT-vCSGO-Beta V2'