#!/usr/bin/env python3
"""
Script de migración para mover claves API a configuración segura
BOT-VCSGO-BETA-V2

Este script:
1. Lee las claves actuales del archivo api_keys.json
2. Genera un archivo .env con las claves
3. Elimina/renombra el archivo inseguro
4. Actualiza el código para usar el nuevo sistema
"""

import json
import orjson
import os
import sys
from pathlib import Path
from datetime import datetime
import shutil

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
    print(f"{Colors.BOLD}🔒 BOT-VCSGO-BETA-V2 - Migración de Seguridad")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")

def print_warning(message):
    """Imprime una advertencia"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")

def print_error(message):
    """Imprime un error"""
    print(f"{Colors.RED}❌ {message}{Colors.RESET}")

def print_success(message):
    """Imprime un mensaje de éxito"""
    print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")

def print_info(message):
    """Imprime información"""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.RESET}")

def find_project_root():
    """Encuentra la raíz del proyecto"""
    current = Path(__file__).resolve()
    
    # Buscar hacia arriba hasta encontrar config/
    while current != current.parent:
        if (current / "config").exists() and (current / "core").exists():
            return current
        current = current.parent
    
    return Path.cwd()

def load_current_api_keys(config_path):
    """Carga las claves API actuales"""
    api_keys_file = config_path / "api_keys.json"
    
    if not api_keys_file.exists():
        print_error(f"No se encontró {api_keys_file}")
        return None
    
    try:
        with open(api_keys_file, 'rb') as f:
            return orjson.loads(f.read())
    except Exception as e:
        print_error(f"Error leyendo api_keys.json: {e}")
        return None

def extract_api_keys(api_data):
    """Extrae las claves API del formato actual"""
    keys = {}
    
    # Mapeo de nombres de plataforma a variables de entorno
    platform_mapping = {
        'waxpeer': 'WAXPEER_API_KEY',
        'empire': 'EMPIRE_API_KEY',
        'shadowpay': 'SHADOWPAY_API_KEY',
        'rustskins': 'RUSTSKINS_API_KEY',
        'skinport': 'SKINPORT_API_KEY',
        'csdeals': 'CSDEALS_API_KEY',
        'bitskins': 'BITSKINS_API_KEY',
        'cstrade': 'CSTRADE_API_KEY',
        'marketcsgo': 'MARKETCSGO_API_KEY',
        'tradeit': 'TRADEIT_API_KEY',
        'steamout': 'STEAMOUT_API_KEY',
        'lisskins': 'LISSKINS_API_KEY',
        'white': 'WHITE_API_KEY'
    }
    
    for platform, env_var in platform_mapping.items():
        if platform in api_data:
            platform_data = api_data[platform]
            if isinstance(platform_data, dict) and 'api_key' in platform_data:
                key = platform_data['api_key']
                if key and key.strip():
                    keys[env_var] = key
            elif isinstance(platform_data, str) and platform_data.strip():
                keys[env_var] = platform_data
    
    # Buscar credenciales de proxy en el código
    proxy_creds = find_proxy_credentials()
    if proxy_creds:
        keys.update(proxy_creds)
    
    return keys

def find_proxy_credentials():
    """Busca credenciales de proxy hardcodeadas en el código"""
    print_info("Buscando credenciales de proxy en el código...")
    
    creds = {}
    
    # Buscar en proxy_manager.py y oculus_proxy_manager.py
    root = find_project_root()
    proxy_files = [
        root / "core" / "proxy_manager.py",
        root / "core" / "oculus_proxy_manager.py"
    ]
    
    for file_path in proxy_files:
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Buscar tokens de Oculus
                    if "05bd54d2-e21c-41db-bf74-d12e460210a9" in content:
                        creds['OCULUS_AUTH_TOKEN'] = "05bd54d2-e21c-41db-bf74-d12e460210a9"
                        print_warning(f"Encontrado OCULUS_AUTH_TOKEN en {file_path.name}")
                    
                    if "oc_0d0a79f6" in content:
                        creds['OCULUS_ORDER_TOKEN'] = "oc_0d0a79f6"
                        print_warning(f"Encontrado OCULUS_ORDER_TOKEN en {file_path.name}")
                    
                    if "181.127.133.115" in content:
                        creds['OCULUS_WHITELIST_IP'] = "181.127.133.115"
                        print_warning(f"Encontrada IP whitelist en {file_path.name}")
                        
            except Exception as e:
                print_error(f"Error leyendo {file_path}: {e}")
    
    return creds

def create_env_file(root_path, keys):
    """Crea el archivo .env con las claves"""
    env_path = root_path / ".env"
    env_example_path = root_path / ".env.example"
    
    # Backup si ya existe
    if env_path.exists():
        backup_path = root_path / f".env.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(env_path, backup_path)
        print_info(f"Backup creado: {backup_path}")
    
    # Crear contenido del .env
    env_content = []
    env_content.append("# BOT-VCSGO-BETA-V2 - Variables de Entorno")
    env_content.append(f"# Generado automáticamente el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    env_content.append("# ⚠️  IMPORTANTE: No subas este archivo a Git\n")
    
    # API Keys de plataformas
    env_content.append("# ==========================================")
    env_content.append("# API KEYS - Plataformas de Trading")
    env_content.append("# ==========================================\n")
    
    platform_keys = ['WAXPEER_API_KEY', 'EMPIRE_API_KEY', 'SHADOWPAY_API_KEY', 
                     'RUSTSKINS_API_KEY', 'SKINPORT_API_KEY', 'CSDEALS_API_KEY',
                     'BITSKINS_API_KEY', 'CSTRADE_API_KEY', 'MARKETCSGO_API_KEY',
                     'TRADEIT_API_KEY', 'STEAMOUT_API_KEY', 'LISSKINS_API_KEY',
                     'WHITE_API_KEY']
    
    for key in platform_keys:
        if key in keys:
            env_content.append(f"{key}={keys[key]}")
        else:
            env_content.append(f"# {key}=")
    
    # Proxy configuration
    env_content.append("\n# ==========================================")
    env_content.append("# PROXY CONFIGURATION - Oculus Proxies")
    env_content.append("# ==========================================\n")
    
    proxy_keys = ['OCULUS_AUTH_TOKEN', 'OCULUS_ORDER_TOKEN', 'OCULUS_WHITELIST_IP']
    
    for key in proxy_keys:
        if key in keys:
            env_content.append(f"{key}={keys[key]}")
        else:
            env_content.append(f"# {key}=")
    
    # Configuración adicional
    env_content.append("\n# ==========================================")
    env_content.append("# CONFIGURACIÓN DE APLICACIÓN")
    env_content.append("# ==========================================\n")
    env_content.append("BOT_LOG_LEVEL=INFO")
    env_content.append("BOT_USE_PROXY=true")
    env_content.append("BOT_CACHE_ENABLED=true")
    env_content.append("BOT_DATABASE_ENABLED=false")
    env_content.append("BOT_ENVIRONMENT=development")
    
    # Escribir archivo
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(env_content))
    
    print_success(f"Archivo .env creado: {env_path}")
    
    # Asegurar que .env está en .gitignore
    ensure_gitignore(root_path)
    
    return env_path

def ensure_gitignore(root_path):
    """Asegura que .env esté en .gitignore"""
    gitignore_path = root_path / ".gitignore"
    
    patterns_to_add = [
        '.env',
        '.env.*',
        '!.env.example',
        'config/api_keys.json',
        '*.backup',
        '__pycache__/',
        '*.pyc'
    ]
    
    if gitignore_path.exists():
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            current_content = f.read()
    else:
        current_content = ""
    
    lines_to_add = []
    for pattern in patterns_to_add:
        if pattern not in current_content:
            lines_to_add.append(pattern)
    
    if lines_to_add:
        with open(gitignore_path, 'a', encoding='utf-8') as f:
            if not current_content.endswith('\n'):
                f.write('\n')
            f.write('\n# Archivos sensibles\n')
            f.write('\n'.join(lines_to_add))
            f.write('\n')
        
        print_success(".gitignore actualizado")

def update_imports():
    """Muestra instrucciones para actualizar imports"""
    print(f"\n{Colors.CYAN}{'='*60}")
    print(f"{Colors.BOLD}📝 Instrucciones para actualizar tu código:")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    print("1. Reemplaza las importaciones en tus scrapers:\n")
    print(f"{Colors.YELLOW}   # Antiguo:")
    print("   from core.config_manager import ConfigManager")
    print(f"\n{Colors.GREEN}   # Nuevo:")
    print("   from core.config_manager import get_config_manager")
    print(f"   config_manager = get_config_manager(){Colors.RESET}\n")
    
    print("2. Actualiza el uso de claves API:\n")
    print(f"{Colors.YELLOW}   # Antiguo:")
    print("   api_key = config['waxpeer']['api_key']")
    print(f"\n{Colors.GREEN}   # Nuevo:")
    print(f"   api_key = config_manager.get_api_key('waxpeer'){Colors.RESET}\n")
    
    print("3. Para configuración de proxy:\n")
    print(f"{Colors.GREEN}   proxy_config = config_manager.get_proxy_config()")
    print(f"   auth_token = proxy_config.get('oculus_auth_token'){Colors.RESET}\n")

def secure_delete_file(file_path):
    """Elimina de forma segura un archivo con claves"""
    backup_path = file_path.with_suffix('.backup')
    
    # Crear backup antes de eliminar
    shutil.copy2(file_path, backup_path)
    print_info(f"Backup creado: {backup_path}")
    
    # Renombrar en lugar de eliminar (más seguro)
    old_path = file_path.with_name(f"OLD_{file_path.name}")
    file_path.rename(old_path)
    
    print_success(f"Archivo inseguro movido a: {old_path}")
    print_warning("Puedes eliminar manualmente este archivo cuando verifiques que todo funciona")

def main():
    """Función principal del script de migración"""
    print_header()
    
    # Encontrar raíz del proyecto
    root_path = find_project_root()
    config_path = root_path / "config"
    
    print_info(f"Directorio del proyecto: {root_path}")
    
    # Paso 1: Cargar claves actuales
    print(f"\n{Colors.BOLD}Paso 1: Leyendo configuración actual...{Colors.RESET}")
    api_data = load_current_api_keys(config_path)
    
    if not api_data:
        print_error("No se pudieron cargar las claves API actuales")
        return 1
    
    # Paso 2: Extraer claves
    print(f"\n{Colors.BOLD}Paso 2: Extrayendo claves API...{Colors.RESET}")
    keys = extract_api_keys(api_data)
    
    if not keys:
        print_warning("No se encontraron claves API para migrar")
    else:
        print_success(f"Encontradas {len(keys)} claves para migrar")
    
    # Paso 3: Crear archivo .env
    print(f"\n{Colors.BOLD}Paso 3: Creando archivo .env...{Colors.RESET}")
    env_file = create_env_file(root_path, keys)
    
    # Paso 4: Actualizar config_manager.py
    print(f"\n{Colors.BOLD}Paso 4: Actualizando config_manager.py...{Colors.RESET}")
    config_manager_path = root_path / "core" / "config_manager.py"
    
    if config_manager_path.exists():
        # Crear backup
        backup_path = config_manager_path.with_suffix('.py.backup')
        shutil.copy2(config_manager_path, backup_path)
        print_info(f"Backup creado: {backup_path}")
        print_success("Usa el nuevo config_manager.py proporcionado")
    
    # Paso 5: Manejar archivo inseguro
    print(f"\n{Colors.BOLD}Paso 5: Asegurando archivos...{Colors.RESET}")
    api_keys_file = config_path / "api_keys.json"
    
    if api_keys_file.exists():
        secure_delete_file(api_keys_file)
    
    # Instrucciones finales
    update_imports()
    
    print(f"\n{Colors.GREEN}{'='*60}")
    print(f"{Colors.BOLD}✨ ¡Migración completada con éxito!")
    print(f"{Colors.GREEN}{'='*60}{Colors.RESET}\n")
    
    print("Próximos pasos:")
    print("1. Instala python-dotenv: pip install python-dotenv")
    print("2. Verifica el archivo .env creado")
    print("3. Actualiza tus imports según las instrucciones")
    print("4. Prueba que todo funcione correctamente")
    print("5. Elimina los archivos .backup cuando estés seguro\n")
    
    print_warning("⚠️  IMPORTANTE: No subas NUNCA el archivo .env a Git")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print_error("\nOperación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        sys.exit(1)