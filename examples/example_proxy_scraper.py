#!/usr/bin/env python3
"""
Ejemplo de Scraper usando ProxyManager Avanzado
Demuestra cómo integrar el sistema de proxy rotation en un scraper personalizado
"""

import sys
from pathlib import Path
import time
import json

# Agregar core al path
sys.path.append(str(Path(__file__).parent.parent))

from core.base_scraper import BaseScraper
from core.proxy_manager import ProxyManager, ProxyManagerContext


class ExampleProxyScraper(BaseScraper):
    """
    Ejemplo de scraper que demuestra el uso del ProxyManager avanzado
    """
    
    def __init__(self, use_advanced_proxy=True):
        super().__init__(
            platform_name='example_proxy',
            use_proxy=True,
            use_advanced_proxy_manager=use_advanced_proxy  # ← Activar ProxyManager
        )
        self.request_count = 0
    
    def fetch_data(self):
        """Obtiene datos de ejemplo usando el sistema de proxy rotation"""
        items = []
        
        # URLs de ejemplo para testing
        test_urls = [
            'https://httpbin.org/ip',          # Muestra la IP usada
            'https://httpbin.org/user-agent',  # Muestra el user agent
            'https://httpbin.org/headers',     # Muestra todos los headers
            'https://httpbin.org/delay/1',     # Simula delay
            'https://httpbin.org/status/200',  # Status code 200
        ]
        
        self.logger.info(f"🚀 Iniciando scraping con {'ProxyManager' if self.proxy_manager else 'proxy tradicional'}")
        
        # Hacer múltiples solicitudes para demostrar la rotación
        for i in range(10):
            url = test_urls[i % len(test_urls)]
            self.logger.info(f"📡 Solicitud {i+1}/10: {url}")
            
            try:
                response = self.make_request(url)
                if response:
                    data = response.json()
                    items.append({
                        'request_id': i + 1,
                        'url': url,
                        'data': data,
                        'status_code': response.status_code
                    })
                    self.logger.info(f"✅ Respuesta exitosa: {response.status_code}")
                    
                    # Si es la URL de IP, mostrar la IP usada
                    if 'ip' in url:
                        ip_used = data.get('origin', 'unknown')
                        self.logger.info(f"🌐 IP utilizada: {ip_used}")
                else:
                    self.logger.warning(f"❌ Fallo en solicitud {i+1}")
                
                self.request_count += 1
                
                # Mostrar estadísticas cada 3 solicitudes
                if self.request_count % 3 == 0 and self.proxy_manager:
                    self._show_proxy_stats()
                
                # Pequeña pausa entre solicitudes
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"💥 Error en solicitud {i+1}: {e}")
        
        return items
    
    def _show_proxy_stats(self):
        """Muestra estadísticas del ProxyManager"""
        if not self.proxy_manager:
            return
        
        stats = self.proxy_manager.get_stats()
        self.logger.info("📊 ESTADÍSTICAS PROXY MANAGER:")
        self.logger.info(f"   Total proxies: {stats['total_proxies']}")
        self.logger.info(f"   Pools activos: {stats['active_pools']}")
        self.logger.info(f"   Rotación habilitada: {stats['rotation_enabled']}")
        self.logger.info(f"   Pool de rotación: {stats['rotation_pool_size']} proxies")
        
        # Mostrar estadísticas por pool
        for pool_name, pool_stats in stats['pools'].items():
            self.logger.info(f"   {pool_name}: {pool_stats['region']} - "
                           f"Success: {pool_stats['success_rate']}% - "
                           f"Proxies: {pool_stats['proxies_count']} - "
                           f"Score: {pool_stats['performance_score']}")


def demo_basic_usage():
    """Demostración de uso básico con BaseScraper"""
    print("\n🔥 DEMO 1: Uso Básico con BaseScraper")
    print("=" * 50)
    
    try:
        with ExampleProxyScraper(use_advanced_proxy=True) as scraper:
            items = scraper.fetch_data()
            
            print(f"\n✅ Scraping completado!")
            print(f"📊 Items obtenidos: {len(items)}")
            
            # Mostrar algunas IPs usadas
            ip_responses = [item for item in items if 'ip' in item['url']]
            if ip_responses:
                print(f"🌐 IPs utilizadas:")
                for item in ip_responses:
                    ip = item['data'].get('origin', 'unknown')
                    print(f"   Solicitud {item['request_id']}: {ip}")
                    
    except Exception as e:
        print(f"❌ Error en demo básico: {e}")


