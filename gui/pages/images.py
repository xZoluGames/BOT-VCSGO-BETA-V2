# Image Cache Page - Gestión del caché de imágenes

import customtkinter as ctk
import os
import threading
from datetime import datetime
from gui.config.constants import COLORS, FONT_SIZES, DIMENSIONS, ICONS
from gui.components.header import PageHeader
from gui.utils.threading_utils import run_in_background

class ImagesPage(ctk.CTkFrame):
    def __init__(self, parent, app_controller):
        super().__init__(parent, fg_color="transparent")
        self.app = app_controller
        self.cache_stats = {}
        self.image_list = []
        
        self.setup_ui()
        self.load_cache_stats()
    
    def setup_ui(self):
        """Setup image cache page UI"""
        # Header
        header_container = ctk.CTkFrame(self, fg_color="transparent")
        header_container.pack(fill="x", padx=20, pady=(20, 10))
        
        self.header = PageHeader(
            header_container,
            "Image Cache Management",
            "Monitor and manage cached skin images"
        )
        self.header.pack(fill="x")
        
        # Actions
        actions_frame = ctk.CTkFrame(self.header.header_frame, fg_color="transparent")
        actions_frame.pack(side="right", padx=20)
        
        ctk.CTkButton(
            actions_frame, 
            text="🔄 Scan Cache", 
            width=100, 
            height=35,
            command=self.scan_cache
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            actions_frame, 
            text="🧹 Clean Up", 
            width=100, 
            height=35, 
            fg_color=COLORS["warning"],
            hover_color=COLORS["warning_hover"],
            command=self.cleanup_cache
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            actions_frame, 
            text="📥 Import", 
            width=100, 
            height=35,
            command=self.import_images
        ).pack(side="left", padx=5)
        
        # Stats cards
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        self.create_stats_cards(stats_frame)
        
        # Content area
        content_frame = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=15)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Tabs
        self.create_tabs(content_frame)
    
    def create_stats_cards(self, parent):
        """Create cache statistics cards"""
        for i in range(4):
            parent.grid_columnconfigure(i, weight=1)
        
        # Stats data
        stats_data = [
            ("Total Images", "0", "🖼️"),
            ("Cache Size", "0 MB", "💾"),
            ("Avg Image Size", "0 KB", "📊"),
            ("Last Cleanup", "Never", "🧹")
        ]
        
        self.stat_labels = {}
        
        for i, (label, value, icon) in enumerate(stats_data):
            card = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=15)
            card.grid(row=0, column=i, padx=10, sticky="ew")
            
            ctk.CTkLabel(card, text=icon, font=("Arial", 24)).pack(pady=(15, 5))
            
            value_label = ctk.CTkLabel(
                card,
                text=value,
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color=COLORS["text"]
            )
            value_label.pack()
            
            ctk.CTkLabel(
                card,
                text=label,
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_secondary"]
            ).pack(pady=(5, 15))
            
            self.stat_labels[label] = value_label
    
    def create_tabs(self, parent):
        """Create tabbed interface"""
        # Tab buttons
        tab_frame = ctk.CTkFrame(parent, fg_color="transparent")
        tab_frame.pack(fill="x", padx=20, pady=(15, 10))
        
        self.tabs = ["Recent Images", "Popular Items", "Missing Images", "Duplicates"]
        self.current_tab = self.tabs[0]
        self.tab_buttons = {}
        
        for i, tab in enumerate(self.tabs):
            btn = ctk.CTkButton(
                tab_frame,
                text=tab,
                width=120,
                height=30,
                fg_color=COLORS["primary"] if i == 0 else "#444444",
                command=lambda t=tab: self.switch_tab(t)
            )
            btn.pack(side="left", padx=5)
            self.tab_buttons[tab] = btn
        
        # Content area
        self.tab_content = ctk.CTkScrollableFrame(
            parent,
            fg_color=COLORS["card"]
        )
        self.tab_content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Load initial content
        self.load_tab_content()
    
    def switch_tab(self, tab_name):
        """Switch between tabs"""
        # Update button colors
        for tab, btn in self.tab_buttons.items():
            if tab == tab_name:
                btn.configure(fg_color=COLORS["primary"])
            else:
                btn.configure(fg_color="#444444")
        
        self.current_tab = tab_name
        self.load_tab_content()
    
    def load_tab_content(self):
        """Load content for current tab"""
        # Clear existing content
        for widget in self.tab_content.winfo_children():
            widget.destroy()
        
        if self.current_tab == "Recent Images":
            self.show_recent_images()
        elif self.current_tab == "Popular Items":
            self.show_popular_items()
        elif self.current_tab == "Missing Images":
            self.show_missing_images()
        elif self.current_tab == "Duplicates":
            self.show_duplicates()
    
    def show_recent_images(self):
        """Show recently cached images"""
        # Get cache directory
        cache_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "cache", "images"
        )
        
        if not os.path.exists(cache_dir):
            ctk.CTkLabel(
                self.tab_content,
                text="Cache directory not found",
                font=ctk.CTkFont(size=14),
                text_color=COLORS["text_secondary"]
            ).pack(pady=50)
            return
        
        # Get list of images (limit to 20 for performance)
        try:
            images = sorted(
                [f for f in os.listdir(cache_dir) if f.endswith(('.jpg', '.png'))],
                key=lambda x: os.path.getmtime(os.path.join(cache_dir, x)),
                reverse=True
            )[:20]
            
            if not images:
                ctk.CTkLabel(
                    self.tab_content,
                    text="No images found in cache",
                    font=ctk.CTkFont(size=14),
                    text_color=COLORS["text_secondary"]
                ).pack(pady=50)
                return
            
            # Create grid of image placeholders
            grid_frame = ctk.CTkFrame(self.tab_content, fg_color="transparent")
            grid_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            for i in range(4):
                grid_frame.grid_columnconfigure(i, weight=1)
            
            for idx, image_file in enumerate(images):
                row = idx // 4
                col = idx % 4
                
                # Image card
                img_card = ctk.CTkFrame(grid_frame, fg_color="#1a1a1a", corner_radius=10)
                img_card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
                
                # Placeholder for image
                img_placeholder = ctk.CTkFrame(
                    img_card, 
                    width=150, 
                    height=150, 
                    fg_color="#333333"
                )
                img_placeholder.pack(padx=10, pady=10)
                img_placeholder.pack_propagate(False)
                
                ctk.CTkLabel(
                    img_placeholder, 
                    text="🔫", 
                    font=("Arial", 48)
                ).pack(expand=True)
                
                # Image info
                file_size = os.path.getsize(os.path.join(cache_dir, image_file)) / 1024
                ctk.CTkLabel(
                    img_card,
                    text=image_file[:20] + "..." if len(image_file) > 20 else image_file,
                    font=ctk.CTkFont(size=10),
                    text_color=COLORS["text"]
                ).pack()
                
                ctk.CTkLabel(
                    img_card,
                    text=f"Size: {file_size:.1f} KB",
                    font=ctk.CTkFont(size=9),
                    text_color=COLORS["text_secondary"]
                ).pack(pady=(0, 10))
                
        except Exception as e:
            print(f"Error loading images: {e}")
    
    def show_popular_items(self):
        """Show popular cached items"""
        ctk.CTkLabel(
            self.tab_content,
            text="Popular items analysis coming soon...",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"]
        ).pack(pady=50)
    
    def show_missing_images(self):
        """Show items missing images"""
        ctk.CTkLabel(
            self.tab_content,
            text="Missing images detection coming soon...",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"]
        ).pack(pady=50)
    
    def show_duplicates(self):
        """Show duplicate images"""
        ctk.CTkLabel(
            self.tab_content,
            text="Duplicate detection coming soon...",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"]
        ).pack(pady=50)
    
    def load_cache_stats(self):
        """Load cache statistics"""
        def load_stats():
            return self.app.cache_controller.get_cache_stats()
        
        def on_success(stats):
            self.cache_stats = stats
            self.update_stats_display()
        
        run_in_background(self, load_stats, on_success)
    
    def update_stats_display(self):
        """Update statistics display"""
        if "Total Images" in self.stat_labels:
            self.stat_labels["Total Images"].configure(
                text=f"{self.cache_stats.get('total_images', 0):,}"
            )
        
        if "Cache Size" in self.stat_labels:
            size_mb = self.cache_stats.get('cache_size_mb', 0)
            if size_mb > 1000:
                size_text = f"{size_mb/1024:.1f} GB"
            else:
                size_text = f"{size_mb:.1f} MB"
            self.stat_labels["Cache Size"].configure(text=size_text)
        
        if "Avg Image Size" in self.stat_labels:
            total_images = self.cache_stats.get('total_images', 1)
            size_mb = self.cache_stats.get('cache_size_mb', 0)
            avg_kb = (size_mb * 1024) / total_images if total_images > 0 else 0
            self.stat_labels["Avg Image Size"].configure(text=f"{avg_kb:.1f} KB")
        
        if "Last Cleanup" in self.stat_labels:
            self.stat_labels["Last Cleanup"].configure(
                text=self.cache_stats.get('last_cleanup', 'Never')
            )
    
    def scan_cache(self):
        """Scan cache directory"""
        def scan():
            self.app.cache_controller.scan_cache()
            return self.app.cache_controller.get_cache_stats()
        
        def on_success(stats):
            self.cache_stats = stats
            self.update_stats_display()
            self.load_tab_content()
        
        run_in_background(self, scan, on_success)
    
    def cleanup_cache(self):
        """Clean up cache"""
        # Aquí podrías agregar un diálogo de confirmación
        def cleanup():
            self.app.cache_controller.cleanup_cache()
            return self.app.cache_controller.get_cache_stats()
        
        def on_success(stats):
            self.cache_stats = stats
            self.update_stats_display()
            self.load_tab_content()
        
        run_in_background(self, cleanup, on_success)
    
    def import_images(self):
        """Import images to cache"""
        print("Import functionality coming soon...")
    
    def refresh(self):
        """Refresh page data"""
        self.load_cache_stats()
        self.load_tab_content()