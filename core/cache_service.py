"""
Cache Service - BOT-vCSGO-Beta V2

Sistema de cache simplificado que preserva datos existentes:
- Mantiene cache de iconos de skins existente (1.7GB, 15,414 archivos)
- Usa orjson para máximo rendimiento
- Cache permanente para imágenes
- Sistema de cache en memoria con LRU
- Enfoque personal y simplificado
"""

import os
import hashlib
import orjson
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from collections import OrderedDict
from datetime import datetime, timedelta
import requests
import time


class SimplifiedCacheV2:
    """
    Sistema de cache simplificado para BOT-vCSGO-Beta V2
    
    Funcionalidades:
    - Cache permanente de imágenes de skins
    - Cache en memoria con LRU para datos
    - Preservación de cache existente
    - Interfaz simple y eficiente
    - Usa orjson para performance
    """
    
    def __init__(self, cache_dir: str = "cache"):
        """
        Inicializa el sistema de cache
        
        Args:
            cache_dir: Directorio base para cache
        """
        self.cache_dir = Path(cache_dir)
        self.image_cache_dir = self.cache_dir / "images"
        self.data_cache_dir = self.cache_dir / "data"
        
        # Crear directorios si no existen
        self.cache_dir.mkdir(exist_ok=True)
        self.image_cache_dir.mkdir(exist_ok=True)
        self.data_cache_dir.mkdir(exist_ok=True)
        
        # Cache en memoria para datos (LRU)
        self.memory_cache = OrderedDict()
        self.max_memory_items = 1000
        self.cache_ttl = {}  # TTL para items en memoria
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("cache_v2")
        
        # Migrar cache existente si es la primera vez
        self._migrate_existing_cache()
        
        self.logger.info(f"Cache V2 inicializado en {self.cache_dir}")
    
    def _migrate_existing_cache(self):
        """
        Migra el cache existente de iconos a la estructura V2
        """
        # Buscar cache existente en ubicación original
        external_cache_paths = [
            Path("/mnt/c/Users/Zolu/Documents/csgo ico cache/images"),
            Path("../csgo ico cache/images"),  # Relativo
            Path("../../csgo ico cache/images")  # Más arriba
        ]
        
        existing_cache = None
        for path in external_cache_paths:
            if path.exists() and path.is_dir():
                existing_cache = path
                break
        
        if existing_cache:
            existing_files = list(existing_cache.glob("*.jpg"))
            self.logger.info(f"✅ Cache existente encontrado: {len(existing_files)} imágenes en {existing_cache}")
            
            # Crear symlink si no existe (más eficiente que copiar)
            symlink_target = self.image_cache_dir / "external_cache"
            if not symlink_target.exists():
                try:
                    # En Windows/WSL2 crear symlink puede no funcionar, usar método alternativo
                    symlink_target.symlink_to(existing_cache)
                    self.logger.info(f"✅ Symlink creado: {symlink_target} → {existing_cache}")
                except (OSError, NotImplementedError):
                    # Fallback: guardar ruta en archivo de configuración
                    config_file = self.cache_dir / "external_cache_path.txt"
                    with open(config_file, 'w') as f:
                        f.write(str(existing_cache))
                    self.logger.info(f"✅ Ruta de cache externa guardada en {config_file}")
            
            self.external_cache_path = existing_cache
        else:
            self.logger.info("ℹ️ No se encontró cache existente")
            self.external_cache_path = None
    
    def _get_external_cache_path(self) -> Optional[Path]:
        """
        Obtiene la ruta del cache externo
        """
        if hasattr(self, 'external_cache_path') and self.external_cache_path:
            return self.external_cache_path
        
        # Leer de archivo de configuración
        config_file = self.cache_dir / "external_cache_path.txt"
        if config_file.exists():
            with open(config_file, 'r') as f:
                path_str = f.read().strip()
                return Path(path_str) if path_str else None
        
        return None
    
    def _hash_key(self, key: str) -> str:
        """
        Genera hash MD5 para una clave
        """
        return hashlib.md5(key.encode()).hexdigest()
    
    def _is_expired(self, key: str) -> bool:
        """
        Verifica si un item en memoria ha expirado
        """
        if key not in self.cache_ttl:
            return False
        
        return datetime.now() > self.cache_ttl[key]
    
    def _cleanup_expired(self):
        """
        Limpia items expirados del cache en memoria
        """
        expired_keys = [
            key for key in self.cache_ttl 
            if self._is_expired(key)
        ]
        
        for key in expired_keys:
            self.memory_cache.pop(key, None)
            self.cache_ttl.pop(key, None)
    
    def get(self, key: str) -> Optional[Any]:
        """
        Obtiene un valor del cache (memoria → disco → None)
        
        Args:
            key: Clave del cache
            
        Returns:
            Valor cacheado o None si no existe
        """
        # Limpiar expirados
        self._cleanup_expired()
        
        # Buscar en memoria primero
        if key in self.memory_cache and not self._is_expired(key):
            # Mover al final (LRU)
            value = self.memory_cache.pop(key)
            self.memory_cache[key] = value
            return value
        
        # Buscar en disco
        cache_file = self.data_cache_dir / f"{self._hash_key(key)}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    data = orjson.loads(f.read())
                
                # Verificar TTL en disco
                if 'expires_at' in data:
                    expires_at = datetime.fromisoformat(data['expires_at'])
                    if datetime.now() > expires_at:
                        cache_file.unlink()  # Eliminar archivo expirado
                        return None
                
                # Cargar a memoria
                value = data['value']
                self.memory_cache[key] = value
                
                return value
                
            except Exception as e:
                self.logger.warning(f"Error leyendo cache de disco para {key}: {e}")
                return None
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """
        Guarda un valor en el cache (memoria + disco)
        
        Args:
            key: Clave del cache
            value: Valor a guardar
            ttl: Tiempo de vida en segundos
        """
        # Limpiar expirados
        self._cleanup_expired()
        
        # Guardar en memoria
        if len(self.memory_cache) >= self.max_memory_items:
            # Remover el más antiguo (LRU)
            oldest_key = next(iter(self.memory_cache))
            self.memory_cache.pop(oldest_key)
            self.cache_ttl.pop(oldest_key, None)
        
        self.memory_cache[key] = value
        self.cache_ttl[key] = datetime.now() + timedelta(seconds=ttl)
        
        # Guardar en disco asincrónicamente
        try:
            cache_file = self.data_cache_dir / f"{self._hash_key(key)}.json"
            data = {
                'value': value,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(seconds=ttl)).isoformat()
            }
            
            with open(cache_file, 'wb') as f:
                f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
                
        except Exception as e:
            self.logger.warning(f"Error guardando cache en disco para {key}: {e}")
    
    def get_image_path(self, steam_url: str) -> Optional[Path]:
        """
        Obtiene la ruta local de una imagen de skin
        
        Args:
            steam_url: URL de la imagen en Steam
            
        Returns:
            Path al archivo local o None si no existe
        """
        # Generar nombre de archivo usando hash MD5
        url_hash = self._hash_key(steam_url)
        filename = f"{url_hash}.jpg"
        
        # Buscar en cache nuevo
        local_path = self.image_cache_dir / filename
        if local_path.exists():
            return local_path
        
        # Buscar en cache externo (preservado)
        external_cache = self._get_external_cache_path()
        if external_cache:
            external_path = external_cache / filename
            if external_path.exists():
                return external_path
        
        return None
    
    def has_image(self, steam_url: str) -> bool:
        """
        Verifica si una imagen está en cache
        """
        return self.get_image_path(steam_url) is not None
    
    def cache_image(self, steam_url: str, max_retries: int = 3) -> bool:
        """
        Descarga y cachea una imagen de skin
        
        Args:
            steam_url: URL de la imagen en Steam
            max_retries: Máximo número de reintentos
            
        Returns:
            True si se descargó exitosamente
        """
        # Verificar si ya existe
        if self.has_image(steam_url):
            return True
        
        # Generar nombre de archivo
        url_hash = self._hash_key(steam_url)
        filename = f"{url_hash}.jpg"
        local_path = self.image_cache_dir / filename
        
        # Descargar imagen
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    steam_url,
                    timeout=30,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                )
                response.raise_for_status()
                
                # Guardar imagen
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                self.logger.info(f"✅ Imagen cacheada: {filename}")
                return True
                
            except Exception as e:
                self.logger.warning(f"Error descargando imagen (intento {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Esperar antes de reintentar
        
        self.logger.error(f"❌ Error descargando imagen después de {max_retries} intentos: {steam_url}")
        return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del cache
        """
        # Contar archivos en cache local
        local_images = len(list(self.image_cache_dir.glob("*.jpg")))
        local_data = len(list(self.data_cache_dir.glob("*.json")))
        
        # Contar archivos en cache externo
        external_images = 0
        external_cache = self._get_external_cache_path()
        if external_cache and external_cache.exists():
            external_images = len(list(external_cache.glob("*.jpg")))
        
        return {
            'memory_items': len(self.memory_cache),
            'memory_max': self.max_memory_items,
            'local_images': local_images,
            'external_images': external_images,
            'total_images': local_images + external_images,
            'data_files': local_data,
            'cache_dir': str(self.cache_dir),
            'external_cache_dir': str(external_cache) if external_cache else None
        }
    
    def clear_expired(self):
        """
        Limpia archivos expirados del disco
        """
        self._cleanup_expired()
        
        # Limpiar archivos expirados en disco
        cleaned = 0
        for cache_file in self.data_cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'rb') as f:
                    data = orjson.loads(f.read())
                
                if 'expires_at' in data:
                    expires_at = datetime.fromisoformat(data['expires_at'])
                    if datetime.now() > expires_at:
                        cache_file.unlink()
                        cleaned += 1
                        
            except Exception as e:
                self.logger.warning(f"Error procesando archivo de cache {cache_file}: {e}")
        
        self.logger.info(f"🧹 Limpieza completada: {cleaned} archivos eliminados")
        return cleaned


# Instancia global del cache
_cache_instance = None

def get_cache_service() -> SimplifiedCacheV2:
    """
    Obtiene la instancia global del servicio de cache
    """
    global _cache_instance
    if _cache_instance is None:
        # Usar el directorio data/cache dentro del proyecto
        cache_dir = Path(__file__).parent.parent / "data" / "cache"
        _cache_instance = SimplifiedCacheV2(str(cache_dir))
    
    return _cache_instance


def main():
    """
    Función de prueba del sistema de cache
    """
    print("=== Probando Sistema de Cache V2 ===")
    
    cache = get_cache_service()
    
    # Mostrar estadísticas
    stats = cache.get_cache_stats()
    print(f"\n📊 Estadísticas del Cache:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Prueba de datos
    print(f"\n🧪 Probando cache de datos...")
    cache.set("test_key", {"mensaje": "Hola Cache V2"}, ttl=60)
    retrieved = cache.get("test_key")
    print(f"   Guardado y recuperado: {retrieved}")
    
    # Prueba de imágenes (si hay cache externo)
    if stats['external_images'] > 0:
        print(f"\n🖼️ Cache de imágenes disponible:")
        print(f"   Total de imágenes: {stats['total_images']}")
        print(f"   Cache externo: {stats['external_cache_dir']}")
    
    print(f"\n✅ Sistema de cache V2 funcionando correctamente!")


if __name__ == "__main__":
    main()