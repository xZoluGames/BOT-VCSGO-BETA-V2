"""
Steam Listing Scraper - BOT-vCSGO-Beta V2 with Oculus Proxy Manager
Simplified version using the new OculusProxyManager base class (multi mode)

Features:
- Oculus Proxy Manager integration (multi mode for batch operations)
- Automatic IP detection and whitelist updates
- Multiple proxy pools with intelligent rotation
- WSL optimizations and robust connection management
- Performance tracking and error recovery
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
import socket
import json
import psutil
import platform
from collections import defaultdict, Counter
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from core.base_scraper import BaseScraper
from core.resource_optimizer import get_resource_optimizer
from core.oculus_proxy_manager import create_proxy_manager
from core.unified_logger import create_logger


class SteamListingScraper(BaseScraper):
    """
    Steam Listing scraper with Oculus Proxy Manager integration (multi-pool mode)
    
    Features:
    - Multi-pool proxy management for batch operations
    - Automatic IP detection and updates
    - WSL optimizations and robust connection management
    - Performance tracking and intelligent pool rotation
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        # Initialize logger first
        self.logger = logging.getLogger('SteamListing')
        
        if use_proxy is None:
            use_proxy = True
            self.logger.info("SteamListing: Proxy usage not specified, defaulting to proxy usage")
        
        super().__init__(
            platform_name="steam_listing",
            use_proxy=use_proxy
        )
        
        # Initialize unified logger after parent initialization
        self.unified_logger = create_logger('SteamListing', self.logger)
        
        # Steam API configuration
        self.base_url = "https://steamcommunity.com/market/search/render/?query=&start={}&count={}&search_descriptions=0&sort_column=name&sort_dir=asc&appid=730&norender=1"
        
        # Headers specific for Steam
        self.steam_headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://steamcommunity.com/market/search?appid=730'
        }
        
        # Initialize Oculus Proxy Manager (multi mode for batch operations)
        self.proxy_manager = create_proxy_manager(mode="multi", pool_count=5, proxies_per_pool=10000)
        
        # Initialize resource optimizer
        self.resource_optimizer = get_resource_optimizer()
        
        # Get system info and calculate dynamic workers
        proxy_stats = self.proxy_manager.get_stats()
        total_proxies = sum(pool['proxy_count'] for pool in proxy_stats['pools'].values())
        self.optimal_config = self.resource_optimizer.get_optimal_config(
            'steam_listing', 
            total_proxies, 
            50000  # Updated for 50,000 total proxies (5 pools x 10,000)
        )
        
        # WSL Performance Detection and Dynamic Worker Calculation
        self.dynamic_workers = self._calculate_optimal_workers()
        
        system_info = self.optimal_config['system_info']
        
        # ENHANCED PERFORMANCE settings for 5-pool system with dynamic workers
        self.max_workers = self.dynamic_workers  # Use calculated optimal workers
        
        if system_info['is_wsl2']:
            self.request_delay = 0.2  # Ultra-fast requests with 5 pools and 50k proxies
            self.batch_delay = 1     # Minimal batch delay
        else:
            self.request_delay = 0.3  # Lightning-fast requests for native systems
            self.batch_delay = 1     # Minimal delay
        
        # UNLIMITED RETRIES - Never give up!
        self.max_retries = float('inf')  # Infinite retries
        self.max_retry_delay = 600  # Max 10 minutes between retries
        
        # Connection management
        self.session = self._create_session()
        self.last_request_time = 0
        self.connection_errors = 0
        self.consecutive_errors = 0
        
        # Performance tracking
        self.session_start_time = time.time()
        self.current_batch = 0
        self.total_batches = 0
        self.request_count = 0
        
        self.logger.info("Steam Listing scraper with Oculus Proxy Manager initialized")
        self.logger.info(f"System detected: {system_info['system_type']}")
        self.logger.info(f"WSL2 optimized: {'[YES]' if system_info['is_wsl2'] else '[NO]'}")
        self.logger.info(f"Max workers: {self.max_workers}")
        self.logger.info(f"Request delay: {self.request_delay}s")
        
        # Log pool initialization status
        self.logger.info(f"🌍 ENHANCED 5-POOL SYSTEM INITIALIZED: {total_proxies} total proxies")
        active_regions = [pool['region'] for pool in proxy_stats['pools'].values() if pool['active']]
        self.logger.info(f"🚀 Active Regions: {', '.join([r.upper() for r in active_regions])}")
        self.logger.info(f"🎯 Auto-detected IP: {proxy_stats['whitelist_ip'][0] if proxy_stats['whitelist_ip'] else 'None'}")
        
        if total_proxies == 0:
            self.logger.warning("⚠️ No proxies loaded in any pool")
    
    def _create_session(self):
        """Create ultra-conservative session for WSL"""
        session = requests.Session()
        
        # Estrategia de reintentos muy conservadora
        from urllib3.util.retry import Retry
        retry_strategy = Retry(
            total=2,
            backoff_factor=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        # Pool de conexiones mínimo
        from requests.adapters import HTTPAdapter
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=3,   # Mínimo para WSL
            pool_maxsize=5        # Mínimo para WSL
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _calculate_optimal_workers(self) -> int:
        """Calculate optimal number of workers based on system performance and WSL detection"""
        try:
            # Get system information
            cpu_count = psutil.cpu_count(logical=True)
            memory_gb = psutil.virtual_memory().total / (1024**3)
            
            # Detect WSL
            is_wsl = self._detect_wsl()
            
            # Base calculation
            if is_wsl:
                # WSL optimization: more conservative approach
                base_workers = min(cpu_count * 2, 40)  # WSL handles threading differently
                
                # Adjust based on memory (need more memory for 50k proxies)
                if memory_gb >= 16:
                    memory_factor = 1.2
                elif memory_gb >= 8:
                    memory_factor = 1.0
                else:
                    memory_factor = 0.8
                
                # WSL-specific adjustments
                wsl_factor = 0.9  # Slightly reduce for WSL overhead
                
            else:
                # Native system: more aggressive
                base_workers = min(cpu_count * 3, 80)
                
                # Memory factor for native systems
                if memory_gb >= 32:
                    memory_factor = 1.5
                elif memory_gb >= 16:
                    memory_factor = 1.2
                elif memory_gb >= 8:
                    memory_factor = 1.0
                else:
                    memory_factor = 0.8
                
                wsl_factor = 1.0  # No reduction for native
            
            # Calculate final workers
            optimal_workers = int(base_workers * memory_factor * wsl_factor)
            
            # Ensure minimum and maximum bounds
            optimal_workers = max(optimal_workers, 200)  # Minimum 200 workers
            optimal_workers = min(optimal_workers, 1000)  # Maximum 1000 workers
            
            self.logger.info(f"🧮 PERFORMANCE CALCULATION:")
            self.logger.info(f"   CPU Cores: {cpu_count} | Memory: {memory_gb:.1f}GB")
            self.logger.info(f"   WSL Detected: {'YES' if is_wsl else 'NO'}")
            self.logger.info(f"   Base Workers: {base_workers}")
            self.logger.info(f"   Memory Factor: {memory_factor:.1f}x")
            self.logger.info(f"   WSL Factor: {wsl_factor:.1f}x")
            self.logger.info(f"   ⚡ OPTIMAL WORKERS: {optimal_workers}")
            
            return optimal_workers
            
        except Exception as e:
            self.logger.warning(f"Error calculating optimal workers: {e}, using default")
            return 350  # Fallback value
    
    def _detect_wsl(self) -> bool:
        """Detect if running in WSL environment"""
        try:
            # Method 1: Check /proc/version for Microsoft/WSL
            if Path('/proc/version').exists():
                with open('/proc/version', 'r') as f:
                    version_info = f.read().lower()
                    if 'microsoft' in version_info or 'wsl' in version_info:
                        return True
            
            # Method 2: Check platform information
            platform_info = platform.platform().lower()
            if 'microsoft' in platform_info or 'wsl' in platform_info:
                return True
            
            # Method 3: Check environment variables
            wsl_vars = ['WSL_DISTRO_NAME', 'WSL_INTEROP', 'WSLENV']
            for var in wsl_vars:
                if var in os.environ:
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _aggressive_rate_limit(self):
        """Ultra-aggressive rate limiting for WSL"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Base delay
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            time.sleep(sleep_time)
        
        # Additional delay based on connection errors
        if self.connection_errors > 0:
            error_delay = min(self.connection_errors * 1.0, 10.0)  # Max 10 seconds
            time.sleep(error_delay)
        
        # Extra delay for consecutive errors
        if self.consecutive_errors > 3:
            consecutive_delay = min(self.consecutive_errors * 2.0, 20.0)  # Max 20 seconds
            self.logger.warning(f"Consecutive errors detected, extra delay: {consecutive_delay}s")
            time.sleep(consecutive_delay)
        
        self.last_request_time = time.time()
    
    def _handle_connection_error(self, error_msg: str):
        """Handle connection errors with progressive recovery"""
        self.connection_errors += 1
        self.consecutive_errors += 1
        
        # Progressive backoff
        backoff_time = min(self.consecutive_errors * 5, 60)  # Max 1 minute
        
        self.logger.error(f"Connection error #{self.connection_errors}: {error_msg}")
        self.logger.warning(f"Backing off for {backoff_time} seconds...")
        
        time.sleep(backoff_time)
        
        # Reset session on too many errors
        if self.consecutive_errors > 5:
            self.logger.warning("Too many consecutive errors, recreating session...")
            try:
                self.session.close()
            except:
                pass
            self.session = self._create_session()
            self.consecutive_errors = 0
    
    def _make_safe_request(self, url: str, pool_name: str = None, timeout: int = 30):
        """Make a request with comprehensive error handling using proxy manager"""
        try:
            self._aggressive_rate_limit()
            
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
            self.proxy_manager.record_success(response_time, pool_name)
            
            # Reset consecutive errors on success
            if self.consecutive_errors > 0:
                self.consecutive_errors = max(0, self.consecutive_errors - 1)
                
            return response
            
        except (requests.exceptions.ConnectionError, OSError) as e:
            # Record failure in proxy manager
            self.proxy_manager.record_failure(pool_name)
            
            error_msg = str(e)
            if "[Errno 22]" in error_msg or "Invalid argument" in error_msg:
                self._handle_connection_error(error_msg)
            raise
        except requests.exceptions.Timeout as e:
            # Record failure in proxy manager
            self.proxy_manager.record_failure(pool_name)
            self.logger.warning(f"Request timeout: {e}")
            raise
        except Exception as e:
            # Record failure in proxy manager
            self.proxy_manager.record_failure(pool_name)
            self.logger.error(f"Unexpected request error: {e}")
            raise
    
    def fetch_data(self) -> List[Dict]:
        """Get Steam Listing prices with multi-pool proxy management"""
        self.logger.info("Starting Steam Listing processing with Oculus Proxy Manager...")
        
        # Step 1: Get total count
        total_count = self._get_total_count()
        if not total_count:
            self.logger.error("Could not get total_count from Steam")
            return []
        
        self.logger.info(f"Total items available: {total_count}")
        
        # Step 2: Calculate batches
        batch_size = 10
        self.total_batches = (total_count + batch_size - 1) // batch_size
        self.logger.info(f"📊 PROCESSING PLAN: {self.total_batches} batches with {self.max_workers} workers")
        self.logger.info(f"⚙️ Settings: {self.request_delay}s request delay, {self.batch_delay}s batch delay")
        
        # Step 3: Create batch tasks
        batch_tasks = [i * batch_size for i in range(self.total_batches)]
        
        # Step 4: Process with optimized settings
        all_items = self._process_batches_safely(batch_tasks, batch_size)
        
        self.logger.info(f"Processing completed: {len(all_items)} items obtained")
        return all_items
    
    def _get_total_count(self) -> Optional[int]:
        """Get total count with unlimited retries using proxy manager"""
        url = self.base_url.format(0, 1)
        attempt = 0
        
        while True:  # UNLIMITED RETRIES!
            attempt += 1
            
            try:
                # Make safe request using proxy manager
                response = self._make_safe_request(url, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                total_count = data.get('total_count')
                if total_count:
                    return int(total_count)
                    
            except Exception as e:
                self.logger.warning(f"Attempt {attempt} failed: {e}")
                
                # Progressive delay with max cap
                delay = min(self.batch_delay * min(attempt, 10), self.max_retry_delay)
                self.logger.info(f"⏳ Waiting {delay:.1f}s before retry {attempt + 1}... (Total Count)")
                time.sleep(delay)
    
    def _process_batches_safely(self, batch_tasks: List[int], batch_size: int) -> List[Dict]:
        """Process batches with multi-pool proxy management"""
        all_items = []
        
        self.logger.info(f"Using {self.max_workers} workers for {len(batch_tasks)} batches")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_start = {
                executor.submit(self._fetch_batch_safely, start, batch_size): start 
                for start in batch_tasks
            }
            
            completed = 0
            successful = 0
            start_time = time.time()
            
            for future in concurrent.futures.as_completed(future_to_start):
                start_index = future_to_start[future]
                try:
                    batch_items = future.result()
                    if batch_items:
                        all_items.extend(batch_items)
                        successful += 1
                    
                    completed += 1
                    self.current_batch = completed
                    
                    # Enhanced progress logging with timing
                    if completed % 50 == 0 or completed in [1, 10, 25]:
                        progress = (completed / len(batch_tasks)) * 100
                        success_rate = (successful / completed) * 100
                        elapsed = time.time() - start_time
                        rate = completed / elapsed if elapsed > 0 else 0
                        eta = (len(batch_tasks) - completed) / rate if rate > 0 else 0
                        
                        # Get current proxy stats
                        proxy_stats = self.proxy_manager.get_stats()
                        active_pools = [name for name, pool in proxy_stats['pools'].items() if pool['active']]
                        
                        self.logger.info(
                            f"📈 BATCH {completed}/{len(batch_tasks)} ({progress:.1f}%) | "
                            f"✅ Success: {success_rate:.1f}% | "
                            f"⚡ Rate: {rate:.1f}/min | "
                            f"⏱️ ETA: {eta/60:.1f}min | "
                            f"🌍 Active Pools: {len(active_pools)}"
                        )
                        
                except Exception as e:
                    self.logger.error(f"❌ Error in batch {start_index}: {e}")
                    completed += 1
                    self.current_batch = completed
        
        final_success_rate = (successful / len(batch_tasks)) * 100 if batch_tasks else 0
        self.logger.info(f"Processing completed: {successful}/{len(batch_tasks)} batches successful ({final_success_rate:.1f}%)")
        
        return all_items
    
    def _fetch_batch_safely(self, start: int, count: int) -> List[Dict]:
        """Fetch batch with unlimited retries using proxy manager"""
        url = self.base_url.format(start, count)
        attempt = 0
        
        while True:  # UNLIMITED RETRIES!
            attempt += 1
            self.request_count += 1
            
            try:
                # Make safe request using proxy manager
                response = self._make_safe_request(url, timeout=35)
                response.raise_for_status()
                
                data = response.json()
                if "results" in data and data["results"]:
                    return self._extract_items(data["results"])
                else:
                    # Empty results but successful request
                    return []
                    
            except Exception as e:
                self.logger.debug(f"Batch {start} attempt {attempt} failed: {e}")
                
                # Progressive delay with max cap
                delay = min(self.batch_delay * min(attempt, 10), self.max_retry_delay)
                time.sleep(delay)
    
    def _extract_items(self, json_data: List) -> List[Dict]:
        """Extract items with sell prices and icons"""
        from core.cache_service import get_cache_service
        
        image_cache = get_cache_service()
        items = []
        
        for item in json_data:
            try:
                name = item.get('name', 'Unknown')
                name = name.replace("/", "-")
                
                sell_price_cents = item.get('sell_price', 0)
                sell_price_dollars = sell_price_cents / 100.0
                
                # Extract icon_url
                icon_url = item.get('asset_description', {}).get('icon_url', '')
                full_icon_url = f"https://community.fastly.steamstatic.com/economy/image/{icon_url}" if icon_url else ""
                
                # Use cache service
                cached_icon_url = self._get_optimized_image_url(image_cache, full_icon_url)
                
                items.append({
                    "Item": name,
                    "Price": float(sell_price_dollars),
                    "IconUrl": cached_icon_url
                })
            except Exception as e:
                self.unified_logger.log_error(f"Error extracting item: {e}")
        
        return items
    
    def _get_optimized_image_url(self, image_cache, steam_icon_url: str) -> str:
        """Get optimized URL - automatically download if not cached"""
        if not steam_icon_url:
            return ""
        
        # Check if already cached
        cache_path = image_cache.get_image_path(steam_icon_url)
        if cache_path and cache_path.exists():
            try:
                relative_path = cache_path.relative_to(Path("static"))
                return f"/static/{relative_path.as_posix()}"
            except ValueError:
                return f"/cache/images/{cache_path.name}"
        else:
            # Return original URL for now (avoid additional connections)
            return steam_icon_url
    
    def save_data(self, data):
        """Override to save as steam_listing_data.json with incremental update"""
        try:
            filename = "steam_listing_data.json"
            filepath = self.data_dir / filename
            
            # Load existing data if exists
            existing_data = {}
            existing_count = 0
            if filepath.exists():
                try:
                    with open(filepath, 'rb') as f:
                        existing_items = orjson.loads(f.read())
                    existing_count = len(existing_items)
                    
                    # Create dictionary for fast search by name
                    for item in existing_items:
                        item_name = item.get('Item', '')
                        if item_name:
                            existing_data[item_name] = item
                    
                    self.unified_logger.log_info(f"📚 Loaded {existing_count} existing items")
                except Exception as e:
                    self.unified_logger.log_warning(f"Error loading existing data: {e}")
            
            # Process new data
            new_items_added = 0
            updated_items = 0
            duplicates_skipped = 0
            
            for new_item in data:
                item_name = new_item.get('Item', '')
                if not item_name:
                    continue
                
                if item_name in existing_data:
                    # Item exists - update price if different
                    existing_item = existing_data[item_name]
                    new_price = new_item.get('Price', 0)
                    existing_price = existing_item.get('Price', 0)
                    
                    if abs(new_price - existing_price) > 0.01:
                        existing_item['Price'] = new_price
                        new_icon = new_item.get('IconUrl', '')
                        if new_icon.startswith('/static/') or new_icon.startswith('/cache/'):
                            existing_item['IconUrl'] = new_icon
                        updated_items += 1
                    else:
                        duplicates_skipped += 1
                else:
                    # New item
                    existing_data[item_name] = new_item
                    new_items_added += 1
            
            # Convert dictionary back to list
            final_data = list(existing_data.values())
            
            # Operation statistics
            self.unified_logger.log_info(f"📈 Incremental update completed:")
            self.unified_logger.log_info(f"  - Existing items: {existing_count}")
            self.unified_logger.log_info(f"  - New items added: {new_items_added}")
            self.unified_logger.log_info(f"  - Items updated: {updated_items}")
            self.unified_logger.log_info(f"  - Duplicates skipped: {duplicates_skipped}")
            self.unified_logger.log_info(f"  - Final total: {len(final_data)}")
            
            # Save updated data
            json_data = orjson.dumps(final_data, option=orjson.OPT_INDENT_2)
            with open(filepath, 'wb') as f:
                f.write(json_data)
            
            self.unified_logger.log_info(f"💾 Data saved to {filepath}")
            return True
            
        except Exception as e:
            self.unified_logger.log_error(f"Error saving data: {e}")
            return False
    
    def parse_response(self, response):
        """Not used in SteamListing"""
        pass
    
    def calculate_profitability(self, items: List[Dict]) -> List[Dict]:
        """Override to suppress profitability calculations"""
        return items
    
    def _generate_performance_report(self):
        """Generate final performance report for 5-pool system"""
        session_duration = time.time() - self.session_start_time
        proxy_stats = self.proxy_manager.get_stats()
        
        self.logger.info("\\n" + "="*60)
        self.logger.info("🌍 ENHANCED 5-POOL PERFORMANCE REPORT")
        self.logger.info("="*60)
        self.logger.info(f"⏱️ Session duration: {session_duration:.1f} seconds ({session_duration/60:.1f} minutes)")
        self.logger.info(f"📊 Total requests made: {self.request_count}")
        self.logger.info(f"📈 Batches processed: {self.current_batch}/{self.total_batches}")
        self.logger.info(f"🎯 Auto-detected IP: {proxy_stats['whitelist_ip'][0] if proxy_stats['whitelist_ip'] else 'None'}")
        
        # Enhanced pool performance analysis
        self.logger.info("\\n🏊 5-POOL PERFORMANCE ANALYSIS:")
        self.logger.info("-" * 60)
        
        pool_scores = []
        for pool_name, pool_data in proxy_stats['pools'].items():
            total_requests = pool_data['success_count'] + pool_data['error_count']
            
            if total_requests > 0:
                success_rate = (pool_data['success_count'] / total_requests) * 100
                score = success_rate - (pool_data['consecutive_errors'] * 15)
                pool_scores.append((pool_name, pool_data['region'], score, success_rate, pool_data))
            else:
                pool_scores.append((pool_name, pool_data['region'], 0, 0, pool_data))
        
        # Sort pools by score (highest first)
        pool_scores.sort(key=lambda x: x[2], reverse=True)
        
        for i, (pool_name, region, score, success_rate, pool_data) in enumerate(pool_scores, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            total_requests = pool_data['success_count'] + pool_data['error_count']
            
            self.logger.info(
                f"{medal} {pool_name.upper()} ({region.upper()}): Score={score:.1f} | "
                f"Success={success_rate:.1f}% | "
                f"Requests={total_requests} | Errors={pool_data['error_count']} | "
                f"Proxies={pool_data['proxy_count']} | ConsecErrors={pool_data['consecutive_errors']}"
            )
        
        if pool_scores:
            best_pool, best_region, best_score = pool_scores[0][0], pool_scores[0][1], pool_scores[0][2]
            self.logger.info(f"\\n🏆 CHAMPION POOL: {best_pool.upper()} ({best_region.upper()}) - Score: {best_score:.1f}")
            self.logger.info("="*60)
            return best_region
        
        return 'us'  # Fallback
    
    def cleanup(self):
        """Cleanup resources including proxy manager"""
        # Generate performance report
        self._generate_performance_report()
        
        if hasattr(self, 'session'):
            try:
                self.session.close()
                self.unified_logger.log_info("Session closed successfully")
            except Exception as e:
                self.unified_logger.log_warning(f"Error closing session: {e}")
        
        if hasattr(self, 'proxy_manager'):
            self.proxy_manager.cleanup()


def main():
    """Main function for testing"""
    try:
        scraper = SteamListingScraper(use_proxy=True)
        data = scraper.run_once()
        print(f"Obtained {len(data)} items from Steam Listing")
        
        # Show some examples
        if data:
            print("\\nExample listings obtained:")
            for item in data[:5]:
                print(f"- {item['Item']}: ${item['Price']:.2f}")
        
        # Show proxy manager stats
        proxy_stats = scraper.proxy_manager.get_stats()
        print(f"\\n📊 Proxy Manager Stats:")
        print(f"   - Total pools: {proxy_stats['pool_count']}")
        total_proxies = sum(pool['proxy_count'] for pool in proxy_stats['pools'].values())
        print(f"   - Total proxies: {total_proxies}")
        print(f"   - Auto-detected IP: {proxy_stats['whitelist_ip'][0] if proxy_stats['whitelist_ip'] else 'None'}")
        
        # Cleanup and show performance report
        best_region = scraper.cleanup()
        if best_region:
            print(f"\\n🏆 Best performing region: {best_region.upper()}")
        
    except ValueError as e:
        print(f"Configuration error: {e}")
    except KeyboardInterrupt:
        print("\\nScraping interrupted by user")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()