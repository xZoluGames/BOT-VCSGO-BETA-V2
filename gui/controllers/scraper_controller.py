# Scraper Controller - Connects GUI to Backend Scrapers

import threading
import queue
import time
import os
import sys
from datetime import datetime
import importlib.util
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class ScraperController:
    def __init__(self):
        self.scrapers = {}
        self.scraper_threads = {}
        self.scraper_status = {}
        self.results_queue = queue.Queue()
        self.callbacks = {}
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "scrapers.json")
        
        self.load_scrapers()
        self.load_config()
        
    def load_scrapers(self):
        """Load all available scrapers dynamically"""
        scrapers_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scrapers")
        
        if not os.path.exists(scrapers_dir):
            print(f"Scrapers directory not found: {scrapers_dir}")
            return
        
        # List of expected scrapers
        scraper_files = [
            "bitskins_scraper.py",
            "waxpeer_scraper.py", 
            "skinport_scraper.py",
            "steam_market_scraper.py",
            "csdeals_scraper.py",
            "empire_scraper.py",
            "shadowpay_scraper.py",
            "lisskins_scraper.py",
            "tradeit_scraper.py",
            "rapidskins_scraper.py",
            "manncostore_scraper.py",
            "marketcsgo_scraper.py",
            "skindeck_scraper.py",
            "skinout_scraper.py",
            "white_scraper.py",
            "cstrade_scraper.py",
            "steam_listing_scraper.py",
            "steamid_scraper.py"
        ]
        
        for scraper_file in scraper_files:
            scraper_path = os.path.join(scrapers_dir, scraper_file)
            if os.path.exists(scraper_path):
                scraper_name = scraper_file.replace(".py", "")
                try:
                    # Load module
                    spec = importlib.util.spec_from_file_location(scraper_name, scraper_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    self.scrapers[scraper_name] = module
                    
                    # Initialize status
                    self.scraper_status[scraper_name] = {
                        "status": "idle",
                        "last_run": None,
                        "items_fetched": 0,
                        "success_rate": 95,  # Default
                        "error": None,
                        "config": {
                            "enabled": True,
                            "use_proxy": False,
                            "run_in_loop": False,
                            "timeout": 30,
                            "delay": 2.0,
                            "max_retries": 3
                        }
                    }
                    
                    print(f"Loaded scraper: {scraper_name}")
                except Exception as e:
                    print(f"Error loading {scraper_name}: {e}")
            else:
                print(f"Scraper file not found: {scraper_path}")
    
    def load_config(self):
        """Load scraper configuration from JSON"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    
                # Update scraper configs
                for scraper_name, scraper_config in config.items():
                    if scraper_name in self.scraper_status:
                        self.scraper_status[scraper_name]["config"].update(scraper_config)
        except Exception as e:
            print(f"Error loading scraper config: {e}")
    
    def save_config(self):
        """Save scraper configuration to JSON"""
        try:
            config = {}
            for scraper_name, status in self.scraper_status.items():
                config[scraper_name] = status["config"]
            
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving scraper config: {e}")
    
    def run_scraper(self, scraper_name, callback=None):
        """Execute a scraper in a separate thread"""
        if scraper_name not in self.scrapers:
            print(f"Scraper not found: {scraper_name}")
            return False
        
        # Check if scraper is enabled
        if not self.scraper_status[scraper_name]["config"]["enabled"]:
            print(f"Scraper {scraper_name} is disabled")
            return False
        
        # Store callback
        if callback:
            self.callbacks[scraper_name] = callback
        
        # Check if already running
        if self.scraper_status[scraper_name]["status"] == "running":
            print(f"Scraper {scraper_name} is already running")
            return False
        
        # Start thread
        thread = threading.Thread(
            target=self._run_scraper_thread,
            args=(scraper_name,),
            daemon=True
        )
        self.scraper_threads[scraper_name] = thread
        thread.start()
        
        return True
    
    def _run_scraper_thread(self, scraper_name):
        """Thread worker for running scraper"""
        try:
            print(f"Starting scraper: {scraper_name}")
            
            # Update status
            self.scraper_status[scraper_name]["status"] = "running"
            self.scraper_status[scraper_name]["error"] = None
            
            # Notify callback
            if scraper_name in self.callbacks:
                self.callbacks[scraper_name]("started", scraper_name)
            
            # Get scraper module
            module = self.scrapers[scraper_name]
            
            items_count = 0
            
            # Try to find and execute main function
            if hasattr(module, 'main'):
                # Execute main function
                result = module.main()
                # The scrapers are writing to files, so read the file to get count
                items_count = self.get_items_count_from_file(scraper_name)
            elif hasattr(module, 'scrape'):
                # Execute scrape function
                result = module.scrape()
                items_count = self.get_items_count_from_file(scraper_name)
            else:
                # Try to find a class and instantiate it
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and 'scraper' in attr_name.lower():
                        scraper_instance = attr()
                        if hasattr(scraper_instance, 'scrape'):
                            result = scraper_instance.scrape()
                            items_count = self.get_items_count_from_file(scraper_name)
                            break
                else:
                    # Fallback: get from file
                    items_count = self.get_items_count_from_file(scraper_name)
            
            # Update status with real items count
            self.scraper_status[scraper_name].update({
                "status": "idle",
                "last_run": datetime.now(),
                "items_fetched": items_count,
                "success_rate": 100 if items_count > 0 else 0
            })
            
            # Notify callback with real items count
            if scraper_name in self.callbacks:
                self.callbacks[scraper_name]("completed", scraper_name, items_count)
            
            print(f"Scraper {scraper_name} completed with {items_count} items")
            
        except Exception as e:
            print(f"Error in scraper {scraper_name}: {e}")
            
            # Update status
            self.scraper_status[scraper_name]["status"] = "error"
            self.scraper_status[scraper_name]["error"] = str(e)
            
            # Notify callback
            if scraper_name in self.callbacks:
                self.callbacks[scraper_name]("error", scraper_name, str(e))

    def get_items_count_from_file(self, scraper_name):
        """Get items count from the scraper's data file"""
        try:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
            filename = f"{scraper_name.replace('_scraper', '')}_data.json"
            filepath = os.path.join(data_dir, filename)
            
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return len(data)
            return 0
        except Exception as e:
            print(f"Error reading items count for {scraper_name}: {e}")
            return 0
    
    def stop_scraper(self, scraper_name):
        """Stop a running scraper"""
        if scraper_name in self.scraper_threads:
            # Note: In a real implementation, you'd need a proper way to stop threads
            # For now, just mark as stopped
            self.scraper_status[scraper_name]["status"] = "stopped"
            print(f"Scraper {scraper_name} stopped")
    
    def update_scraper_config(self, scraper_name, key, value):
        """Update scraper configuration"""
        if scraper_name in self.scraper_status:
            self.scraper_status[scraper_name]["config"][key] = value
            self.save_config()
            print(f"Updated {scraper_name} config: {key} = {value}")
    
    def get_scraper_status(self, scraper_name):
        """Get status of a specific scraper"""
        return self.scraper_status.get(scraper_name, {})
    
    def get_all_status(self):
        """Get status of all scrapers"""
        return self.scraper_status.copy()
    
    def get_active_scrapers(self):
        """Get count of active scrapers"""
        return sum(1 for status in self.scraper_status.values() if status["status"] == "running")
    
    def get_total_items(self):
        """Get total items fetched by all scrapers"""
        return sum(status.get("items_fetched", 0) for status in self.scraper_status.values())
    
    def run_all_scrapers(self, callback=None):
        """Run all enabled scrapers"""
        enabled_scrapers = [
            name for name, status in self.scraper_status.items() 
            if status["config"]["enabled"]
        ]
        
        for scraper_name in enabled_scrapers:
            self.run_scraper(scraper_name, callback)
        
        return len(enabled_scrapers)
    
    def run_group(self, group_name, callback=None):
        """Run a group of scrapers"""
        groups = {
            "fast": ["waxpeer_scraper", "skinport_scraper", "csdeals_scraper", "lisskins_scraper", "white_scraper"],
            "api": ["waxpeer_scraper", "skinport_scraper", "empire_scraper"],
            "essential": ["waxpeer_scraper", "skinport_scraper"]
        }
        
        if group_name not in groups:
            print(f"Unknown group: {group_name}")
            return 0
        
        scrapers_to_run = groups[group_name]
        count = 0
        
        for scraper_name in scrapers_to_run:
            if scraper_name in self.scraper_status:
                if self.run_scraper(scraper_name, callback):
                    count += 1
        
        return count
# Agregar estos métodos al ScraperController existente

    def get_scraper_data(self, scraper_name):
        """Get the latest data from a scraper's JSON file"""
        try:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
            data_file = os.path.join(data_dir, f"{scraper_name.replace('_scraper', '')}_data.json")
            
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    data = json.load(f)
                    return data
            return None
        except Exception as e:
            print(f"Error reading data for {scraper_name}: {e}")
            return None

    def get_last_scrape_time(self, scraper_name):
        """Get the last time this scraper ran successfully"""
        data = self.get_scraper_data(scraper_name)
        if data and isinstance(data, list) and len(data) > 0:
            # Buscar timestamp en el primer item
            first_item = data[0]
            if 'timestamp' in first_item:
                return first_item['timestamp']
        return None

    def get_total_items_all_scrapers(self):
        """Get the real total count of items from all JSON files"""
        total = 0
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
        
        for scraper_name in self.scrapers:
            data_file = os.path.join(data_dir, f"{scraper_name.replace('_scraper', '')}_data.json")
            if os.path.exists(data_file):
                try:
                    with open(data_file, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            total += len(data)
                except:
                    pass
        
        return total