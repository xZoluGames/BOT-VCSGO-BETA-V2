"""
Profitability Engine - BOT-vCSGO-Beta V2

Sistema de cálculo de rentabilidad y arbitraje entre plataformas CS:GO
Migrado desde OLD BASE y Beta, simplificado para uso personal

Características:
- Cálculo de fees de Steam con algoritmo exacto
- Comparación de precios entre múltiples plataformas
- Filtros por rentabilidad mínima y precio
- URLs automáticas para cada plataforma
- Modo rápido y completo de cálculo
- Notificaciones de oportunidades
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import orjson
import time

# Agregar el directorio padre al path para imports
sys.path.append(str(Path(__file__).parent.parent))

from core.config_manager import get_config_manager
from core.logger import get_scraper_logger

@dataclass
class ProfitableItem:
    """Representa un item con oportunidad de arbitraje"""
    name: str
    buy_price: float
    buy_platform: str
    buy_url: str
    steam_price: float
    net_steam_price: float
    profit_percentage: float
    profit_absolute: float
    steam_url: str
    timestamp: str
    
    @property
    def profit_percentage_display(self) -> float:
        """Retorna la rentabilidad como porcentaje para mostrar"""
        return self.profit_percentage * 100
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario para JSON/serialización"""
        return {
            'name': self.name,
            'buy_price': self.buy_price,
            'buy_platform': self.buy_platform,
            'buy_url': self.buy_url,
            'steam_price': self.steam_price,
            'net_steam_price': self.net_steam_price,
            'profit_percentage': self.profit_percentage,
            'profit_absolute': self.profit_absolute,
            'profit_percentage_display': self.profit_percentage_display,
            'steam_url': self.steam_url,
            'timestamp': self.timestamp
        }

class SteamFeeCalculator:
    """
    Calculadora de fees de Steam usando el algoritmo exacto del proyecto original
    
    Steam cobra comisiones variables según el precio:
    - Fee base + fee de desarrollador
    - Estructura de intervalos dinámicos
    """
    
    @staticmethod
    def calculate_net_price(gross_price: float) -> float:
        """
        Calcula el precio neto después de las comisiones de Steam
        
        Args:
            gross_price: Precio bruto de venta en Steam
            
        Returns:
            Precio neto que recibirá el vendedor
        """
        # Intervalos y fees del algoritmo original
        intervals = [0.02, 0.21, 0.32, 0.43]
        fees = [0.02, 0.03, 0.04, 0.05, 0.07, 0.09]
        
        # Extender intervalos dinámicamente según el precio
        while gross_price > intervals[-1]:
            last_interval = intervals[-1]
            if len(intervals) % 2 == 0:
                intervals.append(round(last_interval + 0.12, 2))
            else:
                intervals.append(round(last_interval + 0.11, 2))
        
        # Extender fees dinámicamente
        while len(intervals) > len(fees):
            last_fee = fees[-1]
            if len(fees) % 2 == 0:
                fees.append(round(last_fee + 0.01, 2))
            else:
                fees.append(round(last_fee + 0.02, 2))
        
        # Encontrar el intervalo correspondiente
        applicable_interval_index = None
        for i, interval_value in enumerate(intervals):
            if gross_price <= interval_value:
                applicable_interval_index = i
                break
        
        # Si no encontramos intervalo, usar el último
        if applicable_interval_index is None:
            applicable_interval_index = len(intervals) - 1
        
        # Calcular precio neto
        fee_to_subtract = fees[applicable_interval_index]
        net_price = round(gross_price - fee_to_subtract, 2)
        
        return max(0.0, net_price)  # No puede ser negativo
    
    @staticmethod
    def calculate_profit_margin(gross_price: float, buy_price: float) -> Tuple[float, float]:
        """
        Calcula margen de ganancia y rentabilidad
        
        Args:
            gross_price: Precio de venta en Steam
            buy_price: Precio de compra en otra plataforma
            
        Returns:
            Tuple con (ganancia_absoluta, rentabilidad_porcentual)
        """
        net_price = SteamFeeCalculator.calculate_net_price(gross_price)
        profit_absolute = net_price - buy_price
        
        if buy_price > 0:
            profit_percentage = profit_absolute / buy_price
        else:
            profit_percentage = 0.0
        
        return profit_absolute, profit_percentage

