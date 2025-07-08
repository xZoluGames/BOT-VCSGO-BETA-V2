# Scrapers Page - Implementación completa con diseño del mock

import customtkinter as ctk
from gui.config.constants import COLORS, FONT_SIZES, DIMENSIONS, ICONS, REFRESH_INTERVALS
from gui.components.header import PageHeader
import threading

class ScrapersPage(ctk.CTkFrame):
    def __init__(self, parent, app_controller):
        super().__init__(parent, fg_color="transparent")
        self.app = app_controller
        self.scraper_cards = {}
        self.auto_refresh = True
        self.refresh_interval = REFRESH_INTERVALS["scrapers"]
        
        self.setup_ui()
        self.start_auto_refresh()
    
    def setup_ui(self):
        """Setup scrapers page UI"""
        # Header
        self.header = PageHeader(
            self, 
            "Scraper Management", 
            "Control and monitor individual marketplace scrapers"
        )
        self.header.pack(fill="x", padx=20, pady=(20, 10))
        
        # Controls frame
        controls_frame = ctk.CTkFrame(self.header.header_frame, fg_color="transparent")
        controls_frame.pack(side="right", padx=20)
        
        # Control buttons
        ctk.CTkButton(
            controls_frame, 
            text="▶️ Start All", 
            width=100, 
            height=35, 
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            command=self.start_all_scrapers
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            controls_frame, 
            text="⏸️ Pause All", 
            width=100, 
            height=35, 
            fg_color=COLORS["warning"],
            hover_color=COLORS["warning_hover"],
            command=self.pause_all_scrapers
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            controls_frame, 
            text="🔧 Settings", 
            width=100, 
            height=35,
            command=self.open_settings
        ).pack(side="left", padx=5)
        
        # Scrollable frame for scraper cards
        self.scrapers_frame = ctk.CTkScrollableFrame(
            self, 
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["hover"]
        )
        self.scrapers_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create scraper cards
        self.create_scraper_cards()
    
    def create_scraper_cards(self):
        """Create individual scraper cards"""
        scraper_status = self.app.scraper_controller.get_all_status()
        
        # Configure grid
        for i in range(2):
            self.scrapers_frame.grid_columnconfigure(i, weight=1)
        
        row = 0
        col = 0
        
        for scraper_name, status in scraper_status.items():
            # Create card
            card = self.create_single_scraper_card(scraper_name, status)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
            
            # Store reference
            self.scraper_cards[scraper_name] = card
            
            # Update grid position
            col += 1
            if col > 1:
                col = 0
                row += 1
    
    def create_single_scraper_card(self, scraper_name, status):
        """Create a single scraper card with all controls"""
        # Main card frame
        card = ctk.CTkFrame(self.scrapers_frame, fg_color=COLORS["card"], corner_radius=15)
        
        # Header with status
        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 5))
        
        # Status indicator
        status_color = {
            "running": COLORS["success"],
            "idle": COLORS["warning"],
            "error": COLORS["error"],
            "stopped": COLORS["inactive"]
        }.get(status["status"], COLORS["inactive"])
        
        ctk.CTkLabel(
            header_frame, 
            text="●", 
            text_color=status_color,
            font=("Arial", 16)
        ).pack(side="left", padx=(0, 10))
        
        # Scraper name
        display_name = scraper_name.replace("_scraper", "").replace("_", " ").title()
        ctk.CTkLabel(
            header_frame,
            text=display_name,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"]
        ).pack(side="left")
        
        # Toggle switch
        toggle = ctk.CTkSwitch(
            header_frame,
            text="",
            width=50,
            button_color=status_color,
            progress_color=status_color,
            command=lambda: self.toggle_scraper(scraper_name)
        )
        toggle.pack(side="right")
        
        # Set toggle state
        if status["config"]["enabled"] and status["status"] == "running":
            toggle.select()
        
        # Store toggle reference
        card.toggle = toggle
        
        # Stats
        stats_frame = ctk.CTkFrame(card, fg_color="transparent")
        stats_frame.pack(fill="x", padx=20, pady=5)
        
        items_text = f"Items: {status.get('items_fetched', 0):,}"
        success_text = f"Success: {status.get('success_rate', 0)}%"
        
        ctk.CTkLabel(
            stats_frame,
            text=items_text,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        ).pack(side="left", padx=(0, 20))
        
        ctk.CTkLabel(
            stats_frame,
            text=success_text,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        ).pack(side="left")
        
        # Settings section
        settings_frame = ctk.CTkFrame(card, fg_color="#1a1a1a", corner_radius=10)
        settings_frame.pack(fill="x", padx=20, pady=10)
        
        # Row 1: Proxy and Loop
        row1 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=(10, 5))
        
        proxy_cb = ctk.CTkCheckBox(
            row1, 
            text="Use Proxy", 
            font=ctk.CTkFont(size=12),
            command=lambda: self.update_config(scraper_name, "use_proxy", proxy_cb.get())
        )
        proxy_cb.pack(side="left", padx=(0, 20))
        if status["config"].get("use_proxy", False):
            proxy_cb.select()
        
        loop_cb = ctk.CTkCheckBox(
            row1, 
            text="Run in Loop", 
            font=ctk.CTkFont(size=12),
            command=lambda: self.update_config(scraper_name, "run_in_loop", loop_cb.get())
        )
        loop_cb.pack(side="left")
        if status["config"].get("run_in_loop", False):
            loop_cb.select()
        
        # Row 2: Timeout
        row2 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(row2, text="Timeout (s):", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        
        timeout_value = ctk.CTkLabel(row2, text=str(status["config"]["timeout"]), font=ctk.CTkFont(size=12), width=30)
        timeout_value.pack(side="right")
        
        timeout_slider = ctk.CTkSlider(
            row2, 
            from_=1, 
            to=60, 
            number_of_steps=59, 
            width=150,
            command=lambda v: self.update_slider_value(scraper_name, "timeout", v, timeout_value)
        )
        timeout_slider.pack(side="right", padx=(10, 5))
        timeout_slider.set(status["config"]["timeout"])
        
        # Row 3: Delay
        row3 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row3.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(row3, text="Delay (s):", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        
        delay_value = ctk.CTkLabel(row3, text=f"{status['config']['delay']:.1f}", font=ctk.CTkFont(size=12), width=30)
        delay_value.pack(side="right")
        
        delay_slider = ctk.CTkSlider(
            row3, 
            from_=0, 
            to=10, 
            number_of_steps=20, 
            width=150,
            command=lambda v: self.update_slider_value(scraper_name, "delay", v, delay_value, True)
        )
        delay_slider.pack(side="right", padx=(10, 5))
        delay_slider.set(status["config"]["delay"])
        
        # Row 4: Retries
        row4 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row4.pack(fill="x", padx=15, pady=(5, 10))
        
        ctk.CTkLabel(row4, text="Max Retries:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        
        retries_value = ctk.CTkLabel(row4, text=str(status["config"]["max_retries"]), font=ctk.CTkFont(size=12), width=30)
        retries_value.pack(side="right")
        
        retries_slider = ctk.CTkSlider(
            row4, 
            from_=0, 
            to=10, 
            number_of_steps=10, 
            width=150,
            command=lambda v: self.update_slider_value(scraper_name, "max_retries", v, retries_value)
        )
        retries_slider.pack(side="right", padx=(10, 5))
        retries_slider.set(status["config"]["max_retries"])
        
        # Action buttons
        actions_frame = ctk.CTkFrame(card, fg_color="transparent")
        actions_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        run_btn = ctk.CTkButton(
            actions_frame, 
            text="▶️ Run Now", 
            width=90, 
            height=30,
            fg_color=COLORS["success"] if status["config"]["enabled"] else COLORS["inactive"],
            command=lambda: self.run_single_scraper(scraper_name)
        )
        run_btn.pack(side="left", padx=5)
        
        stats_btn = ctk.CTkButton(
            actions_frame, 
            text="📊 Stats", 
            width=90, 
            height=30,
            command=lambda: self.show_scraper_stats(scraper_name)
        )
        stats_btn.pack(side="left", padx=5)
        
        advanced_btn = ctk.CTkButton(
            actions_frame, 
            text="🔧 Advanced", 
            width=90, 
            height=30,
            command=lambda: self.show_advanced_settings(scraper_name)
        )
        advanced_btn.pack(side="left", padx=5)
        
        # Store button references
        card.run_btn = run_btn
        card.stats_btn = stats_btn
        card.advanced_btn = advanced_btn
        
        return card
    
    def toggle_scraper(self, scraper_name):
        """Toggle scraper on/off"""
        if scraper_name in self.scraper_cards:
            card = self.scraper_cards[scraper_name]
            enabled = card.toggle.get()
            
            if enabled:
                self.app.scraper_controller.run_scraper(scraper_name, self.scraper_callback)
            else:
                self.app.scraper_controller.stop_scraper(scraper_name)
            
            self.app.scraper_controller.update_scraper_config(scraper_name, "enabled", enabled)
    
    def update_config(self, scraper_name, key, value):
        """Update scraper configuration"""
        self.app.scraper_controller.update_scraper_config(scraper_name, key, value)
    
    def update_slider_value(self, scraper_name, key, value, is_float=False):
        """Update slider value and label"""
        if is_float:
            display_value = f"{value:.1f}"
            config_value = round(value, 1)
        else:
            display_value = str(int(value))
            config_value = int(value)
        
        # Update configuration
        self.app.scraper_controller.update_scraper_config(scraper_name, key, config_value)
    
    def run_single_scraper(self, scraper_name):
        """Run a single scraper"""
        def callback(status, name, *args):
            self.after(0, lambda: self.update_scraper_status(name, status, *args))
        
        self.app.scraper_controller.run_scraper(scraper_name, callback)
    
    def scraper_callback(self, status, scraper_name, *args):
        """Callback for scraper status updates"""
        self.after(0, lambda: self.update_scraper_status(scraper_name, status, *args))
    
    def update_scraper_status(self, scraper_name, status, *args):
        """Update scraper card based on status"""
        if scraper_name not in self.scraper_cards:
            return
        
        card = self.scraper_cards[scraper_name]
        
        # Update visual elements based on status
        if status == "started":
            # Update status color to green
            self.update_card_status(card, "running", COLORS["success"])
            
        elif status == "completed":
            items_count = args[0] if args else 0
            # Update status to idle
            self.update_card_status(card, "idle", COLORS["warning"])
            # Update items count
            self.update_card_stats(card, scraper_name, items_count)
            
        elif status == "error":
            error_msg = args[0] if args else "Unknown error"
            # Update status to error
            self.update_card_status(card, "error", COLORS["error"])

    def update_card_status(self, card, status, color):
        """Update card status indicator"""
        # Find the status indicator (first label with ●)
        for widget in card.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkLabel) and child.cget("text") == "●":
                        child.configure(text_color=color)
                        break
        
        # Update toggle color
        if hasattr(card, 'toggle'):
            card.toggle.configure(button_color=color, progress_color=color)

    def update_card_stats(self, card, scraper_name, items_count):
        """Update card statistics"""
        # Get current scraper status
        status = self.app.scraper_controller.get_scraper_status(scraper_name)
        
        # Update the status in controller
        status["items_fetched"] = items_count
        status["success_rate"] = 100 if items_count > 0 else 0
        
        # Find stats labels and update them
        for widget in card.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkLabel):
                        text = child.cget("text")
                        if "Items:" in text:
                            child.configure(text=f"Items: {items_count:,}")
                        elif "Success:" in text:
                            success_rate = status.get("success_rate", 0)
                            child.configure(text=f"Success: {success_rate}%")
    
    def refresh_single_card(self, scraper_name):
        """Refresh a single scraper card"""
        # Get updated status
        status = self.app.scraper_controller.get_scraper_status(scraper_name)
        
        # Update card if it exists
        if scraper_name in self.scraper_cards:
            # This is a simplified version - in production you'd update the specific elements
            pass
    
    def start_all_scrapers(self):
        """Start all scrapers"""
        count = self.app.scraper_controller.run_all_scrapers(self.scraper_callback)
        print(f"Started {count} scrapers")
    
    def pause_all_scrapers(self):
        """Pause all scrapers"""
        for scraper_name in self.scraper_cards:
            self.app.scraper_controller.stop_scraper(scraper_name)
    
    def open_settings(self):
        """Open global scraper settings"""
        print("Opening scraper settings...")
    
    def show_scraper_stats(self, scraper_name):
        """Show detailed statistics for a scraper"""
        print(f"Showing stats for {scraper_name}")
    
    def show_advanced_settings(self, scraper_name):
        """Show advanced settings for a scraper"""
        print(f"Showing advanced settings for {scraper_name}")
    
    def refresh(self):
        """Refresh all scraper cards"""
        for scraper_name in self.scraper_cards:
            self.refresh_single_card(scraper_name)
    
    def start_auto_refresh(self):
        """Start auto-refresh timer"""
        if self.auto_refresh:
            self.refresh()
            self.after(self.refresh_interval, self.start_auto_refresh)