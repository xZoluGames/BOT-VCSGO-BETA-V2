#!/usr/bin/env python3
"""
Script para ejecutar tests - BOT-VCSGO-BETA-V2

Proporciona una interfaz simple para ejecutar diferentes tipos de tests
con varias opciones de configuración.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

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


def print_header(title):
    """Imprime un header formateado"""
    print(f"\n{Colors.CYAN}{'='*60}")
    print(f"{Colors.BOLD}{title}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")


def check_dependencies():
    """Verifica que las dependencias de testing estén instaladas"""
    required_packages = ['pytest', 'pytest-cov', 'pytest-mock', 'pytest-asyncio']
    missing = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"{Colors.RED}❌ Faltan dependencias de testing:{Colors.RESET}")
        print(f"   {', '.join(missing)}")
        print(f"\n{Colors.YELLOW}Instala con:{Colors.RESET}")
        print(f"   pip install -r requirements-test.txt")
        return False
    
    return True


def run_tests(args):
    """Ejecuta los tests con la configuración especificada"""
    # Construir comando pytest
    cmd = ['pytest']
    
    # Agregar marcadores según el tipo de test
    if args.type == 'unit':
        cmd.extend(['-m', 'unit'])
    elif args.type == 'integration':
        cmd.extend(['-m', 'integration'])
    elif args.type == 'security':
        cmd.extend(['-m', 'security'])
    elif args.type == 'smoke':
        cmd.extend(['-m', 'smoke'])
    elif args.type == 'slow':
        cmd.extend(['-m', 'slow'])
    elif args.type == 'not-slow':
        cmd.extend(['-m', 'not slow'])
    
    # Verbosidad
    if args.verbose:
        cmd.append('-vv')
    elif args.quiet:
        cmd.append('-q')
    
    # Coverage
    if not args.no_coverage:
        cmd.extend(['--cov', '--cov-report=term-missing'])
        if args.html_coverage:
            cmd.append('--cov-report=html')
    
    # Parar en el primer fallo
    if args.fail_fast:
        cmd.append('-x')
    
    # Tests específicos
    if args.tests:
        cmd.extend(args.tests)
    
    # Argumentos adicionales de pytest
    if args.pytest_args:
        cmd.extend(args.pytest_args.split())
    
    # Ejecutar comando
    print(f"{Colors.BLUE}Ejecutando: {' '.join(cmd)}{Colors.RESET}\n")
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        return result.returncode
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrumpidos por el usuario{Colors.RESET}")
        return 1
    except Exception as e:
        print(f"{Colors.RED}Error ejecutando tests: {e}{Colors.RESET}")
        return 1


def run_specific_test_suites(args):
    """Ejecuta suites de tests específicas"""
    suites = {
        'config': 'tests/test_config_manager.py tests/test_path_manager.py',
        'scrapers': 'tests/test_scrapers/',
        'proxy': 'tests/test_proxy_manager.py',
        'cache': 'tests/test_cache_service.py',
        'analysis': 'tests/test_profitability_engine.py',
        'exceptions': 'tests/test_exceptions.py'
    }
    
    if args.suite in suites:
        args.tests = [suites[args.suite]]
        return run_tests(args)
    else:
        print(f"{Colors.RED}Suite desconocida: {args.suite}{Colors.RESET}")
        print(f"Suites disponibles: {', '.join(suites.keys())}")
        return 1


def generate_coverage_report():
    """Genera y abre el reporte de coverage HTML"""
    print(f"\n{Colors.BLUE}Generando reporte de coverage HTML...{Colors.RESET}")
    
    subprocess.run(['coverage', 'html'], capture_output=True)
    
    # Abrir en el navegador
    import webbrowser
    coverage_file = Path('htmlcov/index.html').absolute()
    if coverage_file.exists():
        print(f"{Colors.GREEN}✅ Reporte generado: {coverage_file}{Colors.RESET}")
        webbrowser.open(f'file://{coverage_file}')
    else:
        print(f"{Colors.RED}❌ No se pudo generar el reporte{Colors.RESET}")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Ejecutar tests para BOT-VCSGO-BETA-V2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python run_tests.py                    # Ejecutar todos los tests
  python run_tests.py --type unit        # Solo tests unitarios
  python run_tests.py --type integration # Solo tests de integración
  python run_tests.py --no-coverage      # Sin coverage
  python run_tests.py --fail-fast        # Parar en el primer fallo
  python run_tests.py tests/test_config_manager.py  # Test específico
  python run_tests.py --suite config     # Suite de configuración
        """
    )
    
    parser.add_argument(
        'tests',
        nargs='*',
        help='Tests específicos a ejecutar'
    )
    
    parser.add_argument(
        '--type',
        choices=['all', 'unit', 'integration', 'security', 'smoke', 'slow', 'not-slow'],
        default='all',
        help='Tipo de tests a ejecutar'
    )
    
    parser.add_argument(
        '--suite',
        choices=['config', 'scrapers', 'proxy', 'cache', 'analysis', 'exceptions'],
        help='Suite específica de tests'
    )
    
    parser.add_argument(
        '--no-coverage',
        action='store_true',
        help='Desactivar análisis de coverage'
    )
    
    parser.add_argument(
        '--html-coverage',
        action='store_true',
        help='Generar reporte HTML de coverage'
    )
    
    parser.add_argument(
        '--fail-fast',
        '-x',
        action='store_true',
        help='Parar en el primer test que falle'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Output detallado'
    )
    
    parser.add_argument(
        '--quiet',
        '-q',
        action='store_true',
        help='Output mínimo'
    )
    
    parser.add_argument(
        '--pytest-args',
        help='Argumentos adicionales para pytest (entre comillas)'
    )
    
    parser.add_argument(
        '--open-coverage',
        action='store_true',
        help='Abrir reporte de coverage al finalizar'
    )
    
    args = parser.parse_args()
    
    # Header
    print_header('🧪 BOT-VCSGO-BETA-V2 - Sistema de Testing')
    
    # Verificar dependencias
    if not check_dependencies():
        return 1
    
    # Información del entorno
    print(f"{Colors.BLUE}📁 Directorio: {Path.cwd()}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}\n")
    
    # Ejecutar tests
    if args.suite:
        result = run_specific_test_suites(args)
    else:
        result = run_tests(args)
    
    # Generar reporte si se solicitó
    if args.open_coverage and not args.no_coverage:
        generate_coverage_report()
    
    # Resumen final
    if result == 0:
        print(f"\n{Colors.GREEN}✅ Tests completados exitosamente{Colors.RESET}")
    else:
        print(f"\n{Colors.RED}❌ Algunos tests fallaron{Colors.RESET}")
    
    return result


if __name__ == '__main__':
    sys.exit(main())