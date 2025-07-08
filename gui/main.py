# Main GUI Application for CS:GO Arbitrage Bot

import customtkinter as ctk
import sys
import os

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)

# GUI imports
from gui.components.sidebar import Sidebar
from gui.config.constants import WINDOW_WIDTH, WINDOW_HEIGHT, COLORS
from gui.config.themes import ThemeManager

# Controllers
from gui.controllers.scraper_controller import ScraperController
from gui.controllers.profitability_controller import ProfitabilityController
from gui.controllers.cache_controller import CacheController
from gui.controllers.config_controller import ConfigController
from gui.controllers.analytics_controller import AnalyticsController

# Pages (will be imported dynamically)
import importlib

class CSGOArbitrageGUI:
    def __init__(self):
        # Initialize CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title("CS:GO Arbitrage Bot - Professional Edition v2.0")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(800, 600)
        
        # Initialize theme manager
        self.theme_manager = ThemeManager()
        
        # Initialize controllers
        print("Initializing controllers...")
        self.scraper_controller = ScraperController()
        self.profitability_controller = ProfitabilityController()
        self.cache_controller = CacheController()
        self.config_controller = ConfigController()
        self.analytics_controller = AnalyticsController()
        
        # Page management
        self.pages = {}
        self.current_page = None
        
        # Setup UI
        self.setup_ui()
        
        # Show initial page
        self.show_page("dashboard")
        
        print("GUI initialization complete!")
    
    def setup_ui(self):
        """Setup the main UI"""
        # Configure root window
        self.root.configure(fg_color=COLORS["background"])
        
        # Main container
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill="both", expand=True)
        
        # Sidebar
        self.sidebar = Sidebar(main_container, self.show_page)
        self.sidebar.pack(side="left", fill="y")
        
        # Content area
        self.content_area = ctk.CTkFrame(
            main_container, 
            corner_radius=0, 
            fg_color=COLORS["background"]
        )
        self.content_area.pack(side="right", fill="both", expand=True)
        
        # Initialize pages
        self.initialize_pages()
    
    def initialize_pages(self):
        """Initialize all page components"""
        page_modules = {
            "dashboard": "gui.pages.dashboard",
            "scrapers": "gui.pages.scrapers", 
            "profitability": "gui.pages.profitability",
            "images": "gui.pages.images",
            "config": "gui.pages.config",
            "debug": "gui.pages.debug",
            "analytics": "gui.pages.analytics"
        }
        
        for page_name, module_path in page_modules.items():
            try:
                # Import page module
                module = importlib.import_module(module_path)
                
                # Get page class (assumes class name is PageName + "Page")
                class_name = page_name.capitalize() + "Page"
                page_class = getattr(module, class_name)
                
                # Create page instance
                page_instance = page_class(self.content_area, self)
                self.pages[page_name] = page_instance
                
                print(f"Initialized page: {page_name}")
                
            except Exception as e:
                print(f"Error initializing page {page_name}: {e}")
                # Create a placeholder page
                self.pages[page_name] = self.create_placeholder_page(page_name)
    
    def create_placeholder_page(self, page_name):
        """Create a placeholder page for missing implementations"""
        placeholder = ctk.CTkFrame(self.content_area, fg_color="transparent")
        
        # Title
        title_label = ctk.CTkLabel(
            placeholder,
            text=f"{page_name.capitalize()} Page",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS["text"]
        )
        title_label.pack(pady=50)
        
        # Status message
        status_label = ctk.CTkLabel(
            placeholder,
            text=f"This page is being implemented...",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"]
        )
        status_label.pack(pady=10)
        
        # Add refresh method for compatibility
        def refresh():
            print(f"Refreshing placeholder page: {page_name}")
        
        placeholder.refresh = refresh
        
        return placeholder
    
    def show_page(self, page_name):
        """Switch to a different page"""
        try:
            # Hide current page
            if self.current_page and self.current_page in self.pages:
                self.pages[self.current_page].pack_forget()
            
            # Show new page
            if page_name in self.pages:
                self.current_page = page_name
                self.pages[page_name].pack(fill="both", expand=True)
                
                # Refresh page data
                if hasattr(self.pages[page_name], 'refresh'):
                    self.pages[page_name].refresh()
                
                print(f"Switched to page: {page_name}")
            else:
                print(f"Page not found: {page_name}")
                
        except Exception as e:
            print(f"Error switching to page {page_name}: {e}")
    
    def get_controller(self, controller_name):
        """Get a controller by name"""
        controllers = {
            "scraper": self.scraper_controller,
            "profitability": self.profitability_controller,
            "cache": self.cache_controller,
            "config": self.config_controller,
            "analytics": self.analytics_controller
        }
        return controllers.get(controller_name)
    
    def run(self):
        """Start the GUI application"""
        try:
            print("Starting CS:GO Arbitrage Bot GUI...")
            
            # Center window on screen
            self.center_window()
            
            # Start main loop
            self.root.mainloop()
            
        except KeyboardInterrupt:
            print("Application interrupted by user")
        except Exception as e:
            print(f"Error running application: {e}")
        finally:
            print("GUI application closed")
    
    def center_window(self):
        """Center the window on the screen"""
        try:
            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Calculate position
            x = (screen_width - WINDOW_WIDTH) // 4
            y = (screen_height - WINDOW_HEIGHT) // 4
            
            # Set window position
            self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")
            
        except Exception as e:
            print(f"Error centering window: {e}")

def main():
    """Main function to run the GUI"""
    try:
        # Create and run GUI
        app = CSGOArbitrageGUI()
        app.run()
        
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()