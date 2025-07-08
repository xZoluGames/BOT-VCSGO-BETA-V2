# Configuration Controller

import json
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class ConfigController:
    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config")
        self.config_files = {
            "scrapers": "scrapers.json",
            "api_keys": "api_keys.json", 
            "settings": "settings.json",
            "gui_settings": "gui_settings.json"
        }
        self.config_data = {}
        
        self.load_all_configs()
    
    def load_all_configs(self):
        """Load all configuration files"""
        for config_name, filename in self.config_files.items():
            self.load_config(config_name, filename)
    
    def load_config(self, config_name, filename):
        """Load a specific configuration file"""
        try:
            config_path = os.path.join(self.config_dir, filename)
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.config_data[config_name] = json.load(f)
                    print(f"Loaded config: {config_name}")
            else:
                print(f"Config file not found: {config_path}")
                self.config_data[config_name] = {}
        except Exception as e:
            print(f"Error loading {config_name}: {e}")
            self.config_data[config_name] = {}
    
    def save_config(self, config_name):
        """Save a specific configuration file"""
        try:
            if config_name not in self.config_files:
                raise ValueError(f"Unknown config: {config_name}")
            
            filename = self.config_files[config_name]
            config_path = os.path.join(self.config_dir, filename)
            
            # Ensure directory exists
            os.makedirs(self.config_dir, exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(self.config_data[config_name], f, indent=2)
            
            print(f"Saved config: {config_name}")
            return True
            
        except Exception as e:
            print(f"Error saving {config_name}: {e}")
            return False
    
    def get_config(self, config_name):
        """Get configuration data"""
        return self.config_data.get(config_name, {}).copy()
    
    def update_config(self, config_name, key, value):
        """Update a configuration value"""
        if config_name not in self.config_data:
            self.config_data[config_name] = {}
        
        self.config_data[config_name][key] = value
        return self.save_config(config_name)
    
    def get_scraper_config(self, scraper_name):
        """Get configuration for a specific scraper"""
        scrapers_config = self.get_config("scrapers")
        return scrapers_config.get(scraper_name, {})
    
    def update_scraper_config(self, scraper_name, config_data):
        """Update configuration for a specific scraper"""
        if "scrapers" not in self.config_data:
            self.config_data["scrapers"] = {}
        
        self.config_data["scrapers"][scraper_name] = config_data
        return self.save_config("scrapers")
    
    def validate_api_key(self, platform, api_key):
        """Validate an API key (basic validation)"""
        if not api_key or len(api_key) < 10:
            return False, "API key too short"
        
        # Platform-specific validation could be added here
        return True, "Valid"
    
    def update_api_key(self, platform, api_key, api_type="bearer"):
        """Update API key for a platform"""
        is_valid, message = self.validate_api_key(platform, api_key)
        if not is_valid:
            return False, message
        
        if "api_keys" not in self.config_data:
            self.config_data["api_keys"] = {}
        
        self.config_data["api_keys"][platform] = {
            "api_key": api_key,
            "type": api_type
        }
        
        success = self.save_config("api_keys")
        return success, "API key updated" if success else "Failed to save"