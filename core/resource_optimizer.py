# backend/core/resource_optimizer.py

import os
import platform
import psutil
from typing import Dict, Tuple
import subprocess
import logging

class ResourceOptimizer:
    """
    Optimizador de recursos para scrapers con detección automática de WSL2
    Calcula la configuración óptima basada en recursos disponibles
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._system_info = self._detect_system()
        
    def _detect_system(self) -> Dict:
        """Detecta el sistema y recursos disponibles"""
        info = {
            'is_wsl2': False,
            'is_docker': False,
            'cpu_cores': os.cpu_count() or 4,
            'memory_gb': 0,
            'available_memory_gb': 0,
            'system_type': 'unknown'
        }
        
        try:
            # Detectar WSL2
            uname = platform.uname()
            if 'microsoft' in uname.release.lower():
                info['is_wsl2'] = True
                info['system_type'] = 'wsl2'
                
                # En WSL2, verificar si tenemos acceso a más información
                try:
                    # Intentar obtener información específica de WSL2
                    result = subprocess.run(['wsl.exe', '--status'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        self.logger.info("WSL2 detectado con acceso completo al sistema")
                except:
                    pass
                    
            # Detectar Docker
            elif os.path.exists('/.dockerenv'):
                info['is_docker'] = True
                info['system_type'] = 'docker'
            else:
                info['system_type'] = 'native'
            
            # Información de memoria
            memory = psutil.virtual_memory()
            info['memory_gb'] = round(memory.total / (1024**3), 2)
            info['available_memory_gb'] = round(memory.available / (1024**3), 2)
            
            self.logger.info(f"Sistema detectado: {info['system_type']} | "
                           f"CPU cores: {info['cpu_cores']} | "
                           f"Memoria: {info['memory_gb']}GB total, "
                           f"{info['available_memory_gb']}GB disponible")
            
        except Exception as e:
            self.logger.warning(f"Error detectando sistema: {e}")
            
        return info
    
    def get_optimal_workers(self, scraper_type: str, proxy_count: int, item_count: int) -> int:
        """Calcula el número óptimo de workers basado en el sistema y tipo de scraper"""
        
        base_multiplier = self._get_base_multiplier(scraper_type)
        cpu_cores = self._system_info['cpu_cores']
        available_memory = self._system_info['available_memory_gb']
        
        # Cálculo base
        if self._system_info['is_wsl2']:
            # WSL2 puede manejar más concurrencia eficientemente
            base_workers = cpu_cores * base_multiplier * 2
            memory_factor = min(available_memory / 2, 4)  # Máximo 4x por memoria
            
        elif self._system_info['is_docker']:
            # Docker tiene overhead, ser más conservador
            base_workers = cpu_cores * base_multiplier * 0.75
            memory_factor = min(available_memory / 3, 2)  # Máximo 2x por memoria
            
        else:
            # Sistema nativo
            base_workers = cpu_cores * base_multiplier
            memory_factor = min(available_memory / 2, 3)  # Máximo 3x por memoria
        
        # Aplicar factor de memoria
        calculated_workers = int(base_workers * memory_factor)
        
        # Límites específicos por tipo de scraper
        limits = self._get_scraper_limits(scraper_type)
        
        # Aplicar límites
        optimal_workers = min(
            calculated_workers,
            limits['max_workers'],
            proxy_count,  # No más workers que proxies
            item_count    # No más workers que items
        )
        
        optimal_workers = max(optimal_workers, limits['min_workers'])
        
        self.logger.info(f"Workers óptimos para {scraper_type}: {optimal_workers} "
                        f"(base: {calculated_workers}, límites: {limits})")
        
        return optimal_workers
    
    def _get_base_multiplier(self, scraper_type: str) -> int:
        """Obtiene el multiplicador base según el tipo de scraper"""
        multipliers = {
            'steammarket': 8,     # Asíncrono, puede manejar más concurrencia
            'steamlisting': 6,    # Procesamiento por lotes
            'steamid': 4,         # Más intensivo en CPU por el regex
            'default': 4
        }
        return multipliers.get(scraper_type.lower(), multipliers['default'])
    
    def _get_scraper_limits(self, scraper_type: str) -> Dict[str, int]:
        """Obtiene los límites específicos por tipo de scraper"""
        if self._system_info['is_wsl2']:
            limits = {
                'steammarket': {'min_workers': 200, 'max_workers': 2000},
                'steamlisting': {'min_workers': 20, 'max_workers': 500},
                'steamid': {'min_workers': 200, 'max_workers': 300},
                'default': {'min_workers': 200, 'max_workers': 2000}
            }
        else:
            limits = {
                'steammarket': {'min_workers': 200, 'max_workers': 2000},
                'steamlisting': {'min_workers': 200, 'max_workers': 2000},
                'steamid': {'min_workers': 5, 'max_workers': 50},
                'default': {'min_workers': 5, 'max_workers': 50}
            }
        
        return limits.get(scraper_type.lower(), limits['default'])
    
    def get_optimal_config(self, scraper_type: str, proxy_count: int, item_count: int) -> Dict:
        """Obtiene configuración completa optimizada"""
        
        optimal_workers = self.get_optimal_workers(scraper_type, proxy_count, item_count)
        
        config = {
            'max_workers': optimal_workers,
            'system_info': self._system_info.copy(),
            'recommended_settings': self._get_recommended_settings(scraper_type)
        }
        
        return config
    
    def _get_recommended_settings(self, scraper_type: str) -> Dict:
        """Obtiene configuraciones recomendadas según el sistema"""
        
        if self._system_info['is_wsl2']:
            settings = {
                'timeout': 30,
                'retry_delay_base': 0.05,
                'max_retries': 20 if scraper_type == 'steamid' else float('inf'),
                'batch_size': 1000,
                'connection_pool_size': 100
            }
        else:
            settings = {
                'timeout': 20,
                'retry_delay_base': 0.1,
                'max_retries': 15 if scraper_type == 'steamid' else 100,
                'batch_size': 500,
                'connection_pool_size': 50
            }
            
        return settings

# Instancia global para reutilización
_resource_optimizer = None

def get_resource_optimizer() -> ResourceOptimizer:
    """Obtiene instancia singleton del optimizador de recursos"""
    global _resource_optimizer
    if _resource_optimizer is None:
        _resource_optimizer = ResourceOptimizer()
    return _resource_optimizer