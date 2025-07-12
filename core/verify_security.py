#!/usr/bin/env python3
"""
Script de verificación de seguridad - BOT-VCSGO-BETA-V2

Verifica que todas las mejoras de seguridad estén implementadas correctamente:
- Variables de entorno configuradas
- Sin claves API hardcodeadas
- Sin rutas hardcodeadas
- Configuración segura funcionando
"""

import os
import sys
from pathlib import Path
import json
import re
from typing import List, Dict, Tuple
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

def print_header():
    """Imprime el header del script"""
    print(f"\n{Colors.CYAN}{'='*60}")
    print(f"{Colors.BOLD}🔒 Verificación de Seguridad - BOT-VCSGO-BETA-V2")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")

def print_section(title):
    """Imprime un título de sección"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}▶ {title}{Colors.RESET}")
    print(f"{Colors.BLUE}{'─'*50}{Colors.RESET}")

def print_check(passed: bool, message: str, details: str = None):
    """Imprime el resultado de una verificación"""
    icon = "✅" if passed else "❌"
    color = Colors.GREEN if passed else Colors.RED
    print(f"{color}{icon} {message}{Colors.RESET}")
    if details:
        print(f"   {Colors.YELLOW}→ {details}{Colors.RESET}")

def find_project_root():
    """Encuentra la raíz del proyecto"""
    current = Path(__file__).resolve().parent
    
    while current != current.parent:
        if (current / "config").exists() and (current / "core").exists():
            return current
        current = current.parent
    
    return Path.cwd()

def check_env_file(root_path: Path) -> Tuple[bool, List[str]]:
    """Verifica la existencia y contenido del archivo .env"""
    env_file = root_path / ".env"
    missing_vars = []
    
    if not env_file.exists():
        return False, ["Archivo .env no encontrado"]
    
    # Variables requeridas
    required_vars = [
        'EMPIRE_API_KEY',  # Esta es obligatoria
        'OCULUS_AUTH_TOKEN',
        'OCULUS_ORDER_TOKEN'
    ]
    
    # Variables opcionales pero importantes
    optional_vars = [
        'WAXPEER_API_KEY',
        'SHADOWPAY_API_KEY',
        'RUSTSKINS_API_KEY',
        'BOT_LOG_LEVEL',
        'BOT_USE_PROXY',
        'BOT_CACHE_ENABLED'
    ]
    
    # Leer archivo .env
    try:
        with open(env_file, 'r') as f:
            env_content = f.read()
        
        # Verificar variables requeridas
        for var in required_vars:
            pattern = f'^{var}=.+$'
            if not re.search(pattern, env_content, re.MULTILINE):
                missing_vars.append(f"{var} (REQUERIDA)")
        
        # Verificar variables opcionales
        configured_optional = 0
        for var in optional_vars:
            pattern = f'^{var}=.+$'
            if re.search(pattern, env_content, re.MULTILINE):
                configured_optional += 1
        
        if missing_vars:
            return False, missing_vars
        
        return True, [f"{configured_optional}/{len(optional_vars)} variables opcionales configuradas"]
        
    except Exception as e:
        return False, [f"Error leyendo .env: {str(e)}"]

def check_api_keys_removed(root_path: Path) -> Tuple[bool, List[str]]:
    """Verifica que no exista el archivo api_keys.json con claves"""
    api_keys_file = root_path / "config" / "api_keys.json"
    issues = []
    
    if not api_keys_file.exists():
        return True, ["api_keys.json no existe (correcto)"]
    
    # Si existe, verificar que no tenga claves reales
    try:
        with open(api_keys_file, 'r') as f:
            content = f.read()
            data = json.loads(content)
        
        # Buscar claves sospechosas
        found_keys = []
        for platform, config in data.items():
            if isinstance(config, dict) and 'api_key' in config:
                key = config['api_key']
                if key and len(key) > 10:  # Clave que parece real
                    found_keys.append(platform)
        
        if found_keys:
            return False, [f"Claves API encontradas en api_keys.json: {', '.join(found_keys)}"]
        
        # Verificar si es un template
        if "_instructions" in data:
            return True, ["api_keys.json es un template (correcto)"]
        
        return False, ["api_keys.json existe pero no es un template"]
        
    except Exception as e:
        return False, [f"Error verificando api_keys.json: {str(e)}"]

def check_hardcoded_credentials(root_path: Path) -> Tuple[bool, List[str]]:
    """Busca credenciales hardcodeadas en el código"""
    issues = []
    files_to_check = []
    
    # Archivos específicos a verificar
    specific_files = [
        root_path / "core" / "proxy_manager.py",
        root_path / "core" / "oculus_proxy_manager.py",
        root_path / "core" / "config_manager.py"
    ]
    
    # Agregar todos los scrapers
    scrapers_dir = root_path / "scrapers"
    if scrapers_dir.exists():
        files_to_check.extend(scrapers_dir.glob("*.py"))
    
    files_to_check.extend(specific_files)
    
    # Patrones de credenciales hardcodeadas
    credential_patterns = [
        (r'05bd54d2-e21c-41db-bf74-d12e460210a9', 'Oculus Auth Token'),
        (r'oc_0d0a79f6', 'Oculus Order Token'),
        (r'181\.127\.133\.115', 'IP Hardcodeada'),
        (r'31fefea384d0f194de67643b9185796299d676c6e5d1f44de42e3438d7a2c944', 'Waxpeer API Key'),
        (r'5b622a85b8708c866df776626bee562c', 'Empire API Key'),
        (r'36663c5979e004871a1f7275df6ff5c4', 'ShadowPay API Key'),
        (r'b0559639-9b33-4a8e-b11a-27818a02224d', 'RustSkins API Key')
    ]
    
    for file_path in files_to_check:
        if not file_path.exists():
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for pattern, description in credential_patterns:
                if re.search(pattern, content):
                    issues.append(f"{description} en {file_path.name}")
        
        except Exception as e:
            issues.append(f"Error leyendo {file_path.name}: {str(e)}")
    
    if issues:
        return False, issues
    
    return True, ["No se encontraron credenciales hardcodeadas"]

def check_hardcoded_paths(root_path: Path) -> Tuple[bool, List[str]]:
    """Busca rutas hardcodeadas específicas del usuario"""
    issues = []
    files_to_check = []
    
    # Buscar en todos los archivos Python
    for pattern in ['**/*.py']:
        files_to_check.extend(root_path.glob(pattern))
    
    # Patrones de rutas hardcodeadas
    path_patterns = [
        (r'\/mnt\/c\/Users\/Zolu', 'Ruta WSL de Zolu'),
        (r'C:\\Users\\Zolu', 'Ruta Windows de Zolu'),
        (r'\/home\/\w+\/Documents', 'Ruta home hardcodeada'),
        (r'BOT-vCSGO-Beta(?!-V2)', 'Referencia a proyecto antiguo')
    ]
    
    for file_path in files_to_check:
        if '.git' in str(file_path) or '__pycache__' in str(file_path):
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for pattern, description in path_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    relative_path = file_path.relative_to(root_path)
                    issues.append(f"{description} en {relative_path}")
        
        except Exception:
            pass
    
    if issues:
        # Eliminar duplicados
        issues = list(set(issues))
        return False, issues[:10]  # Limitar a 10 para no saturar
    
    return True, ["No se encontraron rutas hardcodeadas"]

def check_gitignore(root_path: Path) -> Tuple[bool, List[str]]:
    """Verifica que .gitignore esté configurado correctamente"""
    gitignore = root_path / ".gitignore"
    issues = []
    
    if not gitignore.exists():
        return False, [".gitignore no existe"]
    
    required_patterns = ['.env', 'api_keys.json', '*.backup', '__pycache__']
    
    try:
        with open(gitignore, 'r') as f:
            content = f.read()
        
        missing = []
        for pattern in required_patterns:
            if pattern not in content:
                missing.append(pattern)
        
        if missing:
            return False, [f"Faltan patrones en .gitignore: {', '.join(missing)}"]
        
        return True, ["Todos los archivos sensibles están en .gitignore"]
        
    except Exception as e:
        return False, [f"Error leyendo .gitignore: {str(e)}"]

def check_imports():
    """Verifica que se puedan importar los módulos actualizados"""
    issues = []
    
    try:
        # Agregar el directorio del proyecto al path
        root_path = find_project_root()
        sys.path.insert(0, str(root_path))
        
        # Intentar importar módulos críticos
        imports_to_test = [
            ("core.config_manager", "get_config_manager"),
            ("core.path_manager", "get_path_manager"),
            ("core.oculus_proxy_manager", "create_secure_proxy_manager")
        ]
        
        for module_name, function_name in imports_to_test:
            try:
                module = __import__(module_name, fromlist=[function_name])
                if not hasattr(module, function_name):
                    issues.append(f"{module_name} no tiene {function_name}")
            except ImportError as e:
                issues.append(f"No se puede importar {module_name}: {str(e)}")
        
        if issues:
            return False, issues
        
        return True, ["Todos los módulos se importan correctamente"]
        
    except Exception as e:
        return False, [f"Error general en imports: {str(e)}"]

def generate_report(results: Dict[str, Tuple[bool, List[str]]]) -> Tuple[int, int]:
    """Genera un reporte final"""
    print_section("Resumen de Verificación")
    
    passed = sum(1 for r in results.values() if r[0])
    total = len(results)
    
    for check_name, (success, details) in results.items():
        status = "PASS" if success else "FAIL"
        color = Colors.GREEN if success else Colors.RED
        print(f"{color}[{status}] {check_name}{Colors.RESET}")
    
    percentage = (passed / total) * 100 if total > 0 else 0
    
    print(f"\n{Colors.BOLD}Resultado: {passed}/{total} verificaciones pasadas ({percentage:.0f}%){Colors.RESET}")
    
    if percentage == 100:
        print(f"{Colors.GREEN}{Colors.BOLD}¡Excelente! Tu proyecto está completamente seguro.{Colors.RESET}")
    elif percentage >= 80:
        print(f"{Colors.YELLOW}{Colors.BOLD}Bien, pero hay algunos problemas menores por resolver.{Colors.RESET}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}Atención: Hay problemas de seguridad importantes que resolver.{Colors.RESET}")
    
    return passed, total

def main():
    """Función principal de verificación"""
    print_header()
    
    root_path = find_project_root()
    print(f"📁 Verificando proyecto en: {root_path}\n")
    
    results = {}
    
    # 1. Verificar archivo .env
    print_section("Variables de Entorno")
    passed, details = check_env_file(root_path)
    print_check(passed, "Archivo .env configurado", "\n   ".join(details))
    results["Variables de Entorno"] = (passed, details)
    
    # 2. Verificar eliminación de api_keys.json
    print_section("Archivos de Claves API")
    passed, details = check_api_keys_removed(root_path)
    print_check(passed, "Claves API no expuestas", "\n   ".join(details))
    results["Claves API"] = (passed, details)
    
    # 3. Verificar credenciales hardcodeadas
    print_section("Credenciales en Código")
    passed, details = check_hardcoded_credentials(root_path)
    print_check(passed, "Sin credenciales hardcodeadas", "\n   ".join(details[:5]))  # Limitar output
    results["Credenciales"] = (passed, details)
    
    # 4. Verificar rutas hardcodeadas
    print_section("Rutas Hardcodeadas")
    passed, details = check_hardcoded_paths(root_path)
    print_check(passed, "Sin rutas hardcodeadas", "\n   ".join(details[:5]))  # Limitar output
    results["Rutas"] = (passed, details)
    
    # 5. Verificar .gitignore
    print_section("Control de Versiones")
    passed, details = check_gitignore(root_path)
    print_check(passed, "Gitignore configurado", "\n   ".join(details))
    results["Gitignore"] = (passed, details)
    
    # 6. Verificar imports
    print_section("Módulos Actualizados")
    passed, details = check_imports()
    print_check(passed, "Módulos importables", "\n   ".join(details))
    results["Imports"] = (passed, details)
    
    # Generar reporte final
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    passed_count, total_count = generate_report(results)
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    # Recomendaciones finales
    if passed_count < total_count:
        print(f"{Colors.YELLOW}{Colors.BOLD}Próximos pasos recomendados:{Colors.RESET}")
        print("1. Ejecuta el script de migración: python migrate_to_secure_config.py")
        print("2. Configura las variables de entorno en el archivo .env")
        print("3. Actualiza los imports en tu código según las instrucciones")
        print("4. Elimina o renombra archivos con información sensible")
        print("5. Vuelve a ejecutar esta verificación\n")
    
    # Guardar reporte
    report_file = root_path / f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w') as f:
        f.write(f"Reporte de Seguridad - {datetime.now()}\n")
        f.write("="*60 + "\n\n")
        for check_name, (success, details) in results.items():
            f.write(f"[{'PASS' if success else 'FAIL'}] {check_name}\n")
            for detail in details:
                f.write(f"  - {detail}\n")
            f.write("\n")
        f.write(f"\nResultado: {passed_count}/{total_count} verificaciones pasadas\n")
    
    print(f"📄 Reporte guardado en: {report_file}")
    
    return 0 if passed_count == total_count else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Verificación cancelada por el usuario{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Error inesperado: {e}{Colors.RESET}")
        sys.exit(1)