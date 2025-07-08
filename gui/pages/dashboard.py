# Dashboard Page

import customtkinter as ctk
from datetime import datetime
import threading

from gui.config.constants import COLORS, FONT_SIZES, REFRESH_INTERVALS
from gui.components.header import PageHeader
from gui.components.cards import StatCard, ActionCard
from gui.components.charts import SimpleChart, MetricsGrid
from gui.utils.threading_utils import run_in_background
from gui.utils.data_formatter import DataFormatter

class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, app_controller):
        super().__init__(parent, fg_color="transparent")
        self.app = app_controller
        self.auto_refresh = True
        self.refresh_interval = REFRESH_INTERVALS["dashboard"]
        
        # UI components
        self.stat_cards = {}
        self.activity_text = None
        
        self.setup_ui()
        self.start_auto_refresh()
    
    def setup_ui(self):
        """Setup dashboard UI"""
        # Header
        self.header = PageHeader(
            self, 
            "Dashboard Overview", 
            "Real-time system monitoring and quick actions"
        )
        self.header.pack(fill="x", padx=20, pady=(20, 10))
        self.header.set_refresh_callback(self.refresh_all_data)
        
        # Main content container
        content_container = ctk.CTkFrame(self, fg_color="transparent")
        content_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Top section - Statistics cards
        stats_section = ctk.CTkFrame(content_container, fg_color="transparent")
        stats_section.pack(fill="x", pady=(0, 20))
        
        self.create_stat_cards(stats_section)
        
        # Middle section - Charts and metrics
        middle_section = ctk.CTkFrame(content_container, fg_color="transparent")
        middle_section.pack(fill="both", expand=True, pady=(0, 20))
        
        # Left side - Chart
        left_frame = ctk.CTkFrame(middle_section, fg_color=COLORS["card"], corner_radius=10)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.create_chart_section(left_frame)
        
        # Right side - Quick actions and activity
        right_frame = ctk.CTkFrame(middle_section, fg_color="transparent", width=300)
        right_frame.pack(side="right", fill="y", padx=(10, 0))
        right_frame.pack_propagate(False)
        
        self.create_actions_section(right_frame)
    
    def create_stat_cards(self, parent):
        """Create statistics cards"""
        # Container for cards
        cards_frame = ctk.CTkFrame(parent, fg_color="transparent")
        cards_frame.pack(fill="x")
        
        # Configure grid
        for i in range(4):
            cards_frame.grid_columnconfigure(i, weight=1)
        
        # Get initial data
        scraper_status = self.app.scraper_controller.get_all_status()
        active_scrapers = sum(1 for s in scraper_status.values() if s["status"] == "running")
        total_scrapers = len(scraper_status)
        total_items = sum(s.get("items_fetched", 0) for s in scraper_status.values())
        opportunities = len(self.app.profitability_controller.get_opportunities())
        
        # Create cards - ACTUALIZADO CON ICONOS DEL MOCK
        cards_data = [
            ("Active Scrapers", f"{active_scrapers}/{total_scrapers}", COLORS["success"], "📡"),
            ("Total Items", DataFormatter.format_number(total_items, 0), COLORS["info"], "📦"),
            ("Profit Opportunities", str(opportunities), COLORS["warning"], "💎"),
            ("Avg Response Time", "0.38s", "#ff00ff", "⚡"),  # Nuevo del mock
        ]
        
        for i, (title, value, color, icon) in enumerate(cards_data):
            card = StatCard(cards_frame, title, value, color, icon)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="ew")
            
            # Store reference for updates
            self.stat_cards[title] = card
    
    def create_chart_section(self, parent):
        """Create chart section"""
        # Chart title
        chart_title = ctk.CTkLabel(
            parent,
            text="System Performance",
            font=ctk.CTkFont(size=FONT_SIZES["subtitle"], weight="bold"),
            text_color=COLORS["text"]
        )
        chart_title.pack(pady=(20, 10))
        
        # Chart
        self.chart = SimpleChart(parent, "Performance Trend", "line")
        self.chart.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    
    def create_actions_section(self, parent):
        """Create quick actions and activity section"""
        # Quick Actions
        actions_frame = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=10)
        actions_frame.pack(fill="x", pady=(0, 10))
        
        actions_title = ctk.CTkLabel(
            actions_frame,
            text="Quick Actions",
            font=ctk.CTkFont(size=FONT_SIZES["subtitle"], weight="bold"),
            text_color=COLORS["text"]
        )
        actions_title.pack(pady=(20, 10))
        
        # Action buttons
        self.create_action_buttons(actions_frame)
        
        # Activity Feed
        activity_frame = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=10)
        activity_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        activity_title = ctk.CTkLabel(
            activity_frame,
            text="Recent Activity",
            font=ctk.CTkFont(size=FONT_SIZES["subtitle"], weight="bold"),
            text_color=COLORS["text"]
        )
        activity_title.pack(pady=(20, 10))
        
        # Activity text area
        self.activity_text = ctk.CTkTextbox(
            activity_frame,
            height=200,
            fg_color=COLORS["background"],
            text_color=COLORS["text"]
        )
        self.activity_text.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Initial activity
        self.update_activity_feed()
    
    def create_action_buttons(self, parent):
        """Create action buttons"""
        buttons_data = [
            ("🔄 Refresh All", self.refresh_all_data, COLORS["info"]),      # Añadido emoji
            ("⏸️ Pause All", self.pause_all_scrapers, COLORS["warning"]),   # Nuevo botón
            ("📊 Export Report", self.export_report, COLORS["primary"])      # Nuevo botón
        ]
        
        # Crear frame horizontal para los botones
        buttons_frame = ctk.CTkFrame(parent, fg_color="transparent")
        buttons_frame.pack(pady=(10, 20))
        
        for text, command, color in buttons_data:
            button = ctk.CTkButton(
                buttons_frame,
                text=text,
                command=command,
                fg_color=color,
                hover_color=self.get_hover_color(color),
                width=120,
                height=35
            )
            button.pack(side="left", padx=5)
        
        for text, command, color in buttons_data:
            button = ctk.CTkButton(
                parent,
                text=text,
                command=command,
                fg_color=color,
                hover_color=self.get_hover_color(color),
                height=35
            )
            button.pack(fill="x", padx=20, pady=5)
    
    def get_hover_color(self, base_color):
        """Get hover color for button"""
        color_map = {
            COLORS["primary"]: "#0099cc",
            COLORS["success"]: "#00cc00", 
            COLORS["warning"]: "#cc8800",
            COLORS["info"]: "#0099ff"
        }
        return color_map.get(base_color, "#666666")
    
    def run_all_scrapers(self):
        """Run all enabled scrapers"""
        def run_task():
            count = self.app.scraper_controller.run_all_scrapers()
            return f"Started {count} scrapers"
        
        def on_success(result):
            self.add_activity(f"✅ {result}")
            self.refresh_stats()
        
        def on_error(error):
            self.add_activity(f"❌ Error running scrapers: {error}")
        
        run_in_background(self, run_task, on_success, on_error)
        self.add_activity("🕷️ Starting all scrapers...")
    
    def calculate_profits(self):
        """Calculate profitability opportunities"""
        def calc_task():
            self.app.profitability_controller.calculate_opportunities(1.0)
            return "Profitability calculation started"
        
        def on_success(result):
            self.add_activity(f"💰 {result}")
            self.refresh_stats()
        
        def on_error(error):
            self.add_activity(f"❌ Error calculating profits: {error}")
        
        run_in_background(self, calc_task, on_success, on_error)
        self.add_activity("💰 Calculating profit opportunities...")
    
    def clean_cache(self):
        """Clean image cache"""
        def clean_task():
            self.app.cache_controller.cleanup_cache()
            return "Cache cleanup started"
        
        def on_success(result):
            self.add_activity(f"🧹 {result}")
            self.refresh_stats()
        
        def on_error(error):
            self.add_activity(f"❌ Error cleaning cache: {error}")
        
        run_in_background(self, clean_task, on_success, on_error)
        self.add_activity("🧹 Cleaning image cache...")
    
    def refresh_all_data(self):
        """Refresh all dashboard data"""
        self.refresh_stats()
        self.add_activity("🔄 Dashboard refreshed")
    
    def refresh_stats(self):
        """Refresh statistics cards with REAL data"""
        try:
            # Get REAL scraper data
            scraper_status = self.app.scraper_controller.get_all_status()
            active_scrapers = sum(1 for s in scraper_status.values() if s["status"] == "running")
            total_scrapers = len(scraper_status)
            
            # Get REAL total items from JSON files
            total_items = self.app.scraper_controller.get_total_items_all_scrapers()
            
            # Get REAL opportunities
            opportunities = len(self.app.profitability_controller.get_opportunities())
            
            # Calculate average response time (you can implement this based on your logs)
            avg_response = "0.38s"  # Por ahora hardcoded, pero puedes calcularlo
            
            # Update cards with REAL data
            if "Active Scrapers" in self.stat_cards:
                self.stat_cards["Active Scrapers"].update_value(f"{active_scrapers}/{total_scrapers}")
            
            if "Total Items" in self.stat_cards:
                self.stat_cards["Total Items"].update_value(f"{total_items:,}")
            
            if "Profit Opportunities" in self.stat_cards:
                self.stat_cards["Profit Opportunities"].update_value(str(opportunities))
                
            if "Avg Response Time" in self.stat_cards:
                self.stat_cards["Avg Response Time"].update_value(avg_response)
            
        except Exception as e:
            print(f"Error refreshing stats: {e}")
            self.add_activity(f"❌ Error refreshing stats: {e}")
    
    def update_activity_feed(self):
        """Update activity feed with recent events"""
        try:
            if not self.activity_text:
                return
            
            # Clear existing content
            self.activity_text.delete("1.0", "end")
            
            # Actividades del mock
            activities = [
                ("✅", "BitSkins scraper completed", "2 mins ago"),
                ("💰", "New profit opportunity: AK-47 Redline", "5 mins ago"),
                ("🔄", "Waxpeer data updated", "8 mins ago"),
                ("⚠️", "Empire API rate limit warning", "12 mins ago"),
                ("✅", "Cache cleanup completed", "15 mins ago"),
            ]
            
            for icon, text, time_ago in activities:
                line = f"{icon} {text} - {time_ago}\n"
                self.activity_text.insert("end", line)
            
            # Scroll to bottom
            self.activity_text.see("end")
            
        except Exception as e:
            print(f"Error updating activity feed: {e}")
    
    def add_activity(self, message):
        """Add a new activity to the feed"""
        try:
            if self.activity_text:
                timestamp = datetime.now().strftime('%H:%M:%S')
                activity_line = f"[{timestamp}] {message}\n"
                self.activity_text.insert("end", activity_line)
                self.activity_text.see("end")
        except Exception as e:
            print(f"Error adding activity: {e}")
    
    def refresh(self):
        """Refresh page data"""
        self.refresh_stats()
    
    def start_auto_refresh(self):
        """Start auto-refresh timer"""
        if self.auto_refresh:
            self.refresh_stats()
            self.after(self.refresh_interval, self.start_auto_refresh)
    def pause_all_scrapers(self):
        """Pause all running scrapers"""
        def pause_task():
            # Implementación simple por ahora
            for scraper_name in self.app.scraper_controller.scraper_status:
                self.app.scraper_controller.stop_scraper(scraper_name)
            return "All scrapers paused"
        
        def on_success(result):
            self.add_activity(f"⏸️ {result}")
            self.refresh_stats()
        
        def on_error(error):
            self.add_activity(f"❌ Error pausing scrapers: {error}")
        
        run_in_background(self, pause_task, on_success, on_error)
        self.add_activity("⏸️ Pausing all scrapers...")

    def export_report(self):
        """Export profitability report"""
        self.add_activity("📊 Export feature coming soon...")