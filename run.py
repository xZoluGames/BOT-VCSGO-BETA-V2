"""
BOT-vCSGO-Beta V2 - Script Principal

Script simplificado para ejecutar scrapers de CS:GO.
Enfoque personal, simple y directo.

Uso:
    python run.py                     # Mostrar ayuda
    python run.py waxpeer             # Ejecutar scraper específico
    python run.py all                 # Ejecutar todos los scrapers
    python run.py --list              # Listar scrapers disponibles
    python run.py waxpeer --loop      # Ejecutar en bucle infinito
    python run.py --cache-stats       # Ver estadísticas de cache
"""

import sys
import argparse
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Agregar el directorio actual al path
sys.path.append(str(Path(__file__).parent))

# Importar scrapers
from scrapers.waxpeer_scraper import WaxpeerScraper
from scrapers.skinport_scraper import SkinportScraper
from scrapers.csdeals_scraper import CSDealsScraper
from core.cache_service import get_cache_service

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bot_v2")

# Registro de scrapers disponibles
SCRAPERS = {
    'waxpeer': {
        'class': WaxpeerScraper,
        'description': 'Waxpeer.com - API rápida, sin proxy necesario',
        'proxy_recommended': False
    },
    'skinport': {
        'class': SkinportScraper,
        'description': 'Skinport.com - API pública, muy confiable',
        'proxy_recommended': False
    },
    'csdeals': {
        'class': CSDealsScraper,
        'description': 'CS.deals - API con validación success',
        'proxy_recommended': False
    }
}

# Grupos de scrapers
SCRAPER_GROUPS = {
    'fast': ['waxpeer', 'skinport'],
    'api': ['waxpeer', 'skinport', 'csdeals'],
    'all': list(SCRAPERS.keys())
}


class BotRunner:
    """
    Ejecutor principal del bot V2
    """
    
    def __init__(self):
        """
        Inicializa el ejecutor
        """
        self.cache_service = get_cache_service()
        self.proxy_list = self._load_proxy_list()
        
        logger.info("🚀 BOT-vCSGO-Beta V2 inicializado")
        if self.proxy_list:
            logger.info(f"📡 Cargados {len(self.proxy_list)} proxies")
    
    def _load_proxy_list(self) -> List[str]:
        """
        Carga la lista de proxies desde proxy.txt
        """
        proxy_file = Path(__file__).parent / "proxy.txt"
        if not proxy_file.exists():
            return []
        
        try:
            with open(proxy_file, 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]
            return proxies
        except Exception as e:
            logger.warning(f"Error cargando proxies: {e}")
            return []
    
    def list_scrapers(self):
        """
        Lista todos los scrapers disponibles
        """
        print("\n📋 Scrapers Disponibles:")
        print("=" * 50)
        
        for name, info in SCRAPERS.items():
            proxy_status = "🔒 Proxy recomendado" if info['proxy_recommended'] else "🌐 Sin proxy"
            print(f"  {name:12} - {info['description']}")
            print(f"{'':14} {proxy_status}")
        
        print(f"\n📦 Grupos Disponibles:")
        for group, scrapers in SCRAPER_GROUPS.items():
            print(f"  {group:12} - {', '.join(scrapers)}")
    
    def show_cache_stats(self):
        """
        Muestra estadísticas del cache
        """
        stats = self.cache_service.get_cache_stats()
        
        print("\n📊 Estadísticas del Cache:")
        print("=" * 40)
        print(f"  Items en memoria:     {stats['memory_items']}/{stats['memory_max']}")
        print(f"  Imágenes locales:     {stats['local_images']}")
        print(f"  Imágenes externas:    {stats['external_images']}")
        print(f"  Total imágenes:       {stats['total_images']}")
        print(f"  Archivos de datos:    {stats['data_files']}")
        print(f"  Directorio cache:     {stats['cache_dir']}")
        
        if stats['external_cache_dir']:
            print(f"  Cache externo:        {stats['external_cache_dir']}")
        
        # Mostrar tamaño aproximado
        total_images = stats['total_images']
        if total_images > 0:
            estimated_size_mb = total_images * 0.12  # ~120KB por imagen promedio
            print(f"  Tamaño estimado:      {estimated_size_mb:.1f} MB")
    
    def run_scraper(self, scraper_name: str, use_proxy: bool = False, loop: bool = False) -> bool:
        """
        Ejecuta un scraper específico
        
        Args:
            scraper_name: Nombre del scraper
            use_proxy: Si usar proxy
            loop: Si ejecutar en bucle infinito
            
        Returns:
            True si se ejecutó exitosamente
        """
        if scraper_name not in SCRAPERS:
            logger.error(f"❌ Scraper '{scraper_name}' no encontrado")
            return False
        
        scraper_info = SCRAPERS[scraper_name]
        
        try:
            # Crear instancia del scraper
            scraper_class = scraper_info['class']
            scraper = scraper_class(
                use_proxy=use_proxy,
                proxy_list=self.proxy_list if use_proxy else None
            )
            
            print(f"\n🎯 Ejecutando {scraper_name}...")
            print(f"   Descripción: {scraper_info['description']}")
            print(f"   Proxy: {'Sí' if use_proxy else 'No'}")
            print(f"   Modo: {'Bucle infinito' if loop else 'Una vez'}")
            print("-" * 50)
            
            if loop:
                # Ejecutar en bucle infinito
                scraper.run_forever()
            else:
                # Ejecutar una vez
                data = scraper.run_once()
                
                # Mostrar resultados
                print(f"\n✅ Scraper completado:")
                print(f"   Items obtenidos: {len(data)}")
                
                stats = scraper.get_stats()
                print(f"   Requests realizados: {stats['requests_made']}")
                print(f"   Requests fallidos: {stats['requests_failed']}")
                
                if data:
                    print(f"\n📋 Primeros 3 items:")
                    for item in data[:3]:
                        print(f"   - {item['Item']}: ${item['Price']}")
            
            return True
            
        except KeyboardInterrupt:
            print(f"\n🛑 {scraper_name} detenido por el usuario")
            return True
        except Exception as e:
            logger.error(f"❌ Error ejecutando {scraper_name}: {e}")
            return False
    
    def run_multiple_scrapers(self, scraper_names: List[str], use_proxy: bool = False) -> bool:
        """
        Ejecuta múltiples scrapers secuencialmente
        """
        success_count = 0
        total_items = 0
        
        print(f"\n🎯 Ejecutando {len(scraper_names)} scrapers...")
        print("=" * 60)
        
        for scraper_name in scraper_names:
            if scraper_name not in SCRAPERS:
                logger.warning(f"⚠️ Scraper '{scraper_name}' no encontrado, saltando...")
                continue
            
            try:
                scraper_info = SCRAPERS[scraper_name]
                scraper_class = scraper_info['class']
                scraper = scraper_class(
                    use_proxy=use_proxy,
                    proxy_list=self.proxy_list if use_proxy else None
                )
                
                print(f"\n▶️ {scraper_name}...")
                data = scraper.run_once()
                
                if data:
                    print(f"   ✅ {len(data)} items obtenidos")
                    total_items += len(data)
                    success_count += 1
                else:
                    print(f"   ⚠️ No se obtuvieron datos")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print(f"\n📊 Resumen:")
        print(f"   Scrapers exitosos: {success_count}/{len(scraper_names)}")
        print(f"   Total items: {total_items}")
        
        return success_count > 0


