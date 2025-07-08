# Debug Console Page - Monitor system logs and debugging

import customtkinter as ctk
import os
import threading
from datetime import datetime
from collections import deque
from gui.config.constants import COLORS, FONT_SIZES, DIMENSIONS, REFRESH_INTERVALS
from gui.components.header import PageHeader

class DebugPage(ctk.CTkFrame):
    def __init__(self, parent, app_controller):
        super().__init__(parent, fg_color="transparent")
        self.app = app_controller
        self.log_buffer = deque(maxlen=1000)  # Keep last 1000 log entries
        self.current_filter = "All"
        self.auto_scroll = True
        self.is_paused = False
        
        self.setup_ui()
        self.load_initial_logs()
        self.start_log_monitoring()
    
    def setup_ui(self):
        """Setup debug console UI"""
        # Header
        header_container = ctk.CTkFrame(self, fg_color="transparent")
        header_container.pack(fill="x", padx=20, pady=(20, 10))
        
        self.header = PageHeader(
            header_container,
            "Debug Console",
            "Real-time system logs and debugging information"
        )
        self.header.pack(fill="x")
        
        # Controls
        controls_frame = ctk.CTkFrame(self.header.header_frame, fg_color="transparent")
        controls_frame.pack(side="right", padx=20)
        
        ctk.CTkButton(
            controls_frame,
            text="🗑️ Clear",
            width=80,
            height=35,
            command=self.clear_console
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            controls_frame,
            text="💾 Export",
            width=80,
            height=35,
            command=self.export_logs
        ).pack(side="left", padx=5)
        
        self.pause_btn = ctk.CTkButton(
            controls_frame,
            text="⏸️ Pause",
            width=80,
            height=35,
            command=self.toggle_pause
        )
        self.pause_btn.pack(side="left", padx=5)
        
        # Filter buttons
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=20, pady=5)
        
        self.filter_buttons = {}
        filters = ["All", "Info", "Warning", "Error", "Debug"]
        colors = {
            "All": COLORS["primary"],
            "Info": COLORS["info"],
            "Warning": COLORS["warning"],
            "Error": COLORS["error"],
            "Debug": "#666666"
        }
        
        for i, filter_name in enumerate(filters):
            btn = ctk.CTkButton(
                filter_frame,
                text=filter_name,
                width=80,
                height=30,
                fg_color=colors.get(filter_name, "#444444") if i == 0 else "#444444",
                command=lambda f=filter_name: self.set_filter(f)
            )
            btn.pack(side="left", padx=5)
            self.filter_buttons[filter_name] = btn
        
        # Console container
        console_container = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=15)
        console_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Console text area
        self.console_text = ctk.CTkTextbox(
            console_container,
            fg_color="#0a0a0a",
            font=("Consolas", 11),
            wrap="none",
            text_color=COLORS["text"]
        )
        self.console_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Command input
        input_frame = ctk.CTkFrame(self, fg_color=COLORS["card"], height=50)
        input_frame.pack(fill="x", padx=20, pady=(0, 20))
        input_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            input_frame,
            text=">",
            font=("Consolas", 14),
            text_color=COLORS["success"]
        ).pack(side="left", padx=(20, 10))
        
        self.command_entry = ctk.CTkEntry(
            input_frame,
            font=("Consolas", 12),
            placeholder_text="Enter debug command..."
        )
        self.command_entry.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=10)
        self.command_entry.bind("<Return>", self.execute_command)
        
        ctk.CTkButton(
            input_frame,
            text="Execute",
            width=80,
            height=30,
            command=self.execute_command
        ).pack(side="right", padx=20)
        
        # Auto-scroll checkbox
        auto_scroll_frame = ctk.CTkFrame(self, fg_color="transparent")
        auto_scroll_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        self.auto_scroll_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            auto_scroll_frame,
            text="Auto-scroll to bottom",
            variable=self.auto_scroll_var,
            command=self.toggle_auto_scroll
        ).pack(side="left")
    
    def load_initial_logs(self):
        """Load initial log entries"""
        # Load from log files
        log_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "logs"
        )
        
        # Read main log file
        main_log = os.path.join(log_dir, "bot_v2.log")
        if os.path.exists(main_log):
            try:
                with open(main_log, 'r', encoding='utf-8') as f:
                    # Read last 100 lines
                    lines = f.readlines()[-100:]
                    for line in lines:
                        self.add_log_entry(line.strip())
            except Exception as e:
                self.add_log_entry(f"[ERROR] Failed to load log file: {e}", "Error")
        
        # Add startup message
        self.add_log_entry(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Debug console initialized",
            "Info"
        )
    
    def add_log_entry(self, message, level=None):
        """Add a log entry to the console"""
        if self.is_paused:
            return
        
        # Determine log level from message
        if not level:
            if "[ERROR]" in message or "Error" in message:
                level = "Error"
            elif "[WARNING]" in message or "Warning" in message:
                level = "Warning"
            elif "[DEBUG]" in message:
                level = "Debug"
            else:
                level = "Info"
        
        # Add to buffer
        self.log_buffer.append((message, level, datetime.now()))
        
        # Apply filter
        if self.current_filter != "All" and level != self.current_filter:
            return
        
        # Add to console with color
        color_map = {
            "Info": COLORS["info"],
            "Warning": COLORS["warning"],
            "Error": COLORS["error"],
            "Debug": "#888888"
        }
        
        # Insert with color tag
        self.console_text.insert("end", message + "\n")
        
        # Auto-scroll if enabled
        if self.auto_scroll:
            self.console_text.see("end")
    
    def set_filter(self, filter_name):
        """Set log filter"""
        self.current_filter = filter_name
        
        # Update button colors
        for name, btn in self.filter_buttons.items():
            if name == filter_name:
                color_map = {
                    "All": COLORS["primary"],
                    "Info": COLORS["info"],
                    "Warning": COLORS["warning"],
                    "Error": COLORS["error"],
                    "Debug": "#666666"
                }
                btn.configure(fg_color=color_map.get(name, "#444444"))
            else:
                btn.configure(fg_color="#444444")
        
        # Reapply filter to console
        self.refresh_console()
    
    def refresh_console(self):
        """Refresh console with current filter"""
        self.console_text.delete("1.0", "end")
        
        # Create a copy to avoid mutation during iteration
        buffer_copy = list(self.log_buffer)
        
        for message, level, timestamp in buffer_copy:
            if self.current_filter == "All" or level == self.current_filter:
                # Don't call add_log_entry as it modifies the buffer
                # Add directly to console
                self.console_text.insert("end", message + "\n")
        
        if self.auto_scroll:
            self.console_text.see("end")
    
    def clear_console(self):
        """Clear console content"""
        self.console_text.delete("1.0", "end")
        self.log_buffer.clear()
        self.add_log_entry(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Console cleared",
            "Info"
        )
    
    def export_logs(self):
        """Export logs to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = f"debug_export_{timestamp}.log"
        
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                for message, level, ts in self.log_buffer:
                    f.write(f"{message}\n")
            
            self.add_log_entry(f"[INFO] Logs exported to {export_path}", "Info")
        except Exception as e:
            self.add_log_entry(f"[ERROR] Failed to export logs: {e}", "Error")
    
    def toggle_pause(self):
        """Toggle pause state"""
        self.is_paused = not self.is_paused
        self.pause_btn.configure(text="▶️ Resume" if self.is_paused else "⏸️ Pause")
    
    def toggle_auto_scroll(self):
        """Toggle auto-scroll"""
        self.auto_scroll = self.auto_scroll_var.get()
    
    def execute_command(self, event=None):
        """Execute debug command"""
        command = self.command_entry.get().strip()
        if not command:
            return
        
        # Add command to console
        self.add_log_entry(f"> {command}", "Info")
        
        # Clear input
        self.command_entry.delete(0, "end")
        
        # Process command
        self.process_command(command)
    
    def process_command(self, command):
        """Process debug commands"""
        parts = command.lower().split()
        if not parts:
            return
        
        cmd = parts[0]
        
        if cmd == "help":
            self.show_help()
        elif cmd == "status":
            self.show_status()
        elif cmd == "scrapers":
            self.show_scrapers_status()
        elif cmd == "cache":
            self.show_cache_info()
        elif cmd == "config":
            self.show_config_info()
        elif cmd == "test":
            self.run_test(parts[1] if len(parts) > 1 else None)
        else:
            self.add_log_entry(f"[WARNING] Unknown command: {cmd}", "Warning")
            self.add_log_entry("[INFO] Type 'help' for available commands", "Info")
    
    def show_help(self):
        """Show available commands"""
        help_text = """
