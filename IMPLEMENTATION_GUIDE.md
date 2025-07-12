# 📋 Guía de Implementación - BOT-VCSGO-BETA-V2

## 🚀 Resumen de Mejoras Implementadas

### ✅ Fase 1: Seguridad Crítica (COMPLETADA)
1. **Sistema de Configuración Seguro** - `core/config_manager.py`
2. **Gestor de Proxies Seguro** - `core/oculus_proxy_manager.py`
3. **Gestor de Rutas** - `core/path_manager.py`
4. **Scripts de Migración y Verificación**

### ✅ Fase 2: Testing y Manejo de Errores (COMPLETADA)
1. **Framework de Testing** - `tests/` con pytest
2. **Sistema de Excepciones** - `core/exceptions.py`
3. **Configuración de Testing** - `pytest.ini`

## 📝 Pasos de Implementación

### Paso 1: Preparación del Entorno

```bash
# 1. Instalar dependencias necesarias
pip install python-dotenv orjson

# 2. Instalar dependencias de testing (opcional pero recomendado)
pip install -r requirements-test.txt

# 3. Crear estructura de directorios
mkdir -p tests
mkdir -p logs
```

### Paso 2: Migración de Seguridad

```bash
# 1. Ejecutar el script de migración
python migrate_to_secure_config.py

# 2. Verificar que se creó el archivo .env
cat .env

# 3. Editar .env con tus claves reales
nano .env  # o tu editor favorito
```

### Paso 3: Actualizar Archivos Core

```bash
# 1. Hacer backup de archivos originales
cp core/config_manager.py core/config_manager.py.backup
cp core/proxy_manager.py core/proxy_manager.py.backup

# 2. Reemplazar con las versiones seguras
# - Copiar el contenido de config_manager.py del artifact
# - Copiar el contenido de oculus_proxy_manager.py del artifact
# - Crear core/path_manager.py con el contenido del artifact
# - Crear core/exceptions.py con el contenido del artifact
```

### Paso 4: Actualizar Imports en Scrapers

En cada scraper, actualiza los imports:

```python
# Antiguo
from core.config_manager import ConfigManager
config = ConfigManager()

# Nuevo
from core.config_manager import get_config_manager
from core.path_manager import get_path_manager
from core.exceptions import APIError, RateLimitError, ErrorHandler

config_manager = get_config_manager()
path_manager = get_path_manager()
```

### Paso 5: Actualizar Uso de Claves API

```python
# Antiguo
api_key = config.api_keys['waxpeer']['api_key']

# Nuevo
api_key = config_manager.get_api_key('waxpeer')
if not api_key:
    raise MissingAPIKeyError('waxpeer', 'WAXPEER_API_KEY')
```

### Paso 6: Actualizar Gestión de Rutas

```python
# Antiguo
data_file = "/mnt/c/Users/Zolu/Documents/BOT-VCSGO-BETA-V2/data/waxpeer_data.json"

# Nuevo
data_file = path_manager.get_data_file("waxpeer_data.json")
```

### Paso 7: Implementar Manejo de Errores

```python
# En tus scrapers
from core.exceptions import APIError, ErrorHandler

try:
    response = requests.get(url)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    api_error = ErrorHandler.handle_api_error(self.platform_name, e, self.logger)
    if api_error:
        raise api_error
    raise
```

### Paso 8: Ejecutar Verificación

```bash
# Verificar que todo esté configurado correctamente
python verify_security.py

# Si hay problemas, el script te indicará qué resolver
```

### Paso 9: Ejecutar Tests

```bash
# Ejecutar todos los tests
python run_tests.py

# Solo tests unitarios
python run_tests.py --type unit

# Tests con coverage HTML
python run_tests.py --html-coverage --open-coverage
```

## 🔧 Configuración del Archivo .env

```bash
# Claves API principales (ajusta según tus plataformas)
WAXPEER_API_KEY=tu_clave_real_aqui
EMPIRE_API_KEY=tu_clave_real_aqui
SHADOWPAY_API_KEY=tu_clave_real_aqui
RUSTSKINS_API_KEY=tu_clave_real_aqui

# Credenciales de Oculus Proxy
OCULUS_AUTH_TOKEN=tu_token_auth_oculus
OCULUS_ORDER_TOKEN=tu_token_order_oculus

# Configuración opcional
BOT_LOG_LEVEL=INFO
BOT_USE_PROXY=true
BOT_CACHE_ENABLED=true
```

## 📁 Estructura de Archivos Actualizada

```
BOT-VCSGO-BETA-V2/
├── .env                    # Variables de entorno (NO subir a Git)
├── .env.example           # Template de ejemplo
├── .gitignore             # Actualizado con archivos sensibles
├── core/
│   ├── config_manager.py  # NUEVO: Configuración segura
│   ├── path_manager.py    # NUEVO: Gestión de rutas
│   ├── exceptions.py      # NUEVO: Sistema de excepciones
│   └── oculus_proxy_manager.py  # ACTUALIZADO: Sin credenciales
├── tests/
│   ├── conftest.py        # NUEVO: Configuración de tests
│   ├── test_config_manager.py  # NUEVO: Tests de config
│   └── test_path_manager.py    # NUEVO: Tests de rutas
├── pytest.ini             # NUEVO: Configuración pytest
├── run_tests.py          # NUEVO: Script para ejecutar tests
└── requirements-test.txt  # NUEVO: Dependencias de testing
```

## ⚠️ Checklist de Seguridad

- [ ] ¿Eliminaste o renombraste `config/api_keys.json`?
- [ ] ¿Creaste y configuraste el archivo `.env`?
- [ ] ¿Agregaste `.env` a `.gitignore`?
- [ ] ¿Actualizaste todos los scrapers para usar el nuevo sistema?
- [ ] ¿Ejecutaste `verify_security.py` y pasaron todas las verificaciones?
- [ ] ¿No hay rutas hardcodeadas con `/Users/Zolu/` en el código?
- [ ] ¿No hay tokens de Oculus hardcodeados?

## 🎯 Próximos Pasos

Una vez completada esta implementación:

1. **Fase 3: Optimización de Rendimiento**
   - Migración a asyncio
   - Connection pooling
   - Cache inteligente

2. **Fase 4: Mejoras de Arquitectura**
   - Patrón Strategy para scrapers
   - Event-driven architecture
   - Integración de base de datos

## 📞 Soporte

Si encuentras problemas durante la implementación:

1. Revisa los logs en `logs/`
2. Ejecuta `python verify_security.py` para diagnóstico
3. Verifica que todas las variables de entorno estén configuradas
4. Asegúrate de que las dependencias estén instaladas

## ✨ Beneficios de las Mejoras

- **🔒 Seguridad**: No más claves API expuestas
- **🧪 Confiabilidad**: Tests automatizados con 80%+ coverage
- **🚀 Rendimiento**: Preparado para optimizaciones futuras
- **📊 Mantenibilidad**: Código limpio y bien estructurado
- **🔍 Debugging**: Sistema de errores detallado

¡Tu proyecto ahora es más seguro, confiable y mantenible!