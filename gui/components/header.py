# Header Component

import customtkinter as ctk
from gui.config.constants import COLORS, FONT_SIZES, DIMENSIONS

class PageHeader(ctk.CTkFrame):
    def __init__(self, parent, title, subtitle="", show_refresh=True):
        super().__init__(parent, height=DIMENSIONS["header_height"], fg_color=COLORS["card"])
        self.pack_propagate(False)
        
        # Header frame for content
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="both", expand=True, padx=20)
        
        # Title section
        title_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_frame.pack(side="left", fill="y", pady=15)
        
        # Title
        self.title_label = ctk.CTkLabel(
            title_frame,
            text=title,
            font=ctk.CTkFont(size=FONT_SIZES["title"], weight="bold"),
            text_color=COLORS["text"]
        )
        self.title_label.pack(anchor="w")
        
        # Subtitle
        if subtitle:
            self.subtitle_label = ctk.CTkLabel(
                title_frame,
                text=subtitle,
                font=ctk.CTkFont(size=FONT_SIZES["body"]),
                text_color=COLORS["text_secondary"]
            )
            self.subtitle_label.pack(anchor="w", pady=(5, 0))
        
        # Refresh button (optional)
        self.refresh_callback = None
        self.show_refresh = show_refresh
        self.title = title
        self.subtitle = subtitle
        
    def setup_ui(self):
        """Setup header UI"""
        # Left side - titles
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.pack(side="left", fill="y", padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            left_frame,
            text=self.title,
            font=ctk.CTkFont(size=FONT_SIZES["title"], weight="bold"),
            text_color=COLORS["text"]
        )
        title_label.pack(anchor="w")
        
        # Subtitle
        if self.subtitle:
            subtitle_label = ctk.CTkLabel(
                left_frame,
                text=self.subtitle,
                font=ctk.CTkFont(size=FONT_SIZES["body"]),
                text_color=COLORS["text_secondary"]
            )
            subtitle_label.pack(anchor="w", pady=(5, 0))
        
        # Right side - actions
        if self.show_refresh:
            right_frame = ctk.CTkFrame(self, fg_color="transparent")
            right_frame.pack(side="right", fill="y", padx=20, pady=20)
            
            self.refresh_button = ctk.CTkButton(
                right_frame,
                text="🔄 Refresh",
                command=self.refresh_clicked,
                width=120,
                height=35,
                fg_color=COLORS["primary"],
                hover_color="#0099cc"
            )
            self.refresh_button.pack(anchor="e")
    
    def refresh_clicked(self):
        """Handle refresh button click"""
        if self.refresh_callback:
            self.refresh_button.configure(state="disabled", text="Refreshing...")
            self.refresh_callback()
            self.after(1000, self.reset_refresh_button)
    
    def reset_refresh_button(self):
        """Reset refresh button state"""
        self.refresh_button.configure(state="normal", text="🔄 Refresh")
    
    def set_refresh_callback(self, callback):
        """Add refresh button with callback"""
        self.refresh_callback = callback
        
        refresh_btn = ctk.CTkButton(
            self.header_frame,
            text="🔄 Refresh",
            command=callback,
            width=100,
            height=35,
            fg_color=COLORS["info"],
            hover_color=COLORS["info_hover"]
        )
        refresh_btn.pack(side="right", pady=20)