def demo_direct_proxy_manager():
    """Demostración de uso directo del ProxyManager"""
    print("\n🔧 DEMO 2: Uso Directo del ProxyManager")
    print("=" * 50)
    
    try:
        # Usar context manager para limpieza automática
        with ProxyManagerContext(
            num_pools=2,
            proxies_per_pool=500,
            rotation_pool_size=25
        ) as proxy_manager:
            
            import requests
            
            for i in range(5):
                print(f"\n🔄 Solicitud {i+1}/5:")
                
                # Obtener proxy para la solicitud
                proxy_dict = proxy_manager.get_proxy_for_request()
                
                try:
                    # Hacer solicitud con el proxy
                    start_time = time.time()
                    response = requests.get(
                        'https://httpbin.org/ip',
                        proxies=proxy_dict,
                        timeout=10
                    )
                    response_time = time.time() - start_time
                    
                    if response.status_code == 200:
                        ip_data = response.json()
                        ip_used = ip_data.get('origin', 'unknown')
                        print(f"✅ IP utilizada: {ip_used}")
                        print(f"⏱️ Tiempo de respuesta: {response_time:.2f}s")
                        
                        # Registrar éxito
                        proxy_manager.record_request_result(True, response_time)
                    else:
                        print(f"❌ Error HTTP: {response.status_code}")
                        proxy_manager.record_request_result(False)
                        
                except Exception as e:
                    print(f"💥 Error en solicitud: {e}")
                    proxy_manager.record_request_result(False)
                
                time.sleep(2)
            
            # Mostrar estadísticas finales
            stats = proxy_manager.get_stats()
            print(f"\n📊 ESTADÍSTICAS FINALES:")
            print(f"   Total solicitudes: {stats['total_requests']}")
            print(f"   Proxies disponibles: {stats['total_proxies']}")
            print(f"   Pools activos: {stats['active_pools']}")
            
    except Exception as e:
        print(f"❌ Error en demo directo: {e}")


def demo_comparison():
    """Comparación entre proxy tradicional vs ProxyManager"""
    print("\n⚖️ DEMO 3: Comparación Tradicional vs ProxyManager")
    print("=" * 50)
    
    # Test con proxy tradicional
    print("\n📋 Probando con proxy tradicional...")
    try:
        with ExampleProxyScraper(use_advanced_proxy=False) as scraper:
            start_time = time.time()
            items_traditional = scraper.fetch_data()
            traditional_time = time.time() - start_time
            traditional_count = len(items_traditional)
    except Exception as e:
        print(f"❌ Error con proxy tradicional: {e}")
        traditional_count = 0
        traditional_time = 0
    
    print(f"\n🚀 Probando con ProxyManager avanzado...")
    try:
        with ExampleProxyScraper(use_advanced_proxy=True) as scraper:
            start_time = time.time()
            items_advanced = scraper.fetch_data()
            advanced_time = time.time() - start_time
            advanced_count = len(items_advanced)
    except Exception as e:
        print(f"❌ Error con ProxyManager: {e}")
        advanced_count = 0
        advanced_time = 0
    
    # Comparar resultados
    print(f"\n📊 RESULTADOS COMPARACIÓN:")
    print(f"{'Método':<20} {'Items':<10} {'Tiempo':<10} {'Items/min':<12}")
    print("-" * 52)
    
    traditional_rate = (traditional_count / (traditional_time/60)) if traditional_time > 0 else 0
    advanced_rate = (advanced_count / (advanced_time/60)) if advanced_time > 0 else 0
    
    print(f"{'Tradicional':<20} {traditional_count:<10} {traditional_time:<10.1f} {traditional_rate:<12.1f}")
    print(f"{'ProxyManager':<20} {advanced_count:<10} {advanced_time:<10.1f} {advanced_rate:<12.1f}")
    
    if advanced_rate > traditional_rate:
        improvement = ((advanced_rate - traditional_rate) / traditional_rate) * 100 if traditional_rate > 0 else 0
        print(f"\n🚀 ProxyManager es {improvement:.1f}% más eficiente!")
    elif traditional_rate > advanced_rate:
        decline = ((traditional_rate - advanced_rate) / traditional_rate) * 100 if traditional_rate > 0 else 0
        print(f"\n⚠️ Proxy tradicional es {decline:.1f}% más rápido (pero menos robusto)")
    else:
        print(f"\n🤝 Rendimiento similar, pero ProxyManager ofrece mejor robustez")


if __name__ == "__main__":
    print("🔄 SISTEMA PROXY MANAGER - EJEMPLOS DE USO")
    print("=" * 60)
    print("Este script demuestra las capacidades del ProxyManager avanzado")
    print("desarrollado para BOT-VCSGO-BETA-V2")
    
    try:
        # Ejecutar todas las demos
        demo_basic_usage()
        time.sleep(3)
        
        demo_direct_proxy_manager()
        time.sleep(3)
        
        demo_comparison()
        
        print(f"\n🎉 TODAS LAS DEMOS COMPLETADAS!")
        print(f"📚 Ver PROXY_MANAGER_GUIDE.md para más información")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Demos interrumpidas por el usuario")
    except Exception as e:
        print(f"\n💥 Error general en demos: {e}")