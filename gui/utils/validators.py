# Input Validation Utilities

import re
import os
from urllib.parse import urlparse

class Validators:
    """Utility class for input validation"""
    
    @staticmethod
    def validate_api_key(api_key, min_length=10):
        """Validate API key format"""
        if not api_key or not isinstance(api_key, str):
            return False, "API key cannot be empty"
        
        if len(api_key) < min_length:
            return False, f"API key must be at least {min_length} characters"
        
        # Check for basic format (alphanumeric and some special chars)
        if not re.match(r'^[a-zA-Z0-9_\-]+$', api_key):
            return False, "API key contains invalid characters"
        
        return True, "Valid API key"
    
    @staticmethod
    def validate_url(url):
        """Validate URL format"""
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False, "Invalid URL format"
            
            if result.scheme not in ['http', 'https']:
                return False, "URL must use HTTP or HTTPS"
            
            return True, "Valid URL"
        except Exception as e:
            return False, f"URL validation error: {str(e)}"
    
    @staticmethod
    def validate_number(value, min_val=None, max_val=None, allow_float=True):
        """Validate numeric input"""
        try:
            if allow_float:
                num_val = float(value)
            else:
                num_val = int(value)
            
            if min_val is not None and num_val < min_val:
                return False, f"Value must be at least {min_val}"
            
            if max_val is not None and num_val > max_val:
                return False, f"Value must be at most {max_val}"
            
            return True, "Valid number"
        except ValueError:
            return False, "Must be a valid number"
    
    @staticmethod
    def validate_percentage(value):
        """Validate percentage input (0-100)"""
        return Validators.validate_number(value, min_val=0, max_val=100)
    
    @staticmethod
    def validate_timeout(value):
        """Validate timeout value (positive integer)"""
        is_valid, message = Validators.validate_number(value, min_val=1, max_val=300, allow_float=False)
        if not is_valid:
            return False, "Timeout must be between 1 and 300 seconds"
        return True, "Valid timeout"
    
    @staticmethod
    def validate_delay(value):
        """Validate delay value (positive float)"""
        is_valid, message = Validators.validate_number(value, min_val=0.1, max_val=60.0)
        if not is_valid:
            return False, "Delay must be between 0.1 and 60.0 seconds"
        return True, "Valid delay"
    
    @staticmethod
    def validate_path(path, must_exist=False, must_be_dir=False):
        """Validate file/directory path"""
        if not path or not isinstance(path, str):
            return False, "Path cannot be empty"
        
        if must_exist and not os.path.exists(path):
            return False, "Path does not exist"
        
        if must_be_dir and os.path.exists(path) and not os.path.isdir(path):
            return False, "Path must be a directory"
        
        # Check for valid path characters
        invalid_chars = '<>:"|?*'
        if any(char in path for char in invalid_chars):
            return False, "Path contains invalid characters"
        
        return True, "Valid path"
    
    @staticmethod
    def validate_json(json_str):
        """Validate JSON string"""
        try:
            import json
            json.loads(json_str)
            return True, "Valid JSON"
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}"
    
    @staticmethod
    def validate_proxy(proxy_str):
        """Validate proxy format (host:port)"""
        if not proxy_str:
            return True, "No proxy specified"
        
        try:
            if ':' not in proxy_str:
                return False, "Proxy must be in format host:port"
            
            host, port = proxy_str.split(':', 1)
            
            if not host:
                return False, "Proxy host cannot be empty"
            
            port_num = int(port)
            if not (1 <= port_num <= 65535):
                return False, "Proxy port must be between 1 and 65535"
            
            return True, "Valid proxy"
        except ValueError:
            return False, "Invalid proxy port (must be a number)"
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, email):
            return True, "Valid email"
        return False, "Invalid email format"
    
    @staticmethod
    def sanitize_filename(filename):
        """Sanitize filename by removing invalid characters"""
        # Remove invalid characters
        invalid_chars = '<>:"|?*/'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing whitespace and dots
        filename = filename.strip('. ')
        
        # Ensure filename is not empty
        if not filename:
            filename = "untitled"
        
        return filename
    
    @staticmethod
    def validate_config_key(key):
        """Validate configuration key name"""
        if not key or not isinstance(key, str):
            return False, "Key cannot be empty"
        
        # Check key format (alphanumeric, underscore, dash)
        if not re.match(r'^[a-zA-Z0-9_\-]+$', key):
            return False, "Key can only contain letters, numbers, underscores, and dashes"
        
        if len(key) > 50:
            return False, "Key must be 50 characters or less"
        
        return True, "Valid configuration key"

class FormValidator:
    """Utility for validating form data"""
    
    def __init__(self):
        self.errors = {}
    
    def validate_field(self, field_name, value, validator_func, *args, **kwargs):
        """Validate a single field"""
        is_valid, message = validator_func(value, *args, **kwargs)
        if not is_valid:
            self.errors[field_name] = message
        return is_valid
    
    def has_errors(self):
        """Check if there are validation errors"""
        return len(self.errors) > 0
    
    def get_errors(self):
        """Get all validation errors"""
        return self.errors.copy()
    
    def get_error_message(self):
        """Get formatted error message"""
        if not self.errors:
            return ""
        
        if len(self.errors) == 1:
            return list(self.errors.values())[0]
        
        return f"Multiple errors: {', '.join(self.errors.values())}"
    
    def clear_errors(self):
        """Clear all validation errors"""
        self.errors = {}