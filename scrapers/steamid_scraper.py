"""
SteamID Scraper - BOT-vCSGO-Beta V2 with Oculus Proxy Manager
Simplified version using the new OculusProxyManager base class

Features:
- Oculus Proxy Manager integration (single mode)
- Automatic IP detection and whitelist updates
- Concurrent processing with WSL optimizations
- Incremental updates based on steam_listing_data.json
- Enhanced error handling and statistics
"""

import re
import random
from typing import List, Dict, Optional
import sys
from pathlib import Path
import concurrent.futures
import json
import time
import logging

# Add core directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.base_scraper import BaseScraper
from core.resource_optimizer import get_resource_optimizer
from core.oculus_proxy_manager import create_proxy_manager
from core.unified_logger import create_logger


class SteamIDScraper(BaseScraper):
    """
    Advanced SteamID scraper with Oculus Proxy Manager integration
    
    Features:
    - Simplified proxy management using OculusProxyManager
    - Automatic IP detection and updates
    - WSL optimizations and concurrent processing
    - Incremental updates based on Steam Listing data
    """
    
    def __init__(self, use_proxy: Optional[bool] = None):
        """
        Initialize SteamID scraper with Oculus Proxy Manager
        
        Args:
            use_proxy: Optional proxy usage (can work with or without proxy)
        """
        # Initialize logger first
        self.logger = logging.getLogger('SteamID')
        
        # SteamID can work both with and without proxy (V2 feature)
        if use_proxy is None:
            use_proxy = True  # Default to using proxy if available
            self.logger.info("SteamID: Proxy usage not specified, defaulting to proxy usage")
        
        super().__init__(
            platform_name="steamid",
            use_proxy=use_proxy
        )
        
        # Initialize unified logger after parent initialization
        self.unified_logger = create_logger('SteamID', self.logger)
        
        # Base URL for Steam Community Market
        self.base_url = "https://steamcommunity.com/market/listings/730/{}"
        
        # Headers specific for Steam
        self.steam_headers = {
             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Initialize Oculus Proxy Manager (single mode for individual requests)
        self.proxy_manager = create_proxy_manager(mode="single", proxies_per_pool=1000)
        
        # Initialize resource optimizer (WSL optimization)
        self.resource_optimizer = get_resource_optimizer()
        
        # Get optimal configuration (WSL optimization)
        proxy_stats = self.proxy_manager.get_stats()
        self.optimal_config = self.resource_optimizer.get_optimal_config(
            'steamid', 
            proxy_stats['proxy_count'], 
            10000  # Estimated items for initial config
        )
        
        self.max_workers = self.optimal_config['max_workers']
        system_info = self.optimal_config['system_info']
        
        # Log initialization with unified logger
        init_config = {
            'system_info': system_info,
            'max_workers': self.max_workers
        }
        self.unified_logger.log_initialization(init_config, proxy_stats)
        
        # Proxy initialization logging is handled by unified_logger.log_initialization above
    
    def _get_random_proxy(self) -> Optional[str]:
        """
        Get random proxy using Oculus Proxy Manager
        
        Returns:
            Random proxy or None if no proxies available
        """
        return self.proxy_manager.get_proxy()
    
    def _extract_nameid_from_html(self, html_content: str, item_name: str) -> Optional[str]:
        """
        Extract nameid from Steam HTML with enhanced patterns
        
        Args:
            html_content: HTML content from Steam page
            item_name: Item name for logging
            
        Returns:
            Extracted nameid or None if not found
        """
        try:
            # Enhanced patterns for better extraction
            patterns = [
                r'Market_LoadOrderSpread\\(\\s*(\\d+)\\s*\\)',
                r"Market_LoadOrderSpread\(\s*(\d+)\s*\)",
                r'g_rgAssets\\[730\\]\\[2\\]\\[(\\d+)\\]'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html_content)
                if match:
                    nameid = match.group(1)
                    self.logger.debug(f"Nameid found for {item_name}: {nameid}")
                    return nameid
            
            self.logger.warning(f"Could not extract nameid for {item_name}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting nameid for {item_name}: {e}")
            return None
    
    def _process_item_with_retry(self, item: Dict) -> Optional[Dict]:
        """
        Process individual item with retries and proxy rotation
        
        Args:
            item: Dictionary with item information
            
        Returns:
            Dictionary with nameid or None if failed
        """
        item_name = item['name']
        
        # Use optimal configuration from resource optimizer
        settings = self.optimal_config['recommended_settings']
        max_retries = int(settings['max_retries']) if settings['max_retries'] != float('inf') else 5
        
        for attempt in range(max_retries):
            try:
                # Get proxy from proxy manager
                proxy = self._get_random_proxy()
                
                # Format URL
                from urllib.parse import quote
                url = self.base_url.format(item_name)
                
                # Setup proxy (already formatted from Oculus API)
                proxy_dict = None
                if proxy:
                    proxy_dict = {'http': proxy, 'https': proxy}
                
                # Make request with optimal timeout
                start_time = time.time()
                if hasattr(self, 'session'):
                    response = self.session.get(
                        url,
                        headers=self.steam_headers,
                        proxies=proxy_dict,
                        timeout=settings.get('timeout', 20)
                    )
                else:
                    import requests
                    response = requests.get(
                        url,
                        headers=self.steam_headers,
                        proxies=proxy_dict,
                        timeout=settings.get('timeout', 20)
                    )
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    # Record success in proxy manager and reset consecutive errors
                    self.proxy_manager.record_success(response_time)
                    self.unified_logger.reset_consecutive_errors()
                    self.unified_logger.increment_request_count()
                    
                    nameid = self._extract_nameid_from_html(response.text, item_name)
                    if nameid:
                        return {
                            'name': item_name,
                            'id': nameid,
                            'last_updated': time.time()
                        }
                    else:
                        self.logger.warning(f"No nameid found in HTML for {item_name}")
                        continue
                else:
                    # Record failure in proxy manager
                    self.proxy_manager.record_failure()
                    self.unified_logger.log_error(f"HTTP {response.status_code}", item_name, attempt + 1)
                    
            except Exception as e:
                # Record failure in proxy manager
                self.proxy_manager.record_failure()
                self.unified_logger.log_error(str(e), item_name, attempt + 1)
                
                # Rate limiting with optimal delay
                if attempt < max_retries - 1:
                    delay = settings.get('retry_delay_base', 1) * (attempt + 1)
                    self.unified_logger.log_retry(delay, attempt + 1, max_retries, item_name)
                    time.sleep(delay)
        
        self.unified_logger.log_error(f"Failed after {max_retries} attempts", item_name)
        return None
    
    def _process_items_concurrently(self, items_to_update: List[Dict]) -> List[Dict]:
        """
        Process items concurrently with WSL optimization
        
        Args:
            items_to_update: List of items to process
            
        Returns:
            List of items with extracted nameids
        """
        new_nameids = []
        
        # Recalculate optimal configuration based on actual item count
        proxy_stats = self.proxy_manager.get_stats()
        optimal_config = self.resource_optimizer.get_optimal_config(
            'steamid', 
            proxy_stats['proxy_count'], 
            len(items_to_update)
        )
        
        max_workers = optimal_config['max_workers']
        system_info = optimal_config['system_info']
        
        # Start concurrent processing with unified logger
        self.unified_logger.start_batch_processing(len(items_to_update), max_workers=max_workers)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_item = {
                executor.submit(self._process_item_with_retry, item): item 
                for item in items_to_update
            }
            
            completed = 0
            successful = 0
            
            for future in concurrent.futures.as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    if result:  # If result is not None
                        new_nameids.append(result)
                        successful += 1
                    
                    completed += 1
                    
                    # Enhanced progress logging with unified logger
                    proxy_stats = self.proxy_manager.get_stats()
                    extra_info = {'proxy_region': proxy_stats['current_region']}
                    self.unified_logger.log_batch_progress(completed, successful, extra_info)
                        
                except Exception as e:
                    self.logger.error(f"Error in future for {item.get('name', 'unknown')}: {e}")
                    completed += 1
        
        # Log completion with unified logger
        final_stats = self.proxy_manager.get_stats()
        extra_stats = {
            'Proxy region': final_stats['current_region'].upper(),
            'Available proxies': final_stats['proxy_count'],
            'Proxy errors': final_stats['consecutive_errors']
        }
        self.unified_logger.log_completion(len(items_to_update), successful, extra_stats)
        
        return new_nameids
    
    def _compare_and_update_items(self, item_names: List, existing_nameids: List) -> List[Dict]:
        """
        Compare and update items with incremental updates
        
        Args:
            item_names: List of names from steam_listing_data.json
            existing_nameids: List of existing nameids
            
        Returns:
            Updated list of nameids
        """
        # Adapt format from SteamListing (Item/Price) to expected format (name)
        names_dict = {item['Item']: {'name': item['Item']} for item in item_names}
        nameids_dict = {item['name']: item for item in existing_nameids}
        
        # Items that need updating
        items_to_update = []
        
        for name, item in names_dict.items():
            if name not in nameids_dict:
                items_to_update.append(item)
        
        self.unified_logger.log_info(f"📊 Items in steam listing: {len(names_dict)}")
        self.unified_logger.log_info(f"💾 Existing nameids: {len(nameids_dict)}")
        self.unified_logger.log_info(f"🆕 New items to process: {len(items_to_update)}")
        
        # Keep existing items that are still in the list
        updated_nameids = [item for item in existing_nameids if item['name'] in names_dict]
        
        # Process new items concurrently
        if items_to_update:
            new_nameids = self._process_items_concurrently(items_to_update)
            updated_nameids.extend(new_nameids)
        else:
            self.unified_logger.log_info("✅ No new items to process")
        
        return updated_nameids
    
    def validate_item(self, item: Dict) -> bool:
        """Enhanced validation for SteamID format"""
        if 'name' not in item:
            self.logger.warning(f"Invalid item, missing name field: {item}")
            return False
        
        if 'id' not in item:
            self.logger.warning(f"Invalid item, missing id field: {item}")
            return False
        
        # Verify that ID is not None
        if item['id'] is None:
            self.logger.warning(f"Null ID in item: {item}")
            return False
            
        return True
    
    def parse_response(self, response):
        """Required method by BaseScraper - not used directly in SteamID"""
        return []
    
    def calculate_profitability(self, items: List[Dict]) -> List[Dict]:
        """Override to suppress profitability calculations for SteamID scraper"""
        return items
    
    def fetch_data(self) -> List[Dict]:
        """
        Get item_nameids by comparing with existing names
        
        Returns:
            Updated list of nameids
        """
        self.unified_logger.log_info("🚀 Getting item nameids from Steam with Oculus Proxy Manager...")
        
        # Data files
        listing_file = self.data_dir / 'steam_listing_data.json'
        nameids_file = self.data_dir / 'item_nameids.json'
        
        if not listing_file.exists():
            self.logger.error("steam_listing_data.json not found - run steam_listing scraper first")
            return []
        
        try:
            # Load names from SteamListing
            with open(listing_file, 'r', encoding='utf-8') as f:
                item_names = json.load(f)
            
            # Load existing nameids
            existing_nameids = []
            if nameids_file.exists():
                with open(nameids_file, 'r', encoding='utf-8') as f:
                    existing_nameids = json.load(f)
            
        except Exception as e:
            self.logger.error(f"Error loading files: {e}")
            return []
        
        # Compare and find new items with incremental updates
        updated_nameids = self._compare_and_update_items(item_names, existing_nameids)
        
        return updated_nameids
    
    def save_data(self, data):
        """Enhanced save with orjson and optional database"""
        try:
            # Use orjson for better performance
            try:
                import orjson
                use_orjson = True
            except ImportError:
                import json
                use_orjson = False
                self.logger.warning("orjson not available, using standard json")
            
            filename = "item_nameids.json"  # Specific name for SteamID
            filepath = self.data_dir / filename
            
            if use_orjson:
                # Use orjson for better performance
                json_data = orjson.dumps(data, option=orjson.OPT_INDENT_2)
                with open(filepath, 'wb') as f:
                    f.write(json_data)
            else:
                # Fallback to standard json
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Data saved to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving data: {e}")
            return False
    
    def cleanup(self):
        """Cleanup resources including proxy manager"""
        if hasattr(self, 'proxy_manager'):
            self.proxy_manager.cleanup()


def main():
    """
    Main function to run the scraper
    Enhanced with Oculus Proxy Manager and WSL optimizations
    """
    try:
        scraper = SteamIDScraper(use_proxy=True)
        
        print("=== Running SteamID Scraper V2 with Oculus Proxy Manager ===")
        print("Features: Automatic IP detection, proxy management, WSL2 optimizations")
        print("NOTE: This process may take a long time if there are many new items")
        
        data = scraper.run_once()
        
        print(f"\\n✅ Scraper completed:")
        print(f"   - Nameids obtained: {len(data)}")
        print(f"   - Statistics: {scraper.get_stats()}")
        
        # Show proxy manager stats
        proxy_stats = scraper.proxy_manager.get_stats()
        print(f"\\n📊 Proxy Manager Stats:")
        print(f"   - Current region: {proxy_stats['current_region'].upper()}")
        print(f"   - Available proxies: {proxy_stats['proxy_count']}")
        print(f"   - Error count: {proxy_stats['consecutive_errors']}")
        print(f"   - Auto-detected IP: {proxy_stats['whitelist_ip'][0] if proxy_stats['whitelist_ip'] else 'None'}")
        
        if data:
            print(f"\\n📋 First 3 nameids:")
            for item in data[:3]:
                print(f"   - {item['name']}: nameid={item.get('id', 'N/A')}")
        
        # Option to run in loop
        run_forever = input("\\n¿Run in infinite loop? (y/N): ").lower() == 'y'
        if run_forever:
            print("Starting infinite loop with Oculus Proxy Manager... (Ctrl+C to stop)")
            scraper.run_forever()
            
    except ValueError as e:
        print(f"Configuration error: {e}")
    except KeyboardInterrupt:
        print("\\n🛑 Stopped by user")
    except Exception as e:
        print(f"\\n❌ Error: {e}")
    finally:
        # Clean up resources
        if 'scraper' in locals():
            scraper.cleanup()


if __name__ == "__main__":
    main()