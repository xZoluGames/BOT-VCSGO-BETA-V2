# 🚀 Guía de Migración a Async - BOT-VCSGO-BETA-V2

## 📋 Resumen de Optimizaciones de Rendimiento

### ✅ Componentes Implementados

1. **Base Scraper Asíncrono** (`core/async_base_scraper.py`)
   - Soporte async/await nativo
   - Connection pooling automático
   - Rate limiting inteligente
   - Métricas de rendimiento

2. **Cache Service Asíncrono** (`core/async_cache_service.py`)
   - TTL adaptativo basado en frecuencia
   - Compresión automática
   - Estadísticas de uso
   - Cache en memoria y disco

3. **Ejemplo de Scraper Asíncrono** (`scrapers/async_waxpeer_scraper.py`)
   - Procesamiento paralelo de páginas
   - Validación asíncrona

4. **Runner Asíncrono** (`run_async.py`)
   - Ejecución paralela de múltiples scrapers
   - Métricas y comparación de rendimiento

## 📊 Beneficios Esperados

- **⚡ 60-80% más rápido** en operaciones de red
- **🔄 Concurrencia real** - múltiples requests simultáneos
- **💾 Menor uso de memoria** con connection pooling
- **📈 Mayor throughput** - más items por segundo
- **🛡️ Más resiliente** - mejor manejo de errores

## 🔧 Guía de Migración Paso a Paso

### Paso 1: Instalar Dependencias Asíncronas

```bash
pip install aiohttp aiofiles asyncio orjson
```

### Paso 2: Estructura de un Scraper Asíncrono

Aquí está la plantilla para convertir cualquier scraper:

```python
"""
Async [Platform] Scraper - BOT-VCSGO-BETA-V2
"""

import asyncio
from typing import List, Dict, Any, Optional
from core.async_base_scraper import AsyncBaseScraper

class Async[Platform]Scraper(AsyncBaseScraper):
    def __init__(self, use_proxy: Optional[bool] = None):
        # Configuración específica de la plataforma
        custom_config = {
            'rate_limit': 60,      # Ajustar según API
            'burst_size': 10,      
            'cache_ttl': 300,      
            'timeout_seconds': 30,
            'max_retries': 3
        }
        
        super().__init__(
            platform_name='[platform]',
            use_proxy=use_proxy,
            custom_config=custom_config
        )
        
        # URLs y configuración específica
        self.api_url = "https://api.[platform].com/v1/items"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """Implementación del scraping"""
        # Tu lógica de scraping aquí
        items = await self._fetch_items()
        return await self._process_items(items)
    
    async def _fetch_items(self) -> List[Dict[str, Any]]:
        """Obtiene items de la API"""
        # Usar self.fetch_json() en lugar de requests.get()
        data = await self.fetch_json(self.api_url)
        return data.get('items', [])
    
    async def _process_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Procesa items en paralelo"""
        tasks = [self._process_single_item(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrar errores
        return [r for r in results if not isinstance(r, Exception)]
```

### Paso 3: Conversión de Código Síncrono a Asíncrono

#### 🔄 Requests → Aiohttp

**Antes (Síncrono):**
```python
import requests

response = requests.get(url, headers=headers)
data = response.json()
```

**Después (Asíncrono):**
```python
# Usando el método helper del base scraper
data = await self.fetch_json(url, headers=headers)

# O manualmente:
response = await self.fetch(url, headers=headers)
data = await response.json()
```

#### 🔄 Procesamiento Secuencial → Paralelo

**Antes (Síncrono):**
```python
processed_items = []
for item in items:
    processed = self.process_item(item)
    if processed:
        processed_items.append(processed)
```

**Después (Asíncrono):**
```python
# Crear tareas para procesamiento paralelo
tasks = [self.process_item(item) for item in items]
results = await asyncio.gather(*tasks, return_exceptions=True)

# Filtrar resultados válidos
processed_items = [r for r in results if r and not isinstance(r, Exception)]
```

#### 🔄 File I/O → Async File I/O

**Antes (Síncrono):**
```python
with open('data.json', 'w') as f:
    json.dump(data, f)
```

**Después (Asíncrono):**
```python
import aiofiles
import orjson

async with aiofiles.open('data.json', 'wb') as f:
    await f.write(orjson.dumps(data))
```

#### 🔄 Sleep → Async Sleep

**Antes (Síncrono):**
```python
time.sleep(1)
```

**Después (Asíncrono):**
```python
await asyncio.sleep(1)
```

### Paso 4: Manejo de Rate Limiting

El base scraper asíncrono incluye rate limiting automático:

```python
# En tu __init__:
custom_config = {
    'rate_limit': 120,  # Requests por minuto
    'burst_size': 20,   # Requests máximos en burst
}

# El rate limiter se encarga automáticamente
# No necesitas implementar delays manuales
```

### Paso 5: Cache Inteligente

El cache asíncrono se usa automáticamente:

```python
# Cache automático con fetch_json
data = await self.fetch_json(url)  # Primer request: API
data = await self.fetch_json(url)  # Segundo request: Cache

# Control manual del cache
await self.cache.set('key', value, ttl=600)
value = await self.cache.get('key')
```

### Paso 6: Validación Asíncrona

