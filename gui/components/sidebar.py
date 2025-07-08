# Sidebar Component - VERSIÓN MEJORADA CON DISEÑO DEL MOCK

import customtkinter as ctk
from gui.config.constants import COLORS, SIDEBAR_WIDTH, FONT_SIZES, DIMENSIONS, ICONS

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, page_callback):
        super().__init__(parent, width=SIDEBAR_WIDTH, corner_radius=0, fg_color=COLORS["sidebar"])
        self.page_callback = page_callback
        self.current_page = "dashboard"
        self.buttons = {}
        
        # Prevent sidebar from shrinking
        self.pack_propagate(False)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup sidebar UI with mock design"""
        # Logo and title section
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(pady=(20, 30))
        
        # Bot icon
        ctk.CTkLabel(
            logo_frame, 
            text=ICONS["bot"], 
            font=("Arial", FONT_SIZES["logo"])
        ).pack()
        
        # Title
        ctk.CTkLabel(
            logo_frame,
            text="CS:GO Arbitrage",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text"]
        ).pack()
        
        # Version
        ctk.CTkLabel(
            logo_frame,
            text="Professional v2.0",
            font=ctk.CTkFont(size=FONT_SIZES["body"]),
            text_color=COLORS["text_secondary"]
        ).pack()
        
        # Navigation buttons
        nav_buttons = [
            ("dashboard", f"{ICONS['dashboard']}  Dashboard"),
            ("scrapers", f"{ICONS['scrapers']}  Scrapers"),
            ("profitability", f"{ICONS['profitability']}  Profitability"),
            ("images", f"{ICONS['images']}  Image Cache"),
            ("config", f"{ICONS['config']}  Configuration"),
            ("debug", f"{ICONS['debug']}  Debug Console"),
            ("analytics", f"{ICONS['analytics']}  Analytics")
        ]
        
        for page_id, label in nav_buttons:
            self.create_nav_button(page_id, label)
        
        # Bottom info section
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(side="bottom", pady=20, padx=20, fill="x")
        
        ctk.CTkLabel(
            info_frame,
            text="System Status",
            font=ctk.CTkFont(size=FONT_SIZES["body"], weight="bold"),
            text_color=COLORS["text"]
        ).pack()
        
        ctk.CTkLabel(
            info_frame,
            text="● All Systems Operational",
            text_color=COLORS["success"],
            font=ctk.CTkFont(size=FONT_SIZES["small"])
        ).pack(pady=5)
        
        ctk.CTkLabel(
            info_frame,
            text="Last Update: Just now",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(size=FONT_SIZES["tiny"])
        ).pack()
    
    def create_nav_button(self, page_id, label):
        """Create navigation button with new design"""
        button = ctk.CTkButton(
            self,
            text=label,
            command=lambda p=page_id: self.switch_page(p),
            font=ctk.CTkFont(size=14),
            height=DIMENSIONS["nav_button_height"],
            corner_radius=DIMENSIONS["corner_radius"],
            anchor="w",
            fg_color="transparent",
            hover_color=COLORS["hover"],
            text_color=COLORS["text_secondary"]
        )
        button.pack(padx=20, pady=5, fill="x")
        self.buttons[page_id] = button
        
        # Highlight current page
        if page_id == self.current_page:
            self.highlight_button(page_id)
    
    def switch_page(self, page_id):
        """Switch to a different page"""
        # Remove highlight from current button
        if self.current_page in self.buttons:
            self.buttons[self.current_page].configure(
                fg_color="transparent",
                text_color=COLORS["text_secondary"]
            )
        
        # Highlight new button
        self.current_page = page_id
        self.highlight_button(page_id)
        
        # Call page callback
        self.page_callback(page_id)
    
    def highlight_button(self, page_id):
        """Highlight the selected button"""
        if page_id in self.buttons:
            self.buttons[page_id].configure(
                fg_color=COLORS["primary"],
                text_color="white"
            )