class ProfitabilityEngine:
    """
    Motor principal de cálculo de rentabilidad
    
    Analiza datos de múltiples plataformas y encuentra oportunidades de arbitraje
    considerando las comisiones de Steam y filtros de usuario.
    """
    
    # URLs base de las plataformas soportadas
    PLATFORM_URLS = {
        'waxpeer': 'https://waxpeer.com/item/cs-go/',
        'csdeals': 'https://cs.deals/market/',
        'empire': 'https://csgoempire.com/shop/',
        'skinport': 'https://skinport.com/market/730?search=',
        'bitskins': 'https://bitskins.com/market/730/search?market_hash_name=',
        'cstrade': 'https://cs.trade/csgo-skins?search=',
        'marketcsgo': 'https://market.csgo.com/?search=',
        'tradeit': 'https://tradeit.gg/csgo/trade?search=',
        'skindeck': 'https://skindeck.com/listings?query=',
        'rapidskins': 'https://rapidskins.com/item/',
        'manncostore': 'https://mannco.store/item/730/',
        'shadowpay': 'https://shadowpay.com/csgo?search=',
        'skinout': 'https://skinout.gg/market/cs2?item=',
        'lisskins': 'https://lis-skins.com/market_730.html?search_item=',
        'white': 'https://white.market/search?game[]=CS2&query='
    }
    
    STEAM_URL_BASE = 'https://steamcommunity.com/market/listings/730/'
    
    def __init__(self):
        """Inicializa el motor de profitabilidad"""
        self.config_manager = get_config_manager()
        self.fee_calculator = SteamFeeCalculator()
        self.logger = get_scraper_logger('profitability')
        
        # Rutas de datos
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # Cache para optimizar rendimiento
        self._steam_cache = {}
        self._platform_cache = {}
        self._cache_timestamp = {}
        
        # Configuración
        self.config = {
            'cache_ttl': 300,  # 5 minutos
            'min_profit_percentage': 0.01,  # 1% mínimo
            'min_price': 1.0,  # $1 mínimo
            'max_results': 100,
            'steam_fee_mode': True  # True = incluir fees, False = precio bruto
        }
        
        self.logger.info("Motor de profitabilidad inicializado")
    
    def calculate_opportunities(self, 
                              mode: str = "complete",
                              min_profit_percentage: float = 0.05,
                              min_price: float = 1.0,
                              max_results: int = 100) -> List[ProfitableItem]:
        """
        Calcula oportunidades de arbitraje entre plataformas
        
        Args:
            mode: "fast" (sin fees) o "complete" (con fees Steam)
            min_profit_percentage: Rentabilidad mínima (0.05 = 5%)
            min_price: Precio mínimo del item
            max_results: Máximo número de resultados
            
        Returns:
            Lista de items rentables ordenada por rentabilidad
        """
        self.logger.info(
            f"Calculando oportunidades - "
            f"Modo: {mode}, "
            f"Rentabilidad min: {min_profit_percentage*100}%, "
            f"Precio min: ${min_price}"
        )
        
        start_time = time.time()
        
        # Cargar datos de Steam
        steam_data = self._load_steam_data()
        if not steam_data:
            self.logger.error("No hay datos de Steam disponibles")
            return []
        
        opportunities = []
        platforms_processed = 0
        items_analyzed = 0
        
        # Procesar cada plataforma
        for platform in self.PLATFORM_URLS.keys():
            platform_data = self._load_platform_data(platform)
            
            if not platform_data:
                self.logger.debug(f"No hay datos para {platform}")
                continue
            
            platforms_processed += 1
            platform_opportunities = 0
            
            for item in platform_data:
                items_analyzed += 1
                
                # Extraer datos del item
                item_name = item.get('Item', '').strip()
                try:
                    buy_price = float(item.get('Price', 0))
                except (ValueError, TypeError):
                    continue
                
                # Filtros básicos
                if not item_name or buy_price < min_price:
                    continue
                
                # Buscar precio en Steam
                steam_price = steam_data.get(item_name)
                if not steam_price:
                    continue
                
                if steam_price <= buy_price:
                    continue
                
                # Calcular rentabilidad
                if mode == "complete":
                    # Modo completo: incluir fees de Steam
                    profit_abs, profit_pct = self.fee_calculator.calculate_profit_margin(
                        steam_price, buy_price
                    )
                    net_steam_price = self.fee_calculator.calculate_net_price(steam_price)
                else:
                    # Modo rápido: precio bruto
                    profit_abs = steam_price - buy_price
                    profit_pct = profit_abs / buy_price if buy_price > 0 else 0
                    net_steam_price = steam_price
                
                # Filtro de rentabilidad
                if profit_pct < min_profit_percentage:
                    continue
                
                # Crear oportunidad
                opportunity = ProfitableItem(
                    name=item_name,
                    buy_price=buy_price,
                    buy_platform=platform,
                    buy_url=item.get('URL', self._generate_platform_url(platform, item_name)),
                    steam_price=steam_price,
                    net_steam_price=net_steam_price,
                    profit_percentage=profit_pct,
                    profit_absolute=profit_abs,
                    steam_url=self._generate_steam_url(item_name),
                    timestamp=datetime.now().isoformat()
                )
                
                opportunities.append(opportunity)
                platform_opportunities += 1
            
            self.logger.debug(
                f"{platform}: {platform_opportunities} oportunidades "
                f"de {len(platform_data)} items"
            )
        
        # Ordenar por rentabilidad descendente
        opportunities.sort(key=lambda x: x.profit_percentage, reverse=True)
        
        # Limitar resultados
        opportunities = opportunities[:max_results]
        
        # Estadísticas
        runtime = time.time() - start_time
        self.logger.info(
            f"Análisis completado en {runtime:.2f}s - "
            f"Plataformas: {platforms_processed}, "
            f"Items analizados: {items_analyzed}, "
            f"Oportunidades: {len(opportunities)}"
        )
        
        return opportunities
    
    def _load_steam_data(self) -> Dict[str, float]:
        """
        Carga datos de precios de Steam desde archivos disponibles
        
        Returns:
            Diccionario {nombre_item: precio}
        """
        steam_data = {}
        
        # Archivos de Steam a buscar
        steam_files = [
            'steammarket_data.json',
            'steamlisting_data.json', 
            'steamprice_data.json'
        ]
        
        for filename in steam_files:
            filepath = self.data_dir / filename
            
            if not filepath.exists():
                continue
            
            try:
                with open(filepath, 'rb') as f:
                    data = orjson.loads(f.read())
                
                items_loaded = 0
                for item in data:
                    if isinstance(item, dict):
                        name = item.get('Item', '').strip()
                        try:
                            price = float(item.get('Price', 0))
                            if name and price > 0:
                                # Usar el precio más alto encontrado
                                if name not in steam_data or price > steam_data[name]:
                                    steam_data[name] = price
                                    items_loaded += 1
                        except (ValueError, TypeError):
                            continue
                
                self.logger.debug(f"Cargados {items_loaded} precios desde {filename}")
                
            except Exception as e:
                self.logger.error(f"Error cargando {filename}: {e}")
        
        self.logger.info(f"Datos de Steam cargados: {len(steam_data)} items únicos")
        return steam_data
    
    def _load_platform_data(self, platform: str) -> List[Dict]:
        """
        Carga datos de una plataforma específica
        
        Args:
            platform: Nombre de la plataforma
            
        Returns:
            Lista de items de la plataforma
        """
        # Verificar cache
        cache_key = platform
        if cache_key in self._platform_cache:
            if time.time() - self._cache_timestamp.get(cache_key, 0) < self.config['cache_ttl']:
                return self._platform_cache[cache_key]
        
        # Cargar desde archivo
        filename = f"{platform}_data.json"
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            return []
        
        try:
            with open(filepath, 'rb') as f:
                data = orjson.loads(f.read())
            
            # Validar formato
            if not isinstance(data, list):
                self.logger.warning(f"Formato inválido en {filename}")
                return []
            
            # Actualizar cache
            self._platform_cache[cache_key] = data
            self._cache_timestamp[cache_key] = time.time()
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error cargando datos de {platform}: {e}")
            return []
    
    def _generate_platform_url(self, platform: str, item_name: str) -> str:
        """
        Genera URL específica de la plataforma para un item
        
        Args:
            platform: Nombre de la plataforma
            item_name: Nombre del item
            
        Returns:
            URL completa del item en la plataforma
        """
        base_url = self.PLATFORM_URLS.get(platform, '')
        
        if not base_url:
            return ''
        
        # Codificar nombre para URL
        encoded_name = item_name.replace(' ', '%20').replace('|', '%7C')
        
        return f"{base_url}{encoded_name}"
    
    def _generate_steam_url(self, item_name: str) -> str:
        """
        Genera URL de Steam Market para un item
        
        Args:
            item_name: Nombre del item
            
        Returns:
            URL completa de Steam Market
        """
        encoded_name = item_name.replace(' ', '%20').replace('|', '%7C')
        return f"{self.STEAM_URL_BASE}{encoded_name}"
    
    def save_opportunities(self, opportunities: List[ProfitableItem], 
                         filename: Optional[str] = None) -> bool:
        """
        Guarda oportunidades en archivo JSON único con historial de timestamps
        
        Args:
            opportunities: Lista de oportunidades
            filename: Nombre del archivo (por defecto: profitability_data.json)
            
        Returns:
            True si se guardó correctamente
        """
        if not opportunities:
            self.logger.warning("No hay oportunidades para guardar")
            return False
        
        try:
            if filename is None:
                filename = "profitability_data.json"
            
            filepath = self.data_dir / filename
            
            # Cargar datos existentes si el archivo existe
            existing_data = {}
            if filepath.exists():
                try:
                    with open(filepath, 'rb') as f:
                        existing_data = orjson.loads(f.read())
                except Exception as e:
                    self.logger.warning(f"No se pudo cargar archivo existente: {e}, creando uno nuevo")
                    existing_data = {}
            
            # Preparar nueva entrada con timestamp
            current_timestamp = datetime.now().isoformat()
            new_entry = {
                'timestamp': current_timestamp,
                'total_opportunities': len(opportunities),
                'mode': 'complete',
                'opportunities': [item.to_dict() for item in opportunities]
            }
            
            # Estructura del archivo: mantener últimas entradas + histórico
            if 'current' not in existing_data:
                existing_data = {
                    'current': new_entry,
                    'last_updated': current_timestamp,
                    'history': []
                }
            else:
                # Mover entrada actual al histórico
                if existing_data.get('current'):
                    existing_data.setdefault('history', []).append(existing_data['current'])
                
                # Mantener solo últimas 10 entradas en historial
                existing_data['history'] = existing_data['history'][-10:]
                
                # Actualizar entrada actual
                existing_data['current'] = new_entry
                existing_data['last_updated'] = current_timestamp
            
            # Guardar archivo actualizado
            with open(filepath, 'wb') as f:
                f.write(orjson.dumps(existing_data, option=orjson.OPT_INDENT_2))
            
            self.logger.info(f"Oportunidades guardadas en {filepath} (entrada actual + historial)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error guardando oportunidades: {e}")
            return False
    
    def load_current_opportunities(self, filename: str = "profitability_data.json") -> List[ProfitableItem]:
        """
        Carga las oportunidades actuales desde el archivo de datos
        
        Args:
            filename: Nombre del archivo de datos
            
        Returns:
            Lista de oportunidades actuales
        """
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            self.logger.info("No hay archivo de profitabilidad actual")
            return []
        
        try:
            with open(filepath, 'rb') as f:
                data = orjson.loads(f.read())
            
            current_data = data.get('current', {})
            opportunities_data = current_data.get('opportunities', [])
            
            opportunities = []
            for opp_data in opportunities_data:
                opportunity = ProfitableItem(
                    name=opp_data['name'],
                    buy_price=opp_data['buy_price'],
                    buy_platform=opp_data['buy_platform'],
                    buy_url=opp_data['buy_url'],
                    steam_price=opp_data['steam_price'],
                    net_steam_price=opp_data['net_steam_price'],
                    profit_percentage=opp_data['profit_percentage'],
                    profit_absolute=opp_data['profit_absolute'],
                    steam_url=opp_data['steam_url'],
                    timestamp=opp_data['timestamp']
                )
                opportunities.append(opportunity)
            
            self.logger.info(f"Cargadas {len(opportunities)} oportunidades actuales")
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error cargando oportunidades actuales: {e}")
            return []
    
    def get_profitability_summary(self, filename: str = "profitability_data.json") -> Dict:
        """
        Obtiene resumen de datos de profitabilidad
        
        Args:
            filename: Nombre del archivo de datos
            
        Returns:
            Diccionario con resumen de profitabilidad
        """
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            return {
                'has_data': False,
                'last_updated': None,
                'total_opportunities': 0,
                'history_entries': 0
            }
        
        try:
            with open(filepath, 'rb') as f:
                data = orjson.loads(f.read())
            
            current_data = data.get('current', {})
            return {
                'has_data': True,
                'last_updated': data.get('last_updated'),
                'total_opportunities': current_data.get('total_opportunities', 0),
                'history_entries': len(data.get('history', [])),
                'mode': current_data.get('mode', 'unknown')
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo resumen de profitabilidad: {e}")
            return {
                'has_data': False,
                'last_updated': None,
                'total_opportunities': 0,
                'history_entries': 0,
                'error': str(e)
            }

    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas del motor de profitabilidad
        
        Returns:
            Diccionario con estadísticas
        """
        return {
            'platforms_supported': len(self.PLATFORM_URLS),
            'cache_entries': len(self._platform_cache),
            'config': self.config.copy(),
            'data_directory': str(self.data_dir)
        }

def main():
    """Función principal para testing del motor de profitabilidad"""
    engine = ProfitabilityEngine()
    
    try:
        print("💰 Iniciando análisis de profitabilidad...")
        print(f"📊 Estadísticas: {engine.get_stats()}")
        print("-" * 50)
        
        # Calcular oportunidades
        opportunities = engine.calculate_opportunities(
            mode="complete",
            min_profit_percentage=0.01,  # 1% mínimo for debugging
            min_price=1.0,  # $1 mínimo
            max_results=10
        )
        
        if opportunities:
            print(f"✅ {len(opportunities)} oportunidades encontradas:")
            print()
            
            for i, opp in enumerate(opportunities[:5], 1):
                print(f"{i}. {opp.name}")
                print(f"   💸 Comprar: ${opp.buy_price:.2f} en {opp.buy_platform}")
                print(f"   💰 Vender: ${opp.steam_price:.2f} en Steam (neto: ${opp.net_steam_price:.2f})")
                print(f"   📈 Ganancia: ${opp.profit_absolute:.2f} ({opp.profit_percentage_display:.1f}%)")
                print(f"   🔗 {opp.buy_url}")
                print()
            
            # Guardar resultados
            if engine.save_opportunities(opportunities):
                print("💾 Resultados guardados")
        else:
            print("❌ No se encontraron oportunidades rentables")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()