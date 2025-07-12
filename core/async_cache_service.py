"""
Async Cache Service - BOT-VCSGO-BETA-V2

Servicio de cache asíncrono con características avanzadas:
- TTL adaptativo basado en frecuencia de acceso
- Compresión opcional para datos grandes
- Cache en memoria y disco
- Estadísticas de uso
- Limpieza automática
"""

import asyncio
import orjson
import time
import hashlib
import aiofiles
import zlib
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict, defaultdict
import logging
from dataclasses import dataclass, field
from enum import Enum


class CacheStrategy(Enum):
    """Estrategias de cache disponibles"""
    LRU = "lru"              # Least Recently Used
    LFU = "lfu"              # Least Frequently Used
    TTL = "ttl"              # Time To Live
    ADAPTIVE = "adaptive"    # TTL adaptativo basado en uso


@dataclass
class CacheEntry:
    """Entrada individual en el cache"""
    key: str
    value: Any
    size: int
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: float = 300.0
    compressed: bool = False
    
    def is_expired(self) -> bool:
        """Verifica si la entrada ha expirado"""
        return time.time() > (self.created_at + self.ttl)
    
    def update_access(self):
        """Actualiza estadísticas de acceso"""
        self.last_accessed = time.time()
        self.access_count += 1
    
    def get_age(self) -> float:
        """Obtiene la edad de la entrada en segundos"""
        return time.time() - self.created_at
    
    def get_adaptive_ttl(self) -> float:
        """Calcula TTL adaptativo basado en frecuencia de uso"""
        age = self.get_age()
        if age == 0:
            return self.ttl
        
        # Frecuencia de acceso por hora
        access_rate = (self.access_count / age) * 3600
        
        # Ajustar TTL basado en frecuencia
        if access_rate > 10:  # Muy frecuente
            return self.ttl * 2
        elif access_rate > 5:  # Frecuente
            return self.ttl * 1.5
        elif access_rate < 1:  # Poco frecuente
            return self.ttl * 0.5
        else:
            return self.ttl


@dataclass
class CacheStats:
    """Estadísticas del cache"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size: int = 0
    entries_count: int = 0
    compression_saved: int = 0
    
    def get_hit_rate(self) -> float:
        """Calcula la tasa de aciertos"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte las estadísticas a diccionario"""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{self.get_hit_rate():.2f}%",
            'evictions': self.evictions,
            'total_size_mb': f"{self.total_size / 1024 / 1024:.2f}",
            'entries': self.entries_count,
            'compression_saved_mb': f"{self.compression_saved / 1024 / 1024:.2f}"
        }