```python
async def validate_item(self, item: Dict[str, Any]) -> bool:
    # Validación base
    if not await super().validate_item(item):
        return False
    
    # Validaciones específicas de la plataforma
    # Puedes hacer validaciones asíncronas aquí
    if need_external_validation:
        is_valid = await self._check_external_api(item)
        return is_valid
    
    return True
```

## 📝 Ejemplo Completo: Migración de Empire Scraper

### Version Original (Síncrona)
```python
class EmpireScraper(BaseScraper):
    def scrape_market(self):
        response = requests.get(self.api_url, headers=self.headers)
        items = response.json()['items']
        
        processed = []
        for item in items:
            if self.validate_item(item):
                processed.append(self.process_item(item))
        
        return processed
```

### Version Migrada (Asíncrona)
```python
class AsyncEmpireScraper(AsyncBaseScraper):
    async def scrape(self) -> List[Dict[str, Any]]:
        # Fetch con cache automático
        data = await self.fetch_json(self.api_url)
        items = data.get('items', [])
        
        # Procesamiento paralelo
        tasks = []
        for item in items:
            task = asyncio.create_task(self._process_single_item(item))
            tasks.append(task)
        
        # Ejecutar todas las tareas en paralelo
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrar resultados válidos
        return [r for r in results if r and not isinstance(r, Exception)]
    
    async def _process_single_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not await self.validate_item(item):
            return None
        
        return {
            'name': item['name'],
            'price': item['price'] / 100,  # Centavos a dólares
            'quantity': item['quantity'],
            # ... más campos
        }
```

## 🚀 Ejecutar Scrapers Asíncronos

### Individual
```bash
# Ejecutar un scraper específico
python -m scrapers.async_waxpeer_scraper

# Con comparación de rendimiento
python scrapers/async_waxpeer_scraper.py
```

### Múltiples Scrapers
```bash
# Ejecutar todos los scrapers asíncronos
python run_async.py

# Ejecutar scrapers específicos
python run_async.py waxpeer empire skinport

# Con configuración avanzada
python run_async.py --concurrent 10 --use-proxy

# Comparación sync vs async
python run_async.py --compare

# Test de estrés
python run_async.py --stress-test --stress-iterations 10
```

## 📊 Métricas de Rendimiento

El sistema incluye métricas automáticas:

```python
# Acceder a métricas después del scraping
metrics = scraper.metrics.to_dict()
print(f"Requests exitosos: {metrics['requests_successful']}")
print(f"Tiempo promedio: {metrics['avg_response_time']}")
print(f"Cache hit rate: {metrics['cache_hit_rate']}")
```

## ⚡ Tips de Optimización

### 1. **Ajustar Concurrencia**
```python
# En el runner
runner = AsyncScraperRunner(max_concurrent=10)  # Más scrapers paralelos

# En el scraper individual
self.connector = aiohttp.TCPConnector(
    limit=100,           # Total de conexiones
    limit_per_host=30    # Conexiones por host
)
```

### 2. **Optimizar Batch Processing**
```python
# Procesar en lotes para APIs con límites
async def _fetch_all_pages(self):
    batch_size = 5
    for i in range(0, total_pages, batch_size):
        batch = [self._fetch_page(j) for j in range(i, min(i+batch_size, total_pages))]
        results = await asyncio.gather(*batch)
        # Procesar resultados
        await asyncio.sleep(0.5)  # Pausa entre lotes
```

### 3. **Cache Estratégico**
```python
# TTL adaptativo basado en frecuencia de cambio
if frequently_changing_data:
    ttl = 60  # 1 minuto
else:
    ttl = 3600  # 1 hora
```

### 4. **Manejo de Errores Robusto**
```python
async def fetch_with_retry(self, url: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return await self.fetch_json(url)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Backoff exponencial
```

## 🎯 Checklist de Migración

- [ ] Instalar dependencias asíncronas
- [ ] Crear clase que herede de `AsyncBaseScraper`
- [ ] Convertir métodos a `async def`
- [ ] Reemplazar `requests` con `aiohttp`
- [ ] Cambiar procesamiento secuencial a paralelo
- [ ] Actualizar file I/O a versión asíncrona
- [ ] Ajustar rate limiting y configuración
- [ ] Probar y comparar rendimiento
- [ ] Actualizar documentación

## 🔍 Troubleshooting

### Error: "RuntimeError: This event loop is already running"
**Solución**: Usa `asyncio.create_task()` en lugar de `asyncio.run()` dentro de funciones async.

### Error: "Session is closed"
**Solución**: Asegúrate de usar el context manager (`async with`) o llamar `setup()` y `cleanup()`.

### Rendimiento no mejora
**Verificar**:
- ¿Estás procesando en paralelo?
- ¿El rate limiting es muy restrictivo?
- ¿Hay bloqueos síncronos en el código?

## 📈 Resultados Esperados

Con la migración a async, deberías ver:

- **Waxpeer**: ~2-3x más rápido
- **Empire**: ~2-4x más rápido
- **Multiple scrapers**: ~5-10x más rápido (ejecución paralela)

El mayor beneficio se ve cuando:
- Ejecutas múltiples scrapers simultáneamente
- La API permite muchos requests paralelos
- Hay mucha latencia de red

¡Tu bot ahora es significativamente más rápido y eficiente! 🚀