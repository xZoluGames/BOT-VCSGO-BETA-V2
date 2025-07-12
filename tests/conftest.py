"""
Configuración base para testing - BOT-VCSGO-BETA-V2

Fixtures y configuraciones compartidas para todos los tests.
"""

import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import orjson
from datetime import datetime

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Configuración de pytest
pytest_plugins = []


@pytest.fixture(scope="session")
def test_data_dir():
    """Crea un directorio temporal para datos de prueba"""
    temp_dir = tempfile.mkdtemp(prefix="bot_test_")
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def mock_env_vars():
    """Mock de variables de entorno para testing"""
    env_vars = {
        'WAXPEER_API_KEY': 'test_waxpeer_key_12345',
        'EMPIRE_API_KEY': 'test_empire_key_67890',
        'SHADOWPAY_API_KEY': 'test_shadow_key_abcde',
        'RUSTSKINS_API_KEY': 'test_rust_key_fghij',
        'OCULUS_AUTH_TOKEN': 'test_oculus_auth_12345',
        'OCULUS_ORDER_TOKEN': 'test_oculus_order_67890',
        'BOT_LOG_LEVEL': 'DEBUG',
        'BOT_USE_PROXY': 'false',  # Desactivado para tests
        'BOT_CACHE_ENABLED': 'true',
        'BOT_DATABASE_ENABLED': 'false',
        'BOT_ENVIRONMENT': 'testing'
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_config_dir(test_data_dir):
    """Crea un directorio de configuración de prueba"""
    config_dir = test_data_dir / "config"
    config_dir.mkdir(exist_ok=True)
    
    # Crear archivos de configuración de prueba
    settings = {
        "project": {
            "name": "BOT-vCSGO-Beta V2 Test",
            "version": "2.0.0-test",
            "environment": "testing"
        },
        "scrapers": {
            "default_interval": 30,
            "default_timeout": 10,
            "default_retries": 2,
            "use_proxy_by_default": False
        },
        "cache": {
            "enabled": True,
            "memory_limit_items": 100,
            "default_ttl_seconds": 60
        },
        "logging": {
            "level": "DEBUG",
            "save_to_file": False,
            "console_output": True
        }
    }
    
    with open(config_dir / "settings.json", 'wb') as f:
        f.write(orjson.dumps(settings, option=orjson.OPT_INDENT_2))
    
    scrapers = {
        "global_settings": {
            "enabled": True,
            "use_proxy": False,
            "timeout_seconds": 10,
            "max_retries": 2
        },
        "waxpeer": {
            "enabled": True,
            "api_url": "https://api.waxpeer.com/v1/prices",
            "priority": "high"
        },
        "empire": {
            "enabled": True,
            "api_url": "https://csgoempire.com/api/v2/trading/items",
            "priority": "high"
        }
    }
    
    with open(config_dir / "scrapers.json", 'wb') as f:
        f.write(orjson.dumps(scrapers, option=orjson.OPT_INDENT_2))
    
    return config_dir


@pytest.fixture
def mock_requests():
    """Mock para requests.get/post con respuestas predefinidas"""
    with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
        # Configurar respuestas por defecto
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": []}
        mock_response.text = '{"success": true}'
        mock_response.content = b'{"success": true}'
        mock_response.headers = {'Content-Type': 'application/json'}
        
        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        
        yield {
            'get': mock_get,
            'post': mock_post,
            'response': mock_response
        }


@pytest.fixture
def sample_item_data():
    """Datos de ejemplo de items de CS:GO"""
    return [
        {
            "name": "AK-47 | Redline (Field-Tested)",
            "price": 45.50,
            "steam_price": 48.99,
            "quantity": 5,
            "tradable": True,
            "inspect_link": "steam://rungame/730/76561202255233023/+csgo_econ_action_preview%20S76561198044170935A28599273007D11989195491730346294",
            "image": "https://steamcdn-a.akamaihd.net/apps/730/icons/econ/default_generated/weapon_ak47_cu_ak47_rubber_light_large.ec20a6d0e7a03cdc34cb6c5f75f1fd9c1a9c4a08.png"
        },
        {
            "name": "AWP | Dragon Lore (Factory New)",
            "price": 15000.00,
            "steam_price": 16500.00,
            "quantity": 1,
            "tradable": True,
            "inspect_link": "steam://rungame/730/76561202255233023/+csgo_econ_action_preview%20S76561198044170935A28599273008D11989195491730346295",
            "image": "https://steamcdn-a.akamaihd.net/apps/730/icons/econ/default_generated/weapon_awp_cu_awp_dragon_lore_light_large.123a5f7e3e8bf470c8f87e90514091ea9a8b1507.png"
        },
        {
            "name": "Karambit | Doppler (Factory New)",
            "price": 850.00,
            "steam_price": 920.00,
            "quantity": 3,
            "tradable": True,
            "phase": "Phase 2",
            "inspect_link": "steam://rungame/730/76561202255233023/+csgo_econ_action_preview%20S76561198044170935A28599273009D11989195491730346296",
            "image": "https://steamcdn-a.akamaihd.net/apps/730/icons/econ/default_generated/weapon_knife_karambit_am_doppler_phase2_light_large.7e034f5233a8fa9332cc3387b0b8ce2d69a32c2f.png"
        }
    ]


@pytest.fixture
def mock_cache_service(test_data_dir):
    """Mock del servicio de cache"""
    cache_dir = test_data_dir / "cache"
    cache_dir.mkdir(exist_ok=True)
    
    class MockCache:
        def __init__(self):
            self.memory_cache = {}
            self.cache_dir = cache_dir
        
        def get(self, key):
            return self.memory_cache.get(key)
        
        def set(self, key, value, ttl=300):
            self.memory_cache[key] = value
        
        def delete(self, key):
            self.memory_cache.pop(key, None)
        
        def clear(self):
            self.memory_cache.clear()
        
        def get_image_path(self, name):
            return self.cache_dir / "images" / name
    
    return MockCache()


@pytest.fixture
def mock_profitability_data():
    """Datos de ejemplo para análisis de rentabilidad"""
    return {
        "timestamp": datetime.now().isoformat(),
        "opportunities": [
            {
                "item_name": "AK-47 | Redline (Field-Tested)",
                "buy_platform": "waxpeer",
                "buy_price": 45.50,
                "sell_platform": "steam",
                "sell_price": 48.99,
                "profit": 2.49,
                "profit_percentage": 5.47,
                "buy_url": "https://waxpeer.com/item/12345",
                "sell_url": "https://steamcommunity.com/market/listings/730/AK-47%20%7C%20Redline%20%28Field-Tested%29"
            },
            {
                "item_name": "Karambit | Doppler (Factory New)",
                "buy_platform": "empire",
                "buy_price": 850.00,
                "sell_platform": "steam",
                "sell_price": 920.00,
                "profit": 45.00,
                "profit_percentage": 5.29,
                "buy_url": "https://csgoempire.com/item/67890",
                "sell_url": "https://steamcommunity.com/market/listings/730/Karambit%20%7C%20Doppler%20%28Factory%20New%29"
            }
        ],
        "total_opportunities": 2,
        "average_profit_percentage": 5.38
    }


@pytest.fixture
def mock_logger():
    """Mock del logger para capturar logs en tests"""
    import logging
    
    class MockLogHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.messages = []
        
        def emit(self, record):
            self.messages.append({
                'level': record.levelname,
                'message': self.format(record),
                'name': record.name
            })
    
    handler = MockLogHandler()
    handler.setFormatter(logging.Formatter('%(levelname)s - %(name)s - %(message)s'))
    
    # Agregar a root logger
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    yield handler
    
    # Cleanup
    logger.removeHandler(handler)


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons entre tests para evitar contaminación"""
    # Importar los módulos que usan singletons
    from core import config_manager
    from core import path_manager
    
    # Reset singleton instances
    config_manager._config_manager_instance = None
    path_manager._path_manager_instance = None
    
    yield
    
    # Cleanup después del test
    config_manager._config_manager_instance = None
    path_manager._path_manager_instance = None


@pytest.fixture
def mock_proxy_response():
    """Mock de respuesta de Oculus Proxy API"""
    return {
        "proxies": [
            "proxy1.oculus.com:8080:user1:pass1",
            "proxy2.oculus.com:8080:user2:pass2",
            "proxy3.oculus.com:8080:user3:pass3"
        ]
    }


# Marcadores personalizados
def pytest_configure(config):
    """Registrar marcadores personalizados"""
    config.addinivalue_line(
        "markers", "slow: marca tests que son lentos (>1s)"
    )
    config.addinivalue_line(
        "markers", "integration: marca tests de integración"
    )
    config.addinivalue_line(
        "markers", "unit: marca tests unitarios"
    )
    config.addinivalue_line(
        "markers", "security: marca tests de seguridad"
    )


# Configuración para coverage
def pytest_collection_modifyitems(config, items):
    """Modificar items de colección para agregar marcadores automáticos"""
    for item in items:
        # Agregar marcador unit por defecto si no tiene otros
        if not any(mark.name in ['slow', 'integration'] for mark in item.iter_markers()):
            item.add_marker(pytest.mark.unit)