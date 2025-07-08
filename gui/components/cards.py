# Card Components

import customtkinter as ctk
from gui.config.constants import COLORS, FONT_SIZES, DIMENSIONS

class StatCard(ctk.CTkFrame):
    def __init__(self, parent, title, value, color, icon):
        super().__init__(parent, fg_color=COLORS["card"], corner_radius=DIMENSIONS["large_corner_radius"])
        
        # Inner frame
        inner_frame = ctk.CTkFrame(self, fg_color="transparent")
        inner_frame.pack(padx=20, pady=20)
        
        # Icon
        self.icon_label = ctk.CTkLabel(
            inner_frame,
            text=icon,
            font=("Arial", 32)
        )
        self.icon_label.pack()
        
        # Value
        self.value_label = ctk.CTkLabel(
            inner_frame,
            text=value,
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=color
        )
        self.value_label.pack(pady=5)
        
        # Title
        self.title_label = ctk.CTkLabel(
            inner_frame,
            text=title,
            font=ctk.CTkFont(size=FONT_SIZES["body"]),
            text_color=COLORS["text_secondary"]
        )
        self.title_label.pack()
    
    def update_value(self, new_value):
        """Update the displayed value"""
        self.value_label.configure(text=new_value)

class ActionCard(ctk.CTkFrame):
    def __init__(self, parent, title, description, button_text, button_command, button_color=None):
        super().__init__(parent, fg_color=COLORS["card"], corner_radius=DIMENSIONS["corner_radius"])
        
        # Content
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(padx=20, pady=15, fill="both", expand=True)
        
        # Title
        self.title_label = ctk.CTkLabel(
            content_frame,
            text=title,
            font=ctk.CTkFont(size=FONT_SIZES["subtitle"], weight="bold"),
            text_color=COLORS["text"]
        )
        self.title_label.pack(anchor="w")
        
        # Description
        if description:
            self.desc_label = ctk.CTkLabel(
                content_frame,
                text=description,
                font=ctk.CTkFont(size=FONT_SIZES["body"]),
                text_color=COLORS["text_secondary"],
                wraplength=250
            )
            self.desc_label.pack(anchor="w", pady=(5, 10))
        
        # Button
        self.action_button = ctk.CTkButton(
            content_frame,
            text=button_text,
            command=button_command,
            fg_color=button_color or COLORS["primary"],
            height=DIMENSIONS["button_height"]
        )
        self.action_button.pack(fill="x", pady=(10, 0))