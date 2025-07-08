# Theme Configuration

import customtkinter as ctk
from .constants import COLORS

class ThemeManager:
    def __init__(self):
        self.current_theme = "dark"
        self.setup_theme()
    
    def setup_theme(self):
        """Configure CustomTkinter theme"""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
    
    def get_color(self, color_name):
        """Get color by name"""
        return COLORS.get(color_name, "#ffffff")
    
    def get_button_style(self, button_type="primary"):
        """Get button styling"""
        styles = {
            "primary": {
                "fg_color": COLORS["primary"],
                "hover_color": "#0099cc",
                "text_color": "white"
            },
            "success": {
                "fg_color": COLORS["success"],
                "hover_color": "#00cc00",
                "text_color": "white"
            },
            "warning": {
                "fg_color": COLORS["warning"],
                "hover_color": "#cc8800",
                "text_color": "white"
            },
            "error": {
                "fg_color": COLORS["error"],
                "hover_color": "#cc0000",
                "text_color": "white"
            }
        }
        return styles.get(button_type, styles["primary"])
    
    def get_card_style(self):
        """Get card styling"""
        return {
            "fg_color": COLORS["card"],
            "corner_radius": 10,
            "border_width": 1,
            "border_color": COLORS["border"]
        }