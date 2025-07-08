# Data Formatting Utilities

from datetime import datetime
import json

class DataFormatter:
    """Utility class for formatting data for display"""
    
    @staticmethod
    def format_number(value, decimals=2):
        """Format number with thousands separators"""
        try:
            if isinstance(value, (int, float)):
                if decimals == 0:
                    return f"{int(value):,}"
                else:
                    return f"{value:,.{decimals}f}"
            return str(value)
        except:
            return "0"
    
    @staticmethod
    def format_currency(value, currency="$"):
        """Format value as currency"""
        try:
            if isinstance(value, (int, float)):
                return f"{currency}{value:,.2f}"
            return f"{currency}0.00"
        except:
            return f"{currency}0.00"
    
    @staticmethod
    def format_percentage(value, decimals=2):
        """Format value as percentage"""
        try:
            if isinstance(value, (int, float)):
                return f"{value:.{decimals}f}%"
            return "0%"
        except:
            return "0%"
    
    @staticmethod
    def format_datetime(dt, format_str="%Y-%m-%d %H:%M:%S"):
        """Format datetime object"""
        try:
            if isinstance(dt, datetime):
                return dt.strftime(format_str)
            elif isinstance(dt, str):
                # Try to parse string datetime
                parsed_dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                return parsed_dt.strftime(format_str)
            return str(dt)
        except:
            return "Unknown"
    
    @staticmethod
    def format_time_ago(dt):
        """Format datetime as 'time ago' string"""
        try:
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            
            if not isinstance(dt, datetime):
                return "Unknown"
            
            now = datetime.now()
            diff = now - dt
            
            if diff.days > 0:
                return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                return "Just now"
        except:
            return "Unknown"
    
    @staticmethod
    def format_file_size(size_bytes):
        """Format file size in human readable format"""
        try:
            if size_bytes == 0:
                return "0 B"
            
            size_names = ["B", "KB", "MB", "GB", "TB"]
            import math
            i = int(math.floor(math.log(size_bytes, 1024)))
            p = math.pow(1024, i)
            s = round(size_bytes / p, 2)
            return f"{s} {size_names[i]}"
        except:
            return "0 B"
    
    @staticmethod
    def truncate_text(text, max_length=50, suffix="..."):
        """Truncate text if it's too long"""
        try:
            if len(text) <= max_length:
                return text
            return text[:max_length - len(suffix)] + suffix
        except:
            return str(text)
    
    @staticmethod
    def format_status(status):
        """Format status string with appropriate styling"""
        status_map = {
            "running": "🟢 Running",
            "idle": "⚪ Idle", 
            "error": "🔴 Error",
            "stopped": "⏹️ Stopped",
            "pending": "🟡 Pending",
            "completed": "✅ Completed"
        }
        return status_map.get(status.lower(), f"❓ {status.title()}")
    
    @staticmethod
    def format_profit_color(profit_percent):
        """Get color for profit percentage"""
        try:
            profit = float(profit_percent)
            if profit >= 5:
                return "#00ff00"  # Green for high profit
            elif profit >= 2:
                return "#ffaa00"  # Orange for medium profit
            elif profit >= 0:
                return "#0099cc"  # Blue for low profit
            else:
                return "#ff0000"  # Red for loss
        except:
            return "#cccccc"  # Gray for unknown
    
    @staticmethod
    def format_json(data, indent=2):
        """Format data as pretty JSON"""
        try:
            return json.dumps(data, indent=indent, ensure_ascii=False)
        except:
            return str(data)
    
    @staticmethod
    def safe_get(data, key, default="N/A"):
        """Safely get value from dictionary"""
        try:
            if isinstance(data, dict):
                return data.get(key, default)
            elif hasattr(data, key):
                return getattr(data, key, default)
            else:
                return default
        except:
            return default

class TableFormatter:
    """Utility for formatting table data"""
    
    @staticmethod
    def format_table_row(data, columns):
        """Format a single row for table display"""
        row = []
        for col in columns:
            value = DataFormatter.safe_get(data, col["key"], col.get("default", ""))
            
            # Apply column-specific formatting
            if col.get("type") == "currency":
                value = DataFormatter.format_currency(value)
            elif col.get("type") == "percentage":
                value = DataFormatter.format_percentage(value)
            elif col.get("type") == "number":
                value = DataFormatter.format_number(value, col.get("decimals", 2))
            elif col.get("type") == "datetime":
                value = DataFormatter.format_datetime(value, col.get("format", "%Y-%m-%d %H:%M"))
            elif col.get("type") == "time_ago":
                value = DataFormatter.format_time_ago(value)
            elif col.get("type") == "truncate":
                value = DataFormatter.truncate_text(str(value), col.get("max_length", 50))
            
            row.append(str(value))
        
        return row
    
    @staticmethod
    def format_table_data(data_list, columns):
        """Format multiple rows for table display"""
        return [TableFormatter.format_table_row(row, columns) for row in data_list]