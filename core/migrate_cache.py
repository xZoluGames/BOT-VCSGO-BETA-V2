"""
Cache Migration Script - BOT-vCSGO-Beta V2

Script para migrar datos del cache existente al formato V2:
- Preserva los 15,414 iconos de skins (1.7GB) 
- Migra datos de plataformas existentes
- Convierte al formato orjson V2
- Mantiene estructura y metadatos
"""

import os
import shutil
import orjson
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Any
import json

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cache_migration")


class CacheMigrator:
    """
    Migrador de cache de v1 a v2
    """
    
    def __init__(self, 
                 old_project_path: str = "/mnt/c/Users/Zolu/Documents/BOT-vCSGO-Beta",
                 new_project_path: str = "/mnt/c/Users/Zolu/Documents/BOT-VCSGO-BETA-V2"):
        """
        Inicializa el migrador
        
        Args:
            old_project_path: Ruta del proyecto original
            new_project_path: Ruta del proyecto V2
        """
        self.old_project = Path(old_project_path)
        self.new_project = Path(new_project_path)
        
        # Directorios relevantes
        self.old_data_dir = self.old_project / "data"
        self.new_data_dir = self.new_project / "data"
        self.new_cache_dir = self.new_data_dir / "cache"
        
        # Cache de iconos externo
        self.external_cache_dir = Path("/mnt/c/Users/Zolu/Documents/csgo ico cache")
        
        # Asegurar que directorios existan
        self.new_data_dir.mkdir(exist_ok=True)
        self.new_cache_dir.mkdir(exist_ok=True)
        (self.new_cache_dir / "images").mkdir(exist_ok=True)
        (self.new_cache_dir / "data").mkdir(exist_ok=True)
        
        logger.info(f"Migrador inicializado")
        logger.info(f"  Proyecto original: {self.old_project}")
        logger.info(f"  Proyecto V2: {self.new_project}")
    
    def analyze_existing_data(self) -> Dict[str, Any]:
        """
        Analiza los datos existentes para migración
        """
        analysis = {
            'icon_cache': {'exists': False, 'count': 0, 'size_mb': 0},
            'platform_data': {'exists': False, 'files': []},
            'database': {'exists': False, 'size_mb': 0},
            'other_cache': {'exists': False, 'files': []}
        }
        
        # Analizar cache de iconos
        if self.external_cache_dir.exists():
            images_dir = self.external_cache_dir / "images"
            if images_dir.exists():
                image_files = list(images_dir.glob("*.jpg"))
                total_size = sum(f.stat().st_size for f in image_files)
                
                analysis['icon_cache'] = {
                    'exists': True,
                    'count': len(image_files),
                    'size_mb': round(total_size / (1024 * 1024), 2),
                    'path': str(images_dir)
                }
        
        # Analizar datos de plataformas en el proyecto original
        if self.old_data_dir.exists():
            # Buscar archivos JSON de plataformas
            platform_files = list(self.old_data_dir.glob("*_data.json"))
            platform_files.extend(list(self.old_data_dir.glob("items/*.json")))
            
            if platform_files:
                analysis['platform_data'] = {
                    'exists': True,
                    'files': [str(f) for f in platform_files]
                }
            
            # Analizar base de datos
            db_file = self.old_data_dir / "csgo_arbitrage.db"
            if db_file.exists():
                analysis['database'] = {
                    'exists': True,
                    'size_mb': round(db_file.stat().st_size / (1024 * 1024), 2),
                    'path': str(db_file)
                }
            
            # Otros archivos de cache
            cache_files = []
            if (self.old_data_dir / "cache").exists():
                cache_files = list((self.old_data_dir / "cache").glob("*"))
            
            if cache_files:
                analysis['other_cache'] = {
                    'exists': True,
                    'files': [str(f) for f in cache_files]
                }
        
        return analysis
    
    def migrate_icon_cache(self) -> bool:
        """
        Migra el cache de iconos al proyecto V2
        """
        logger.info("🖼️ Migrando cache de iconos...")
        
        if not self.external_cache_dir.exists():
            logger.warning("❌ No se encontró cache de iconos externo")
            return False
        
        images_dir = self.external_cache_dir / "images"
        if not images_dir.exists():
            logger.warning("❌ No se encontró directorio de imágenes")
            return False
        
        # Crear referencia al cache externo en lugar de copiar
        # (más eficiente que copiar 1.7GB)
        cache_ref_file = self.new_cache_dir / "external_icon_cache.txt"
        with open(cache_ref_file, 'w') as f:
            f.write(str(images_dir))
        
        # Crear algunos archivos de metadatos
        image_files = list(images_dir.glob("*.jpg"))
        metadata = {
            'source': 'BOT-vCSGO-Beta v1',
            'migrated_at': datetime.now().isoformat(),
            'total_images': len(image_files),
            'total_size_mb': round(sum(f.stat().st_size for f in image_files) / (1024 * 1024), 2),
            'external_path': str(images_dir)
        }
        
        metadata_file = self.new_cache_dir / "icon_cache_metadata.json"
        with open(metadata_file, 'wb') as f:
            f.write(orjson.dumps(metadata, option=orjson.OPT_INDENT_2))
        
        logger.info(f"✅ Cache de iconos referenciado: {len(image_files)} imágenes")
        return True
    
    def migrate_platform_data(self) -> bool:
        """
        Migra datos de plataformas al formato V2
        """
        logger.info("📊 Migrando datos de plataformas...")
        
        migrated_count = 0
        
        # Buscar archivos de datos en el proyecto original
        data_sources = []
        
        if self.old_data_dir.exists():
            # Archivos JSON directos
            data_sources.extend(list(self.old_data_dir.glob("*_data.json")))
            
            # Directorio items si existe
            items_dir = self.old_data_dir / "items"
            if items_dir.exists():
                data_sources.extend(list(items_dir.glob("*.json")))
        
        for source_file in data_sources:
            try:
                # Leer archivo original
                with open(source_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Determinar nombre de plataforma
                platform_name = source_file.stem.replace('_data', '')
                
                # Convertir a formato V2 con orjson
                v2_data = {
                    'platform': platform_name,
                    'migrated_from': str(source_file),
                    'migrated_at': datetime.now().isoformat(),
                    'data': data,
                    'item_count': len(data) if isinstance(data, list) else 0
                }
                
                # Guardar en formato V2
                output_file = self.new_data_dir / f"{platform_name}_data.json"
                with open(output_file, 'wb') as f:
                    f.write(orjson.dumps(v2_data, option=orjson.OPT_INDENT_2))
                
                logger.info(f"  ✅ {platform_name}: {len(data) if isinstance(data, list) else 'N/A'} items")
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"  ❌ Error migrando {source_file}: {e}")
        
        logger.info(f"✅ Migrados {migrated_count} archivos de datos de plataformas")
        return migrated_count > 0
    
    def create_migration_summary(self, analysis: Dict[str, Any]) -> bool:
        """
        Crea un resumen de la migración
        """
        summary = {
            'migration_completed_at': datetime.now().isoformat(),
            'source_project': str(self.old_project),
            'target_project': str(self.new_project),
            'analysis': analysis,
            'v2_features': {
                'simplified_architecture': True,
                'orjson_performance': True,
                'preserved_icon_cache': analysis['icon_cache']['exists'],
                'personal_use_optimized': True
            },
            'next_steps': [
                "Ejecutar scrapers individuales para probar funcionamiento",
                "Verificar acceso al cache de iconos",
                "Configurar intervalos de scraping según necesidades",
                "Usar run.py para control simplificado"
            ]
        }
        
        summary_file = self.new_project / "MIGRATION_SUMMARY.json"
        with open(summary_file, 'wb') as f:
            f.write(orjson.dumps(summary, option=orjson.OPT_INDENT_2))
        
        logger.info(f"✅ Resumen de migración guardado en {summary_file}")
        return True
    
    def run_migration(self) -> bool:
        """
        Ejecuta la migración completa
        """
        logger.info("🚀 Iniciando migración de BOT-vCSGO-Beta a V2...")
        
        # Analizar datos existentes
        analysis = self.analyze_existing_data()
        
        logger.info("📋 Análisis de datos existentes:")
        logger.info(f"  Cache de iconos: {analysis['icon_cache']['count']} archivos ({analysis['icon_cache']['size_mb']} MB)")
        logger.info(f"  Datos de plataformas: {len(analysis['platform_data']['files'])} archivos")
        logger.info(f"  Base de datos: {'Sí' if analysis['database']['exists'] else 'No'}")
        
        success = True
        
        # Migrar cache de iconos
        if analysis['icon_cache']['exists']:
            success &= self.migrate_icon_cache()
        else:
            logger.warning("⚠️ No se encontró cache de iconos para migrar")
        
        # Migrar datos de plataformas
        if analysis['platform_data']['exists']:
            success &= self.migrate_platform_data()
        else:
            logger.warning("⚠️ No se encontraron datos de plataformas para migrar")
        
        # Crear resumen
        self.create_migration_summary(analysis)
        
        if success:
            logger.info("🎉 ¡Migración completada exitosamente!")
            logger.info(f"   Proyecto V2 listo en: {self.new_project}")
        else:
            logger.warning("⚠️ Migración completada con algunos errores")
        
        return success


def main():
    """
    Función principal de migración
    """
    print("=== Migrador de Cache BOT-vCSGO-Beta V1 → V2 ===")
    print()
    
    # Rutas por defecto
    old_project = "/mnt/c/Users/Zolu/Documents/BOT-vCSGO-Beta"
    new_project = "/mnt/c/Users/Zolu/Documents/BOT-VCSGO-BETA-V2"
    
    # Verificar que existan los directorios
    if not Path(old_project).exists():
        print(f"❌ Error: Proyecto original no encontrado en {old_project}")
        return False
    
    if not Path(new_project).exists():
        print(f"❌ Error: Proyecto V2 no encontrado en {new_project}")
        return False
    
    # Crear migrador y ejecutar
    migrator = CacheMigrator(old_project, new_project)
    success = migrator.run_migration()
    
    if success:
        print("\n✅ ¡Migración exitosa!")
        print(f"   Tu proyecto V2 está listo en: {new_project}")
        print(f"   Los datos del cache han sido preservados")
        print(f"   Puedes ejecutar los scrapers con: python run.py")
    else:
        print("\n⚠️ Migración completada con errores")
        print(f"   Revisa los logs para más detalles")
    
    return success


if __name__ == "__main__":
    main()