def main():
    """
    Función principal
    """
    parser = argparse.ArgumentParser(
        description="BOT-vCSGO-Beta V2 - Scraper simplificado de CS:GO",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python run.py --list              # Listar scrapers disponibles
  python run.py waxpeer             # Ejecutar Waxpeer una vez
  python run.py waxpeer --loop      # Ejecutar Waxpeer en bucle
  python run.py all                 # Ejecutar todos los scrapers
  python run.py fast                # Ejecutar grupo 'fast'
  python run.py --cache-stats       # Ver estadísticas de cache
  python run.py waxpeer --proxy     # Usar proxy (si está disponible)
        """
    )
    
    parser.add_argument(
        'target', 
        nargs='?',
        help='Scraper o grupo a ejecutar (ej: waxpeer, all, fast)'
    )
    parser.add_argument(
        '--list', 
        action='store_true',
        help='Listar scrapers disponibles'
    )
    parser.add_argument(
        '--cache-stats', 
        action='store_true',
        help='Mostrar estadísticas del cache'
    )
    parser.add_argument(
        '--proxy', 
        action='store_true',
        help='Usar proxy (si está configurado)'
    )
    parser.add_argument(
        '--loop', 
        action='store_true',
        help='Ejecutar en bucle infinito'
    )
    
    args = parser.parse_args()
    
    # Crear ejecutor
    runner = BotRunner()
    
    # Procesar argumentos
    if args.list:
        runner.list_scrapers()
        return
    
    if args.cache_stats:
        runner.show_cache_stats()
        return
    
    if not args.target:
        parser.print_help()
        return
    
    # Ejecutar target
    target = args.target.lower()
    
    if target in SCRAPERS:
        # Scraper individual
        runner.run_scraper(target, use_proxy=args.proxy, loop=args.loop)
    elif target in SCRAPER_GROUPS:
        # Grupo de scrapers
        if args.loop:
            print("❌ Error: No se puede usar --loop con grupos de scrapers")
            return
        
        scrapers = SCRAPER_GROUPS[target]
        runner.run_multiple_scrapers(scrapers, use_proxy=args.proxy)
    else:
        print(f"❌ Error: '{target}' no encontrado")
        print("   Usa --list para ver opciones disponibles")


if __name__ == "__main__":
    main()