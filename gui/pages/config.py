# Configuration Page - Gestión de configuraciones

import customtkinter as ctk
import json
from gui.config.constants import COLORS, FONT_SIZES, DIMENSIONS
from gui.components.header import PageHeader

class ConfigPage(ctk.CTkFrame):
    def __init__(self, parent, app_controller):
        super().__init__(parent, fg_color="transparent")
        self.app = app_controller
        self.config_entries = {}
        self.api_entries = {}
        
        self.setup_ui()
        self.load_configurations()
    
    def setup_ui(self):
        """Setup configuration page UI"""
        # Header
        header_container = ctk.CTkFrame(self, fg_color="transparent")
        header_container.pack(fill="x", padx=20, pady=(20, 10))
        
        self.header = PageHeader(
            header_container,
            "Configuration",
            "Manage system settings and API keys"
        )
        self.header.pack(fill="x")
        
        # Save button in header
        save_btn = ctk.CTkButton(
            self.header.header_frame,
            text="💾 Save All Settings",
            width=150,
            height=35,
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            command=self.save_all_settings
        )
        save_btn.pack(side="right", padx=20)
        
        # Scrollable container
        self.scroll_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.scroll_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create sections
        self.create_api_keys_section()
        self.create_general_settings_section()
        self.create_proxy_section()
        self.create_performance_section()
    
    def create_api_keys_section(self):
        """Create API keys configuration section"""
        section = self.create_section("API Keys", self.scroll_container)
        
        api_configs = [
            ("Waxpeer API Key", "waxpeer_key", True),
            ("Empire API Key", "empire_key", True),
            ("BitSkins API Key", "bitskins_key", False),
            ("SkinPort API Key", "skinport_key", False),
        ]
        
        for label, key, show_value in api_configs:
            self.create_api_key_field(section, label, key, show_value)
    
    def create_api_key_field(self, parent, label, key, show_value=False):
        """Create API key input field"""
        field_frame = ctk.CTkFrame(parent, fg_color="transparent")
        field_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(
            field_frame,
            text=label,
            font=ctk.CTkFont(size=12),
            width=150,
            anchor="w"
        ).pack(side="left", padx=(0, 10))
        
        entry = ctk.CTkEntry(
            field_frame,
            width=400,
            show="" if not show_value else None
        )
        entry.pack(side="left", padx=(0, 10))
        
        # Toggle visibility button
        def toggle_visibility():
            current_show = entry.cget("show")
            entry.configure(show="" if current_show else None)
            toggle_btn.configure(text="🙈" if current_show else "👁️")
        
        toggle_btn = ctk.CTkButton(
            field_frame,
            text="👁️",
            width=30,
            height=28,
            command=toggle_visibility
        )
        toggle_btn.pack(side="left")
        
        self.api_entries[key] = entry
    
    def create_general_settings_section(self):
        """Create general settings section"""
        section = self.create_section("General Settings", self.scroll_container)
        
        settings_frame = ctk.CTkFrame(section, fg_color="transparent")
        settings_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        # Settings checkboxes
        settings = [
            ("auto_start", "Auto-start on launch", True),
            ("notifications", "Enable notifications", True),
            ("dark_mode", "Dark mode", True),
            ("show_profit_usd", "Show profit in USD", True),
            ("auto_refresh", "Auto-refresh data", False),
            ("sound_alerts", "Enable sound alerts", False),
        ]
        
        self.setting_vars = {}
        
        for i, (key, label, default) in enumerate(settings):
            row = i // 2
            col = i % 2
            
            var = ctk.BooleanVar(value=default)
            self.setting_vars[key] = var
            
            setting_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
            setting_frame.grid(row=row, column=col, padx=20, pady=5, sticky="w")
            
            switch = ctk.CTkSwitch(
                setting_frame,
                text=label,
                font=ctk.CTkFont(size=12),
                variable=var
            )
            switch.pack()
    
    def create_proxy_section(self):
        """Create proxy configuration section"""
        section = self.create_section("Proxy Configuration", self.scroll_container)
        
        # Enable proxy checkbox
        self.proxy_enabled = ctk.BooleanVar(value=False)
        proxy_check = ctk.CTkCheckBox(
            section,
            text="Enable Proxy",
            font=ctk.CTkFont(size=12),
            variable=self.proxy_enabled,
            command=self.toggle_proxy_fields
        )
        proxy_check.pack(anchor="w", padx=20, pady=5)
        
        # Proxy fields frame
        self.proxy_frame = ctk.CTkFrame(section, fg_color="transparent")
        self.proxy_frame.pack(fill="x", padx=20, pady=5)
        
        # Proxy type
        self.create_field(
            self.proxy_frame,
            "Proxy Type",
            "proxy_type",
            field_type="combo",
            values=["HTTP", "HTTPS", "SOCKS5"]
        )
        
        # Other proxy fields
        proxy_fields = [
            ("Host", "proxy_host", "proxy.example.com"),
            ("Port", "proxy_port", "8080"),
            ("Username", "proxy_user", "user123"),
            ("Password", "proxy_pass", "••••••••"),
        ]
        
        for label, key, placeholder in proxy_fields:
            show_pass = "•" in placeholder
            self.create_field(
                self.proxy_frame,
                label,
                key,
                placeholder=placeholder,
                show="•" if show_pass else None
            )
        
        # Initially disable proxy fields
        self.toggle_proxy_fields()
    
    def create_performance_section(self):
        """Create performance settings section"""
        section = self.create_section("Performance Settings", self.scroll_container)
        
        perf_settings = [
            ("Max Concurrent Scrapers", "max_concurrent", 1, 10, 3),
            ("Request Timeout (seconds)", "timeout", 10, 120, 30),
            ("Retry Attempts", "retries", 0, 10, 3),
            ("Delay Between Requests (seconds)", "delay", 0, 10, 2),
        ]
        
        for label, key, min_val, max_val, default in perf_settings:
            self.create_slider_field(section, label, key, min_val, max_val, default)
    
    def create_section(self, title, parent):
        """Create a configuration section"""
        section = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=15)
        section.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            section,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        return section
    
    def create_field(self, parent, label, key, placeholder="", show=None, field_type="entry", values=None):
        """Create a configuration field"""
        field_frame = ctk.CTkFrame(parent, fg_color="transparent")
        field_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            field_frame,
            text=label,
            font=ctk.CTkFont(size=12),
            width=100,
            anchor="w"
        ).pack(side="left", padx=(20, 10))
        
        if field_type == "entry":
            field = ctk.CTkEntry(
                field_frame,
                width=200,
                placeholder_text=placeholder,
                show=show
            )
            field.pack(side="left")
        elif field_type == "combo":
            field = ctk.CTkComboBox(
                field_frame,
                values=values or [],
                width=200
            )
            field.pack(side="left")
        
        self.config_entries[key] = field
        return field
    
    def create_slider_field(self, parent, label, key, min_val, max_val, default):
        """Create a slider configuration field"""
        field_frame = ctk.CTkFrame(parent, fg_color="transparent")
        field_frame.pack(fill="x", padx=20, pady=10)
        
        # Label
        ctk.CTkLabel(
            field_frame,
            text=label,
            font=ctk.CTkFont(size=12),
            anchor="w"
        ).pack(anchor="w")
        
        # Value label
        value_label = ctk.CTkLabel(
            field_frame,
            text=str(default),
            font=ctk.CTkFont(size=12),
            text_color=COLORS["info"]
        )
        value_label.pack(anchor="e")
        
        # Slider
        slider = ctk.CTkSlider(
            field_frame,
            from_=min_val,
            to=max_val,
            number_of_steps=max_val - min_val,
            command=lambda v: value_label.configure(text=str(int(v)))
        )
        slider.pack(fill="x", pady=5)
        slider.set(default)
        
        self.config_entries[key] = (slider, value_label)
    
    def toggle_proxy_fields(self):
        """Enable/disable proxy fields based on checkbox"""
        if self.proxy_enabled.get():
            for widget in self.proxy_frame.winfo_children():
                for child in widget.winfo_children():
                    if isinstance(child, (ctk.CTkEntry, ctk.CTkComboBox)):
                        child.configure(state="normal")
        else:
            for widget in self.proxy_frame.winfo_children():
                for child in widget.winfo_children():
                    if isinstance(child, (ctk.CTkEntry, ctk.CTkComboBox)):
                        child.configure(state="disabled")
    
    def load_configurations(self):
        """Load current configurations"""
        # Load API keys
        api_keys = self.app.config_controller.get_config("api_keys")
        for key, entry in self.api_entries.items():
            if key.replace("_key", "") in api_keys:
                api_data = api_keys[key.replace("_key", "")]
                if isinstance(api_data, dict) and 'api_key' in api_data:
                    entry.insert(0, api_data['api_key'])
        
        # Load general settings
        settings = self.app.config_controller.get_config("settings")
        # Actualizar checkboxes según configuración guardada
        
        # Load proxy settings
        proxy_config = self.app.config_controller.get_config("scrapers")
        # Actualizar campos de proxy según configuración
    
    def save_all_settings(self):
        """Save all configuration changes"""
        try:
            # Save API keys
            api_config = self.app.config_controller.get_config("api_keys") or {}
            
            for key, entry in self.api_entries.items():
                value = entry.get()
                if value:
                    platform = key.replace("_key", "")
                    api_config[platform] = {"api_key": value, "active": True}
            
            # Save the entire api_keys config
            self.app.config_controller.save_config("api_keys", api_config)
            
            # Save general settings
            settings_config = self.app.config_controller.get_config("settings") or {}
            
            for key, var in self.setting_vars.items():
                settings_config[key] = var.get()
            
            # Save the entire settings config
            self.app.config_controller.save_config("settings", settings_config)
            
            # Show success message
            print("Settings saved successfully!")
            
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def refresh(self):
        """Refresh configuration data"""
        self.load_configurations()