Available Commands:
- help       : Show this help message
- status     : Show system status
- scrapers   : Show scrapers status
- cache      : Show cache information
- config     : Show configuration info
- test [name]: Run test (scrapers/profit/cache)
- clear      : Clear console
        """
        for line in help_text.strip().split('\n'):
            self.add_log_entry(line, "Info")
    
    def show_status(self):
        """Show system status"""
        self.add_log_entry("[INFO] System Status:", "Info")
        
        # Scrapers status
        scraper_status = self.app.scraper_controller.get_all_status()
        active = sum(1 for s in scraper_status.values() if s["status"] == "running")
        self.add_log_entry(f"  Active Scrapers: {active}/{len(scraper_status)}", "Info")
        
        # Profitability
        opportunities = len(self.app.profitability_controller.get_opportunities())
        self.add_log_entry(f"  Profit Opportunities: {opportunities}", "Info")
        
        # Cache
        cache_stats = self.app.cache_controller.get_cache_stats()
        self.add_log_entry(f"  Cached Images: {cache_stats.get('total_images', 0):,}", "Info")
        self.add_log_entry(f"  Cache Size: {cache_stats.get('cache_size_mb', 0):.1f} MB", "Info")
    
    def show_scrapers_status(self):
        """Show detailed scrapers status"""
        self.add_log_entry("[INFO] Scrapers Status:", "Info")
        
        scraper_status = self.app.scraper_controller.get_all_status()
        for name, status in scraper_status.items():
            state = status.get("status", "unknown")
            items = status.get("items_fetched", 0)
            self.add_log_entry(f"  {name}: {state} ({items:,} items)", "Info")
    
    def show_cache_info(self):
        """Show cache information"""
        cache_stats = self.app.cache_controller.get_cache_stats()
        self.add_log_entry("[INFO] Cache Information:", "Info")
        for key, value in cache_stats.items():
            self.add_log_entry(f"  {key}: {value}", "Info")
    
    def show_config_info(self):
        """Show configuration information"""
        self.add_log_entry("[INFO] Configuration:", "Info")
        
        # Show loaded configs
        configs = self.app.config_controller.loaded_configs
        for config_name in configs:
            self.add_log_entry(f"  {config_name}: Loaded", "Info")
    
    def run_test(self, test_name):
        """Run specific test"""
        if not test_name:
            self.add_log_entry("[ERROR] Please specify test name: scrapers/profit/cache", "Error")
            return
        
        if test_name == "scrapers":
            self.add_log_entry("[INFO] Testing scrapers connection...", "Info")
            # Run test scraper
            self.app.scraper_controller.run_scraper("waxpeer_scraper", self.test_callback)
        elif test_name == "profit":
            self.add_log_entry("[INFO] Testing profitability engine...", "Info")
            self.app.profitability_controller.calculate_opportunities(1.0, self.test_callback)
        elif test_name == "cache":
            self.add_log_entry("[INFO] Testing cache service...", "Info")
            stats = self.app.cache_controller.get_cache_stats()
            self.add_log_entry(f"[SUCCESS] Cache test passed: {stats.get('total_images', 0)} images", "Info")
        else:
            self.add_log_entry(f"[ERROR] Unknown test: {test_name}", "Error")
    
    def test_callback(self, status, *args):
        """Callback for tests"""
        if status == "success":
            self.add_log_entry(f"[SUCCESS] Test completed successfully", "Info")
        elif status == "error":
            self.add_log_entry(f"[ERROR] Test failed: {args[0] if args else 'Unknown error'}", "Error")
        else:
            self.add_log_entry(f"[INFO] Test status: {status}", "Info")
    
    def start_log_monitoring(self):
        """Start monitoring log files for changes"""
        # This could be implemented to watch log files in real-time
        pass
    
    def refresh(self):
        """Refresh debug console"""
        # Could reload logs or update status
        pass