class AsyncCacheService:
    """
    Servicio de cache asíncrono con características avanzadas
    """
    
    def __init__(self,
                 cache_dir: Path,
                 platform: str,
                 max_memory_items: int = 1000,
                 max_memory_size: int = 100 * 1024 * 1024,  # 100MB
                 default_ttl: float = 300.0,
                 strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
                 compression_threshold: int = 10240,  # 10KB
                 enable_disk_cache: bool = True):
        """
        Inicializa el servicio de cache asíncrono
        
        Args:
            cache_dir: Directorio base del cache
            platform: Nombre de la plataforma
            max_memory_items: Máximo de items en memoria
            max_memory_size: Tamaño máximo en memoria (bytes)
            default_ttl: TTL por defecto en segundos
            strategy: Estrategia de cache
            compression_threshold: Umbral para comprimir (bytes)
            enable_disk_cache: Si habilitar cache en disco
        """
        self.cache_dir = Path(cache_dir)
        self.platform = platform
        self.max_memory_items = max_memory_items
        self.max_memory_size = max_memory_size
        self.default_ttl = default_ttl
        self.strategy = strategy
        self.compression_threshold = compression_threshold
        self.enable_disk_cache = enable_disk_cache
        
        # Cache en memoria
        self._memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._cache_lock = asyncio.Lock()
        
        # Estadísticas
        self.stats = CacheStats()
        
        # Logger
        self.logger = logging.getLogger(f"AsyncCache.{platform}")
        
        # Directorio de cache en disco
        if enable_disk_cache:
            self.disk_cache_dir = self.cache_dir / "data" / platform
            self.disk_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Task de limpieza
        self._cleanup_task: Optional[asyncio.Task] = None
        
        self.logger.info(f"AsyncCacheService inicializado para {platform}")
    
    async def setup(self):
        """Inicializa el servicio de cache"""
        # Iniciar task de limpieza periódica
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        self.logger.info("Cache service configurado")
    
    async def cleanup(self):
        """Limpia recursos del cache"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Guardar estadísticas
        await self._save_stats()
        
        self.logger.info(f"Cache service limpiado. Stats: {self.stats.to_dict()}")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Obtiene un valor del cache
        
        Args:
            key: Clave a buscar
            
        Returns:
            Valor si existe y no ha expirado, None si no
        """
        async with self._cache_lock:
            # Buscar en memoria
            entry = self._memory_cache.get(key)
            
            if entry:
                if not entry.is_expired():
                    # Hit en memoria
                    entry.update_access()
                    self.stats.hits += 1
                    
                    # Mover al final si es LRU
                    if self.strategy == CacheStrategy.LRU:
                        self._memory_cache.move_to_end(key)
                    
                    # Descomprimir si es necesario
                    value = entry.value
                    if entry.compressed:
                        value = self._decompress_value(value)
                    
                    return value
                else:
                    # Expirado, eliminar
                    del self._memory_cache[key]
                    self.stats.entries_count -= 1
            
            # Buscar en disco si está habilitado
            if self.enable_disk_cache:
                value = await self._get_from_disk(key)
                if value is not None:
                    self.stats.hits += 1
                    # Cargar en memoria para acceso rápido
                    await self._add_to_memory(key, value)
                    return value
            
            # Miss
            self.stats.misses += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """
        Guarda un valor en el cache
        
        Args:
            key: Clave para guardar
            value: Valor a guardar
            ttl: TTL opcional (None = usar default)
        """
        ttl = ttl or self.default_ttl
        
        async with self._cache_lock:
            # Calcular tamaño
            serialized = orjson.dumps(value)
            size = len(serialized)
            
            # Comprimir si es necesario
            compressed = False
            if size > self.compression_threshold:
                compressed_data = self._compress_value(serialized)
                if len(compressed_data) < size:
                    serialized = compressed_data
                    compressed = True
                    self.stats.compression_saved += size - len(compressed_data)
                    size = len(compressed_data)
            
            # Crear entrada
            entry = CacheEntry(
                key=key,
                value=serialized if compressed else value,
                size=size,
                created_at=time.time(),
                last_accessed=time.time(),
                ttl=ttl,
                compressed=compressed
            )
            
            # Verificar límites antes de agregar
            await self._ensure_space(size)
            
            # Agregar a memoria
            self._memory_cache[key] = entry
            self.stats.entries_count += 1
            self.stats.total_size += size
            
            # Guardar en disco si está habilitado
            if self.enable_disk_cache:
                await self._save_to_disk(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """
        Elimina una entrada del cache
        
        Args:
            key: Clave a eliminar
            
        Returns:
            True si se eliminó, False si no existía
        """
        async with self._cache_lock:
            if key in self._memory_cache:
                entry = self._memory_cache[key]
                del self._memory_cache[key]
                self.stats.entries_count -= 1
                self.stats.total_size -= entry.size
                
                # Eliminar de disco
                if self.enable_disk_cache:
                    await self._delete_from_disk(key)
                
                return True
            
            return False
    
    async def clear(self):
        """Limpia todo el cache"""
        async with self._cache_lock:
            self._memory_cache.clear()
            self.stats.entries_count = 0
            self.stats.total_size = 0
            
            # Limpiar disco
            if self.enable_disk_cache:
                await self._clear_disk_cache()
        
        self.logger.info("Cache limpiado completamente")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache"""
        stats = self.stats.to_dict()
        
        # Agregar info adicional
        async with self._cache_lock:
            stats['strategy'] = self.strategy.value
            stats['memory_entries'] = len(self._memory_cache)
            
            # Top 10 keys por acceso
            if self._memory_cache:
                sorted_entries = sorted(
                    self._memory_cache.values(),
                    key=lambda x: x.access_count,
                    reverse=True
                )[:10]
                
                stats['top_accessed_keys'] = [
                    {
                        'key': e.key,
                        'accesses': e.access_count,
                        'size_kb': f"{e.size / 1024:.2f}",
                        'age_minutes': f"{e.get_age() / 60:.1f}"
                    }
                    for e in sorted_entries
                ]
        
        return stats
    
    async def _ensure_space(self, required_size: int):
        """Asegura que hay espacio suficiente en el cache"""
        # Verificar límite de items
        while len(self._memory_cache) >= self.max_memory_items:
            await self._evict_one()
        
        # Verificar límite de tamaño
        while self.stats.total_size + required_size > self.max_memory_size:
            await self._evict_one()
    
    async def _evict_one(self):
        """Desaloja una entrada según la estrategia"""
        if not self._memory_cache:
            return
        
        key_to_evict = None
        
        if self.strategy == CacheStrategy.LRU:
            # Eliminar el menos recientemente usado
            key_to_evict = next(iter(self._memory_cache))
            
        elif self.strategy == CacheStrategy.LFU:
            # Eliminar el menos frecuentemente usado
            min_entry = min(self._memory_cache.values(), key=lambda x: x.access_count)
            key_to_evict = min_entry.key
            
        elif self.strategy == CacheStrategy.TTL:
            # Eliminar el más viejo
            oldest_entry = min(self._memory_cache.values(), key=lambda x: x.created_at)
            key_to_evict = oldest_entry.key
            
        elif self.strategy == CacheStrategy.ADAPTIVE:
            # Eliminar basado en score adaptativo
            def adaptive_score(entry: CacheEntry) -> float:
                age = entry.get_age()
                if age == 0:
                    return float('inf')
                # Score = accesos / edad (más alto = más valioso)
                return entry.access_count / age
            
            min_entry = min(self._memory_cache.values(), key=adaptive_score)
            key_to_evict = min_entry.key
        
        if key_to_evict:
            entry = self._memory_cache[key_to_evict]
            del self._memory_cache[key_to_evict]
            self.stats.entries_count -= 1
            self.stats.total_size -= entry.size
            self.stats.evictions += 1
    
    async def _add_to_memory(self, key: str, value: Any):
        """Agrega un valor a la memoria desde disco"""
        # Usar set para manejar límites y estadísticas
        await self.set(key, value)
    
    def _compress_value(self, data: bytes) -> bytes:
        """Comprime un valor usando zlib"""
        return zlib.compress(data, level=6)
    
    def _decompress_value(self, data: bytes) -> Any:
        """Descomprime un valor y lo deserializa"""
        decompressed = zlib.decompress(data)
        return orjson.loads(decompressed)
    
    def _get_disk_path(self, key: str) -> Path:
        """Obtiene la ruta en disco para una clave"""
        # Usar hash para evitar problemas con nombres de archivo
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.disk_cache_dir / f"{key_hash}.cache"
    
    async def _save_to_disk(self, key: str, value: Any, ttl: float):
        """Guarda un valor en disco"""
        if not self.enable_disk_cache:
            return
        
        try:
            disk_data = {
                'key': key,
                'value': value,
                'created_at': time.time(),
                'ttl': ttl
            }
            
            path = self._get_disk_path(key)
            async with aiofiles.open(path, 'wb') as f:
                await f.write(orjson.dumps(disk_data))
                
        except Exception as e:
            self.logger.error(f"Error guardando en disco: {e}")
    
    async def _get_from_disk(self, key: str) -> Optional[Any]:
        """Obtiene un valor del disco"""
        if not self.enable_disk_cache:
            return None
        
        try:
            path = self._get_disk_path(key)
            if not path.exists():
                return None
            
            async with aiofiles.open(path, 'rb') as f:
                data = await f.read()
            
            disk_data = orjson.loads(data)
            
            # Verificar TTL
            age = time.time() - disk_data['created_at']
            if age > disk_data['ttl']:
                # Expirado, eliminar
                await self._delete_from_disk(key)
                return None
            
            return disk_data['value']
            
        except Exception as e:
            self.logger.error(f"Error leyendo de disco: {e}")
            return None
    
    async def _delete_from_disk(self, key: str):
        """Elimina un valor del disco"""
        if not self.enable_disk_cache:
            return
        
        try:
            path = self._get_disk_path(key)
            if path.exists():
                path.unlink()
        except Exception as e:
            self.logger.error(f"Error eliminando de disco: {e}")
    
    async def _clear_disk_cache(self):
        """Limpia todo el cache en disco"""
        if not self.enable_disk_cache:
            return
        
        try:
            for cache_file in self.disk_cache_dir.glob("*.cache"):
                cache_file.unlink()
        except Exception as e:
            self.logger.error(f"Error limpiando cache de disco: {e}")
    
    async def _periodic_cleanup(self):
        """Task periódica de limpieza"""
        while True:
            try:
                await asyncio.sleep(300)  # Cada 5 minutos
                
                async with self._cache_lock:
                    # Eliminar entradas expiradas
                    expired_keys = []
                    for key, entry in self._memory_cache.items():
                        if entry.is_expired():
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        await self.delete(key)
                    
                    if expired_keys:
                        self.logger.info(f"Limpieza: eliminadas {len(expired_keys)} entradas expiradas")
                    
                    # Ajustar TTL adaptativo
                    if self.strategy == CacheStrategy.ADAPTIVE:
                        for entry in self._memory_cache.values():
                            entry.ttl = entry.get_adaptive_ttl()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error en limpieza periódica: {e}")
    
    async def _save_stats(self):
        """Guarda estadísticas del cache"""
        try:
            stats_file = self.cache_dir / "stats" / f"{self.platform}_cache_stats.json"
            stats_file.parent.mkdir(exist_ok=True)
            
            stats_data = {
                'timestamp': datetime.now().isoformat(),
                'platform': self.platform,
                'stats': self.stats.to_dict()
            }
            
            async with aiofiles.open(stats_file, 'wb') as f:
                await f.write(orjson.dumps(stats_data, option=orjson.OPT_INDENT_2))
                
        except Exception as e:
            self.logger.error(f"Error guardando estadísticas: {e}")