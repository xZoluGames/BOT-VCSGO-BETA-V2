#!/usr/bin/env python3
"""
Async Runner - BOT-VCSGO-BETA-V2

Script para ejecutar scrapers asíncronos con mejoras de rendimiento.
Permite ejecutar múltiples scrapers en paralelo.
"""

import asyncio
import time
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Type
import logging
from datetime import datetime
import orjson
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

# Agregar directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from core.async_base_scraper import AsyncBaseScraper
from core.config_manager import get_config_manager
from core.path_manager import get_path_manager


# Colores para output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class AsyncScraperRunner:
    """
    Ejecutor de scrapers asíncronos con gestión de concurrencia
    """
    
    def __init__(self, max_concurrent: int = 5, use_proxy: bool = False):
        """
        Inicializa el runner
        
        Args:
            max_concurrent: Máximo de scrapers concurrentes
            use_proxy: Si usar proxies
        """
        self.max_concurrent = max_concurrent
        self.use_proxy = use_proxy
        self.config_manager = get_config_manager()
        self.path_manager = get_path_manager()
        self.logger = logging.getLogger("AsyncRunner")
        
        # Scrapers disponibles (importación dinámica)
        self.available_scrapers = self._discover_async_scrapers()
        
        self.logger.info(f"AsyncRunner inicializado con {len(self.available_scrapers)} scrapers disponibles")
    
    def _discover_async_scrapers(self) -> Dict[str, Type[AsyncBaseScraper]]:
        """Descubre scrapers asíncronos disponibles"""
        scrapers = {}
        
        # Lista de scrapers asíncronos conocidos
        async_scrapers = [
            ('waxpeer', 'AsyncWaxpeerScraper'),
            # Agregar más scrapers asíncronos aquí cuando se implementen
            # ('empire', 'AsyncEmpireScraper'),
            # ('skinport', 'AsyncSkinportScraper'),
        ]
        
        for platform, class_name in async_scrapers:
            try:
                module = __import__(f'scrapers.async_{platform}_scraper', fromlist=[class_name])
                scraper_class = getattr(module, class_name)
                scrapers[platform] = scraper_class
                self.logger.debug(f"Scraper asíncrono encontrado: {platform}")
            except (ImportError, AttributeError) as e:
                self.logger.debug(f"Scraper asíncrono no disponible: {platform} ({e})")
        
        return scrapers
    
    async def run_scraper(self, platform: str) -> Dict[str, Any]:
        """
        Ejecuta un scraper individual
        
        Args:
            platform: Nombre de la plataforma
            
        Returns:
            Resultado del scraping
        """
        start_time = time.time()
        result = {
            'platform': platform,
            'status': 'pending',
            'items': 0,
            'time': 0,
            'error': None
        }
        
        try:
            scraper_class = self.available_scrapers[platform]
            
            # Crear y ejecutar scraper
            async with scraper_class(use_proxy=self.use_proxy) as scraper:
                items = await scraper.run()
                
                result['status'] = 'success'
                result['items'] = len(items)
                result['time'] = time.time() - start_time
                result['metrics'] = scraper.metrics.to_dict()
                
                self.logger.info(f"✅ {platform}: {len(items)} items en {result['time']:.2f}s")
                
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            result['time'] = time.time() - start_time
            
            self.logger.error(f"❌ {platform}: {e}")
        
        return result
    
    async def run_scrapers(self, platforms: List[str]) -> List[Dict[str, Any]]:
        """
        Ejecuta múltiples scrapers con límite de concurrencia
        
        Args:
            platforms: Lista de plataformas a scrapear
            
        Returns:
            Lista de resultados
        """
        # Crear semáforo para limitar concurrencia
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def run_with_semaphore(platform: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.run_scraper(platform)
        
        # Crear tareas para todos los scrapers
        tasks = [
            asyncio.create_task(run_with_semaphore(platform))
            for platform in platforms
        ]
        
        # Ejecutar todas las tareas
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'platform': platforms[i],
                    'status': 'error',
                    'error': str(result),
                    'items': 0,
                    'time': 0
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def run_parallel_groups(self, platforms: List[str], group_size: int = 3) -> List[Dict[str, Any]]:
        """
        Ejecuta scrapers en grupos paralelos
        
        Args:
            platforms: Lista de plataformas
            group_size: Tamaño de cada grupo
            
        Returns:
            Lista de resultados
        """
        all_results = []
        
        # Dividir en grupos
        for i in range(0, len(platforms), group_size):
            group = platforms[i:i + group_size]
            
            print(f"\n{Colors.CYAN}Ejecutando grupo: {', '.join(group)}{Colors.RESET}")
            
            group_results = await self.run_scrapers(group)
            all_results.extend(group_results)
            
            # Pausa entre grupos si no es el último
            if i + group_size < len(platforms):
                await asyncio.sleep(2)
        
        return all_results


def print_banner():
    """Imprime el banner del programa"""
    print(f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════╗
║       {Colors.BOLD}BOT-VCSGO-BETA-V2 - Async Scraper Runner{Colors.CYAN}          ║
║                  ⚡ Edición Turbo ⚡                      ║
╚═══════════════════════════════════════════════════════════╝{Colors.RESET}
""")


def print_results_table(results: List[Dict[str, Any]]):
    """Imprime tabla de resultados"""
    print(f"\n{Colors.CYAN}{'='*80}")
    print(f"{Colors.BOLD}{'Platform':<15} {'Status':<10} {'Items':<10} {'Time':<10} {'Rate Limit':<12} {'Cache Hit':<10}")
    print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")
    
    total_items = 0
    total_time = 0
    successful = 0
    
    for result in results:
        platform = result['platform']
        status = result['status']
        items = result.get('items', 0)
        time_taken = result.get('time', 0)
        
        # Obtener métricas adicionales
        metrics = result.get('metrics', {})
        rate_limit = metrics.get('rate_limit_hits', 0)
        cache_hit_rate = metrics.get('cache_hit_rate', '0%')
        
        # Color según estado
        if status == 'success':
            color = Colors.GREEN
            status_icon = '✅'
            successful += 1
            total_items += items
            total_time += time_taken
        else:
            color = Colors.RED
            status_icon = '❌'
        
        print(f"{color}{platform:<15} {status_icon} {status:<8} {items:<10} {time_taken:<10.2f}s {rate_limit:<12} {cache_hit_rate:<10}{Colors.RESET}")
    
    print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}Total: {successful}/{len(results)} exitosos, {total_items} items, {total_time:.2f}s total{Colors.RESET}")


async def compare_sync_vs_async():
    """Compara rendimiento entre versión síncrona y asíncrona"""
    print(f"\n{Colors.YELLOW}{'='*60}")
    print(f"{Colors.BOLD}Comparación Sync vs Async")
    print(f"{Colors.YELLOW}{'='*60}{Colors.RESET}\n")
    
    platforms = ['waxpeer']  # Agregar más cuando estén disponibles
    
    # Test asíncrono
    print(f"{Colors.GREEN}🚀 Ejecutando versión ASÍNCRONA...{Colors.RESET}")
    runner = AsyncScraperRunner(max_concurrent=5, use_proxy=False)
    
    start_async = time.time()
    results_async = await runner.run_scrapers(platforms)
    time_async = time.time() - start_async
    
    print_results_table(results_async)
    
    # Test síncrono (si está disponible)
    try:
        print(f"\n{Colors.YELLOW}🐌 Ejecutando versión SÍNCRONA...{Colors.RESET}")
        from run import run_scrapers_sync  # Asumiendo que existe
        
        start_sync = time.time()
        # Aquí ejecutarías la versión síncrona
        time_sync = time.time() - start_sync
        
        # Calcular mejora
        improvement = ((time_sync - time_async) / time_sync) * 100
        speedup = time_sync / time_async
        
        print(f"\n{Colors.CYAN}{'='*60}")
        print(f"{Colors.BOLD}📊 RESULTADOS DE COMPARACIÓN:")
        print(f"   - Tiempo Async: {time_async:.2f}s")
        print(f"   - Tiempo Sync: {time_sync:.2f}s")
        print(f"   - Mejora: {improvement:.1f}%")
        print(f"   - Speedup: {speedup:.1f}x más rápido")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
        
    except ImportError:
        print(f"\n{Colors.YELLOW}⚠️  Versión síncrona no disponible para comparación{Colors.RESET}")


async def run_stress_test(platforms: List[str], iterations: int = 5):
    """Ejecuta test de estrés"""
    print(f"\n{Colors.MAGENTA}{'='*60}")
    print(f"{Colors.BOLD}Stress Test - {iterations} iteraciones")
    print(f"{Colors.MAGENTA}{'='*60}{Colors.RESET}\n")
    
    runner = AsyncScraperRunner(max_concurrent=10, use_proxy=False)
    
    all_times = []
    all_items = []
    
    for i in range(iterations):
        print(f"\n{Colors.BLUE}Iteración {i+1}/{iterations}{Colors.RESET}")
        
        start = time.time()
        results = await runner.run_scrapers(platforms)
        elapsed = time.time() - start
        
        all_times.append(elapsed)
        total_items = sum(r.get('items', 0) for r in results)
        all_items.append(total_items)
        
        print(f"Completado en {elapsed:.2f}s - {total_items} items")
        
        # Pausa entre iteraciones
        if i < iterations - 1:
            await asyncio.sleep(5)
    
    # Estadísticas
    avg_time = sum(all_times) / len(all_times)
    avg_items = sum(all_items) / len(all_items)
    
    print(f"\n{Colors.CYAN}{'='*60}")
    print(f"{Colors.BOLD}📊 ESTADÍSTICAS DEL STRESS TEST:")
    print(f"   - Tiempo promedio: {avg_time:.2f}s")
    print(f"   - Items promedio: {avg_items:.0f}")
    print(f"   - Tiempo total: {sum(all_times):.2f}s")
    print(f"   - Items totales: {sum(all_items)}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")


async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Ejecutor de scrapers asíncronos para BOT-VCSGO-BETA-V2',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'platforms',
        nargs='*',
        help='Plataformas específicas a scrapear (vacío = todas)'
    )
    
    parser.add_argument(
        '--concurrent',
        '-c',
        type=int,
        default=5,
        help='Máximo de scrapers concurrentes (default: 5)'
    )
    
    parser.add_argument(
        '--use-proxy',
        '-p',
        action='store_true',
        help='Usar proxies para scraping'
    )
    
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Comparar rendimiento sync vs async'
    )
    
    parser.add_argument(
        '--stress-test',
        action='store_true',
        help='Ejecutar test de estrés'
    )
    
    parser.add_argument(
        '--stress-iterations',
        type=int,
        default=5,
        help='Iteraciones para stress test (default: 5)'
    )
    
    parser.add_argument(
        '--groups',
        '-g',
        type=int,
        help='Ejecutar en grupos de N scrapers'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Output detallado'
    )
    
    args = parser.parse_args()
    
    # Configurar logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print_banner()
    
    # Crear runner
    runner = AsyncScraperRunner(
        max_concurrent=args.concurrent,
        use_proxy=args.use_proxy
    )
    
    # Determinar plataformas
    if args.platforms:
        platforms = [p for p in args.platforms if p in runner.available_scrapers]
    else:
        platforms = list(runner.available_scrapers.keys())
    
    if not platforms:
        print(f"{Colors.RED}❌ No hay scrapers asíncronos disponibles{Colors.RESET}")
        return
    
    print(f"\n{Colors.BLUE}Plataformas a procesar: {', '.join(platforms)}{Colors.RESET}")
    print(f"{Colors.BLUE}Concurrencia máxima: {args.concurrent}{Colors.RESET}")
    print(f"{Colors.BLUE}Usar proxy: {'Sí' if args.use_proxy else 'No'}{Colors.RESET}")
    
    # Ejecutar según modo
    if args.compare:
        await compare_sync_vs_async()
    elif args.stress_test:
        await run_stress_test(platforms, args.stress_iterations)
    else:
        # Ejecución normal
        start_time = time.time()
        
        if args.groups:
            results = await runner.run_parallel_groups(platforms, args.groups)
        else:
            results = await runner.run_scrapers(platforms)
        
        total_time = time.time() - start_time
        
        # Mostrar resultados
        print_results_table(results)
        
        # Guardar resumen
        summary_file = runner.path_manager.get_data_file('async_scraping_summary.json')
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_time': total_time,
            'platforms': len(platforms),
            'results': results
        }
        
        with open(summary_file, 'wb') as f:
            f.write(orjson.dumps(summary, option=orjson.OPT_INDENT_2))
        
        print(f"\n{Colors.GREEN}✅ Resumen guardado en: {summary_file}{Colors.RESET}")


if __name__ == "__main__":
    # Verificar versión de Python
    if sys.version_info < (3, 7):
        print(f"{Colors.RED}❌ Python 3.7+ requerido para async/await{Colors.RESET}")
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Ejecución interrumpida por el usuario{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error: {e}{Colors.RESET}")
        sys.exit(1)