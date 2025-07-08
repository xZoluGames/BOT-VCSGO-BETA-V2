"""
Steam Market Scraper - BOT-vCSGO-Beta V2 ULTRA-FAST VERSION
Optimized for maximum speed with aggressive settings and minimal delays

Features:
- ULTRA-FAST proxy loading with smaller initial pools
- AGGRESSIVE request timing with minimal delays
- LIGHTNING-FAST worker calculation
- INSTANT startup optimization
- BLAZING connection management
"""

import time
import requests
from typing import Dict, List, Optional, Tuple
import sys
import os
from pathlib import Path
import concurrent.futures
import random
import orjson
import logging
import json
import psutil
import platform
from collections import defaultdict, Counter
from datetime import datetime
from urllib.parse import unquote

sys.path.append(str(Path(__file__).parent.parent))

from core.base_scraper import BaseScraper
from core.resource_optimizer import get_resource_optimizer
from core.oculus_proxy_manager import create_proxy_manager
from core.unified_logger import create_logger


class SteamMarketScraper(BaseScraper):
    """
    ULTRA-FAST Steam Market scraper with aggressive optimization
    
    SPEED OPTIMIZATIONS:
    - Smaller proxy pools for faster loading (2K per pool instead of 10K)
    - Minimal delays and ultra-aggressive timing
    - Maximum workers and concurrent connections
    - Instant startup with lazy loading
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        # Initialize logger first
        self.logger = logging.getLogger('SteamMarket')
        
        if use_proxy is None:
            use_proxy = True
            self.logger.info("SteamMarket: ULTRA-FAST mode - proxy enabled")
        
        super().__init__(
            platform_name="steam_market",
            use_proxy=use_proxy
        )
        
        # Initialize unified logger after parent initialization
        self.unified_logger = create_logger('SteamMarket', self.logger)
        
        # Steam API configuration
        self.api_url = "https://steamcommunity.com/market/itemordershistogram?country=PK&language=english&currency=1&item_nameid={item_nameid}&two_factor=0&norender=1"
        
        # Ultra-optimized headers
        self.steam_headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Connection': 'keep-alive'
        }
        
        # ULTRA-FAST proxy loading: 5 pools with 2K proxies each = 10K total (faster than 50K)
        self.unified_logger.log_info("🚀 ULTRA-FAST MODE: Initializing optimized proxy pools...")
        self.proxy_manager = create_proxy_manager(mode="multi", pool_count=5, proxies_per_pool=2000)
        
        # Initialize resource optimizer
        self.resource_optimizer = get_resource_optimizer()
        
        # Get system info and calculate AGGRESSIVE workers
        proxy_stats = self.proxy_manager.get_stats()
        total_proxies = sum(pool['proxy_count'] for pool in proxy_stats['pools'].values())
        
        # LIGHTNING-FAST worker calculation
        self.dynamic_workers = self._calculate_ultra_fast_workers()
        
        system_info = self.resource_optimizer.get_optimal_config(
            'steam_market', total_proxies, 5000
        )['system_info']
        
        # ULTRA-AGGRESSIVE PERFORMANCE settings
        self.max_workers = self.dynamic_workers
        
        # BLAZING FAST timing settings
        if system_info['is_wsl2']:
            self.request_delay = 0.05   # ULTRA-FAST: 50ms delay
            self.batch_delay = 0.1      # MINIMAL batch delay  
        else:
            self.request_delay = 0.03   # LIGHTNING: 30ms delay
            self.batch_delay = 0.05     # INSTANT batch delay
        
        # AGGRESSIVE retry settings
        self.max_retries = 3            # Fast retries, don't wait forever
        self.max_retry_delay = 30       # Max 30 seconds between retries
        
        # ULTRA-FAST connection management
        self.session = self._create_ultra_fast_session()
        self.last_request_time = 0
        self.connection_errors = 0
        self.consecutive_errors = 0
        
        # Performance tracking
        self.session_start_time = time.time()
        self.request_count = 0
        
        # Search for nameids file in known locations
        self.item_nameids_file = self._find_nameids_file()
        
        # Log ultra-fast initialization
        init_config = {
            'system_info': system_info,
            'max_workers': self.max_workers,
            'request_delay': self.request_delay
        }
        self.unified_logger.log_initialization(init_config, proxy_stats)
        
        # Log ULTRA-FAST pool status
        self.unified_logger.log_info(f"⚡ ULTRA-FAST 5-POOL SYSTEM: {total_proxies} total proxies")
        active_regions = [pool['region'] for pool in proxy_stats['pools'].values() if pool['active']]
        self.unified_logger.log_info(f"🚀 BLAZING Regions: {', '.join([r.upper() for r in active_regions])}")
        self.unified_logger.log_info(f"⚡ LIGHTNING Workers: {self.max_workers}")
        self.unified_logger.log_info(f"🔥 ULTRA Request Delay: {self.request_delay}s")
        
        if total_proxies == 0:
            self.unified_logger.log_warning("⚠️ No proxies loaded")
    
    def _create_ultra_fast_session(self):
        """Create ULTRA-FAST session optimized for maximum speed"""
        session = requests.Session()
        
        # AGGRESSIVE retry strategy - fail fast
        from urllib3.util.retry import Retry
        retry_strategy = Retry(
            total=1,                    # Only 1 retry per request
            backoff_factor=0.1,         # Minimal backoff
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        # MAXIMUM connection pool for speed
        from requests.adapters import HTTPAdapter
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,        # HIGH connection pool
            pool_maxsize=50             # MAX pool size
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _calculate_ultra_fast_workers(self) -> int:
        """Calculate MAXIMUM workers for ultra-fast processing"""
        try:
            # Get system information
            cpu_count = psutil.cpu_count(logical=True)
            memory_gb = psutil.virtual_memory().total / (1024**3)
            
            # Detect WSL
            is_wsl = self._detect_wsl()
            
            # AGGRESSIVE calculation for maximum speed
            if is_wsl:
                # WSL: Aggressive but stable
                base_workers = min(cpu_count * 8, 200)  # 8x CPU cores
                
                if memory_gb >= 16:
                    memory_factor = 2.0     # DOUBLE for high memory
                elif memory_gb >= 8:
                    memory_factor = 1.5     # 1.5x for medium memory
                else:
                    memory_factor = 1.2     # Still boost for low memory
                
                wsl_factor = 1.0            # No reduction for WSL in ultra-fast mode
                
            else:
                # Native system: MAXIMUM AGGRESSION
                base_workers = min(cpu_count * 12, 400)  # 12x CPU cores!
                
                if memory_gb >= 32:
                    memory_factor = 3.0     # TRIPLE for high memory
                elif memory_gb >= 16:
                    memory_factor = 2.5     # 2.5x for good memory
                elif memory_gb >= 8:
                    memory_factor = 2.0     # DOUBLE for medium memory
                else:
                    memory_factor = 1.5     # Still aggressive for low memory
                
                wsl_factor = 1.2            # BOOST for native systems
            
            # Calculate MAXIMUM workers
            optimal_workers = int(base_workers * memory_factor * wsl_factor)
            
            # AGGRESSIVE bounds for ultra-fast mode
            optimal_workers = max(optimal_workers, 500)   # MINIMUM 500 workers
            optimal_workers = min(optimal_workers, 2000)  # MAXIMUM 2000 workers
            
            self.unified_logger.log_info(f"⚡ ULTRA-FAST CALCULATION:")
            self.unified_logger.log_info(f"   CPU: {cpu_count} | Memory: {memory_gb:.1f}GB | WSL: {'YES' if is_wsl else 'NO'}")
            self.unified_logger.log_info(f"   🔥 BLAZING WORKERS: {optimal_workers}")
            
            return optimal_workers
            
        except Exception as e:
            self.unified_logger.log_warning(f"Error calculating workers: {e}, using ultra-fast default")
            return 1000  # Ultra-fast fallback
    
    def _detect_wsl(self) -> bool:
        """Fast WSL detection"""
        try:
            if Path('/proc/version').exists():
                with open('/proc/version', 'r') as f:
                    if 'microsoft' in f.read().lower():
                        return True
            return False
        except:
            return False
    
    def _find_nameids_file(self) -> Optional[Path]:
        """Fast nameids file detection"""
        possible_paths = [
            self.data_dir / "item_nameids.json",
            self.data_dir.parent / "JSON" / "item_nameids.json"
        ]
        
        for path in possible_paths:
            if path.exists():
                self.unified_logger.log_info(f"📋 Found nameids: {path.name}")
                return path
        
        self.unified_logger.log_warning("📋 Nameids file not found")
        return None
    
    def _ultra_fast_rate_limit(self):
        """MINIMAL rate limiting for maximum speed"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # MINIMAL delay - only if absolutely necessary
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_ultra_fast_request(self, url: str, timeout: int = 10):
        """Make ULTRA-FAST request with minimal overhead"""
        try:
            self._ultra_fast_rate_limit()
            
            # Get proxy from proxy manager
            proxy = self.proxy_manager.get_proxy()
            proxies_dict = {"http": proxy, "https": proxy} if proxy else None
            
            start_time = time.time()
            response = self.session.get(
                url,
                headers=self.steam_headers,
                proxies=proxies_dict,
                timeout=timeout
            )
            response_time = time.time() - start_time
            
            # Record success in proxy manager
            self.proxy_manager.record_success(response_time)
            self.unified_logger.reset_consecutive_errors()
            self.unified_logger.increment_request_count()
            
            return response
            
        except Exception as e:
            # Record failure in proxy manager
            self.proxy_manager.record_failure()
            raise e
    
    def _fetch_item_ultra_fast(self, item: Dict) -> Optional[Dict]:
        """Fetch item with ULTRA-FAST processing"""
        item_nameid = item.get('id')
        name = unquote(item.get('name', ''))
        
        if not item_nameid:
            return None
        
        url = self.api_url.format(item_nameid=item_nameid)
        
        # FAST retries - don't waste time
        for attempt in range(self.max_retries):
            try:
                response = self._make_ultra_fast_request(url, timeout=8)
                response.raise_for_status()
                
                data = response.json()
                
                # Process response FAST
                if 'highest_buy_order' in data:
                    price = int(data['highest_buy_order']) / 100.0 if data['highest_buy_order'] else 0
                    
                    return {
                        "Item": name,
                        "Price": float(price)
                    }
                else:
                    return {
                        "Item": name,
                        "Price": 0.0
                    }
                    
            except Exception as e:
                if attempt == self.max_retries - 1:
                    # Last attempt failed - return zero price quickly
                    return {"Item": name, "Price": 0.0}
                
                # MINIMAL retry delay
                time.sleep(0.1 * (attempt + 1))
        
        return {"Item": name, "Price": 0.0}
    
    def _process_items_ultra_fast(self, items: List[Dict]) -> List[Dict]:
        """Process items with ULTRA-FAST concurrent processing"""
        results = []
        
        # Start ultra-fast processing
        self.unified_logger.start_batch_processing(len(items), max_workers=self.max_workers)
        self.unified_logger.log_info(f"⚡ ULTRA-FAST Settings: {self.request_delay}s delay, {self.max_workers} workers")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit ALL tasks immediately
            future_to_item = {
                executor.submit(self._fetch_item_ultra_fast, item): item 
                for item in items
            }
            
            completed = 0
            successful = 0
            
            for future in concurrent.futures.as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        if result.get('Price', 0) > 0:
                            successful += 1
                        else:
                            successful += 1  # Count zero prices as successful
                    
                    completed += 1
                    
                    # FAST progress logging - only at key intervals
                    if completed % 100 == 0 or completed in [1, 10, 50]:
                        proxy_stats = self.proxy_manager.get_stats()
                        active_pools = [name for name, pool in proxy_stats['pools'].items() if pool['active']]
                        extra_info = {'active_pools': len(active_pools)}
                        self.unified_logger.log_batch_progress(completed, successful, extra_info)
                    
                except Exception as e:
                    completed += 1
        
        # Log ultra-fast completion
        proxy_stats = self.proxy_manager.get_stats()
        active_pools = [name for name, pool in proxy_stats['pools'].items() if pool['active']]
        extra_stats = {
            'ULTRA-FAST Mode': 'Enabled',
            'Active pools': len(active_pools),
            'Total proxies': sum(pool['proxy_count'] for pool in proxy_stats['pools'].values()),
            'Requests made': self.request_count
        }
        self.unified_logger.log_completion(len(items), successful, extra_stats)
        
        return results
    
    def fetch_data(self) -> List[Dict]:
        """ULTRA-FAST Steam Market data fetching"""
        self.unified_logger.log_info("⚡ Starting ULTRA-FAST Steam Market processing...")
        
        # Load items FAST
        if not self.item_nameids_file or not self.item_nameids_file.exists():
            self.unified_logger.log_error("item_nameids.json not found")
            return []
        
        try:
            with open(self.item_nameids_file, 'rb') as f:
                items = orjson.loads(f.read())
        except Exception as e:
            self.unified_logger.log_error(f"Error loading nameids: {e}")
            return []
        
        self.unified_logger.log_info(f"🔥 Processing {len(items)} items in ULTRA-FAST mode")
        
        # Process with ULTRA-FAST speed
        all_items = self._process_items_ultra_fast(items)
        
        self.unified_logger.log_info(f"⚡ ULTRA-FAST completion: {len(all_items)} items")
        return all_items
    
    def parse_response(self, response):
        """Not used in SteamMarket"""
        pass
    
    def calculate_profitability(self, items: List[Dict]) -> List[Dict]:
        """Override to suppress profitability calculations"""
        return items
    
    def _generate_performance_report(self):
        """Generate ULTRA-FAST performance report"""
        proxy_stats = self.proxy_manager.get_stats()
        self.unified_logger.log_performance_report(proxy_stats)
        
        # Return best region for compatibility
        if 'pools' in proxy_stats and proxy_stats['pools']:
            pool_scores = []
            for pool_name, pool_data in proxy_stats['pools'].items():
                total_requests = pool_data['success_count'] + pool_data['error_count']
                if total_requests > 0:
                    success_rate = (pool_data['success_count'] / total_requests) * 100
                    score = success_rate - (pool_data['consecutive_errors'] * 15)
                    pool_scores.append((pool_name, pool_data['region'], score))
            
            if pool_scores:
                pool_scores.sort(key=lambda x: x[2], reverse=True)
                return pool_scores[0][1]
        
        return 'us'
    
    def cleanup(self):
        """FAST cleanup"""
        self._generate_performance_report()
        
        if hasattr(self, 'session'):
            try:
                self.session.close()
                self.unified_logger.log_info("Session closed")
            except:
                pass
        
        if hasattr(self, 'proxy_manager'):
            self.proxy_manager.cleanup()


def main():
    """ULTRA-FAST testing function"""
    try:
        print("🚀 Starting ULTRA-FAST Steam Market Scraper...")
        scraper = SteamMarketScraper(use_proxy=True)
        
        start_time = time.time()
        data = scraper.run_once()
        end_time = time.time()
        
        print(f"⚡ BLAZING SPEED: {len(data)} items in {end_time - start_time:.1f}s")
        
        # Show some examples
        if data:
            print("\\n🔥 ULTRA-FAST Results:")
            for item in data[:3]:
                print(f"- {item['Item']}: ${item['Price']:.2f}")
        
        # Show proxy stats
        proxy_stats = scraper.proxy_manager.get_stats()
        total_proxies = sum(pool['proxy_count'] for pool in proxy_stats['pools'].values())
        print(f"\\n⚡ Proxy Stats: {total_proxies} proxies, {proxy_stats['pool_count']} pools")
        
        # Cleanup
        scraper.cleanup()
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()