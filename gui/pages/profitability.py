# Profitability Page - Página funcional con datos reales

import customtkinter as ctk
import webbrowser
from datetime import datetime
from gui.config.constants import COLORS, FONT_SIZES, DIMENSIONS, ICONS, REFRESH_INTERVALS
from gui.components.header import PageHeader
from gui.utils.threading_utils import run_in_background

class ProfitabilityPage(ctk.CTkFrame):
    def __init__(self, parent, app_controller):
        super().__init__(parent, fg_color="transparent")
        self.app = app_controller
        self.opportunities = []
        self.min_profit = 1.0
        self.auto_refresh = True
        self.refresh_interval = REFRESH_INTERVALS["profitability"]
        
        # UI components
        self.stat_cards = {}
        self.opportunities_frame = None
        self.filter_entry = None
        
        self.setup_ui()
        self.start_auto_refresh()
    
    def setup_ui(self):
        """Setup profitability page UI"""
        # Header with filters
        header_container = ctk.CTkFrame(self, fg_color="transparent")
        header_container.pack(fill="x", padx=20, pady=(20, 10))
        
        # Header
        self.header = PageHeader(
            header_container,
            "Profitability Analysis",
            "Real-time arbitrage opportunities across platforms"
        )
        self.header.pack(fill="x")
        
        # Filters frame dentro del header
        filters_frame = ctk.CTkFrame(self.header.header_frame, fg_color="transparent")
        filters_frame.pack(side="right", padx=20)
        
        # Min profit filter
        ctk.CTkLabel(
            filters_frame, 
            text="Min Profit %:", 
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=5)
        
        self.filter_entry = ctk.CTkEntry(
            filters_frame, 
            width=60, 
            placeholder_text="1.0"
        )
        self.filter_entry.pack(side="left", padx=5)
        self.filter_entry.insert(0, str(self.min_profit))
        
        ctk.CTkButton(
            filters_frame, 
            text="🔍 Filter", 
            width=80, 
            height=35,
            command=self.apply_filter
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            filters_frame, 
            text="🔄 Refresh", 
            width=80, 
            height=35, 
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            command=self.refresh_opportunities
        ).pack(side="left", padx=5)
        
        # Summary cards
        summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        summary_frame.pack(fill="x", padx=20, pady=10)
        
        self.create_summary_cards(summary_frame)
        
        # Table container
        table_container = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=15)
        table_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Table title
        ctk.CTkLabel(
            table_container,
            text="Live Arbitrage Opportunities",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text"]
        ).pack(pady=15)
        
        # Table header
        header_frame = ctk.CTkFrame(table_container, fg_color="#1a1a1a")
        header_frame.pack(fill="x", padx=20)
        
        # Header columns
        headers = [
            ("Item", 3),
            ("Buy From", 1),
            ("Buy Price", 1),
            ("Sell To", 1),
            ("Sell Price", 1),
            ("Profit", 1),
            ("Margin", 1),
            ("Action", 1)
        ]
        
        for col, (header, weight) in enumerate(headers):
            label = ctk.CTkLabel(
                header_frame,
                text=header,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["info"]
            )
            label.grid(row=0, column=col, padx=15, pady=10, sticky="w")
            header_frame.grid_columnconfigure(col, weight=weight)
        
        # Scrollable frame for opportunities
        self.opportunities_frame = ctk.CTkScrollableFrame(
            table_container,
            fg_color=COLORS["card"],
            height=400
        )
        self.opportunities_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Load initial data
        self.refresh_opportunities()
    
    def create_summary_cards(self, parent):
        """Create summary statistics cards"""
        # Configure grid
        for i in range(4):
            parent.grid_columnconfigure(i, weight=1)
        
        # Get statistics
        stats = self.app.profitability_controller.get_statistics()
        
        # Create cards
        cards_data = [
            ("Total Opportunities", "0", COLORS["success"]),
            ("Avg Profit Margin", "0%", COLORS["info"]),
            ("Best Opportunity", "$0", COLORS["warning"]),
            ("Est. Daily Profit", "$0", "#ff00ff")
        ]
        
        for i, (label, value, color) in enumerate(cards_data):
            card = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=15)
            card.grid(row=0, column=i, padx=10, sticky="ew")
            
            value_label = ctk.CTkLabel(
                card,
                text=value,
                font=ctk.CTkFont(size=24, weight="bold"),
                text_color=color
            )
            value_label.pack(pady=(15, 5))
            
            ctk.CTkLabel(
                card,
                text=label,
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_secondary"]
            ).pack(pady=(0, 15))
            
            # Store reference for updates
            self.stat_cards[label] = value_label
        
        # Update with real data
        self.update_summary_cards()
    
    def update_summary_cards(self):
        """Update summary cards with real data"""
        try:
            stats = self.app.profitability_controller.get_statistics()
            opportunities = self.app.profitability_controller.get_opportunities()
            
            # Total opportunities
            if "Total Opportunities" in self.stat_cards:
                self.stat_cards["Total Opportunities"].configure(
                    text=str(len(opportunities))
                )
            
            # Average profit margin
            if "Avg Profit Margin" in self.stat_cards and opportunities:
                avg_profit = sum(opp.get("profit_percentage_display", 0) for opp in opportunities) / len(opportunities)
                self.stat_cards["Avg Profit Margin"].configure(
                    text=f"{avg_profit:.2f}%"
                )
            
            # Best opportunity
            if "Best Opportunity" in self.stat_cards and opportunities:
                best_profit = max(opp.get("profit_absolute", 0) for opp in opportunities)
                self.stat_cards["Best Opportunity"].configure(
                    text=f"${best_profit:.2f}"
                )
            
            # Estimated daily profit (assuming 10 trades per opportunity)
            if "Est. Daily Profit" in self.stat_cards and opportunities:
                total_profit = sum(opp.get("profit_absolute", 0) for opp in opportunities) * 10
                self.stat_cards["Est. Daily Profit"].configure(
                    text=f"${total_profit:,.2f}"
                )
                
        except Exception as e:
            print(f"Error updating summary cards: {e}")
    
    def display_opportunities(self):
        """Display opportunities in the table"""
        # Clear existing content
        for widget in self.opportunities_frame.winfo_children():
            widget.destroy()
        
        # Get current opportunities
        self.opportunities = self.app.profitability_controller.get_opportunities()
        
        if not self.opportunities:
            # Show no data message
            ctk.CTkLabel(
                self.opportunities_frame,
                text="No opportunities found. Try refreshing or lowering the minimum profit threshold.",
                font=ctk.CTkFont(size=14),
                text_color=COLORS["text_secondary"]
            ).pack(pady=50)
            return
        
        # Display each opportunity
        for i, opp in enumerate(self.opportunities):
            self.create_opportunity_row(i, opp)
    
    def create_opportunity_row(self, index, opportunity):
        """Create a single opportunity row"""
        # Row frame
        row_bg = "#1a1a1a" if index % 2 == 0 else "#222222"
        row_frame = ctk.CTkFrame(self.opportunities_frame, fg_color=row_bg, height=50)
        row_frame.pack(fill="x", pady=1)
        row_frame.pack_propagate(False)
        
        # Configure grid
        for i in range(8):
            weight = 3 if i == 0 else 1
            row_frame.grid_columnconfigure(i, weight=weight)
        
        # Item name
        item_label = ctk.CTkLabel(
            row_frame,
            text=opportunity.get("name", "Unknown"),
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text"],
            anchor="w"
        )
        item_label.grid(row=0, column=0, padx=15, pady=15, sticky="w")
        
        # Buy platform
        buy_platform = opportunity.get("buy_platform", "").title()
        ctk.CTkLabel(
            row_frame,
            text=buy_platform,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text"]
        ).grid(row=0, column=1, padx=15, pady=15)
        
        # Buy price
        buy_price = opportunity.get("buy_price", 0)
        ctk.CTkLabel(
            row_frame,
            text=f"${buy_price:.2f}",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text"]
        ).grid(row=0, column=2, padx=15, pady=15)
        
        # Sell platform (Steam)
        ctk.CTkLabel(
            row_frame,
            text="Steam",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text"]
        ).grid(row=0, column=3, padx=15, pady=15)
        
        # Sell price (net after fees)
        net_price = opportunity.get("net_steam_price", 0)
        gross_price = opportunity.get("steam_price", 0)
        ctk.CTkLabel(
            row_frame,
            text=f"${net_price:.2f}",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text"],
            cursor="hand2"
        ).grid(row=0, column=4, padx=15, pady=15)
        
        # Profit
        profit = opportunity.get("profit_absolute", 0)
        profit_color = self.get_profit_color(opportunity.get("profit_percentage_display", 0))
        ctk.CTkLabel(
            row_frame,
            text=f"${profit:.2f}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=profit_color
        ).grid(row=0, column=5, padx=15, pady=15)
        
        # Margin
        margin = opportunity.get("profit_percentage_display", 0)
        ctk.CTkLabel(
            row_frame,
            text=f"{margin:.2f}%",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=profit_color
        ).grid(row=0, column=6, padx=15, pady=15)
        
        # Action buttons
        action_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        action_frame.grid(row=0, column=7, padx=15, pady=10)
        
        # Buy button
        buy_btn = ctk.CTkButton(
            action_frame,
            text="Buy",
            width=50,
            height=28,
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            command=lambda url=opportunity.get("buy_url"): self.open_url(url)
        )
        buy_btn.pack(side="left", padx=2)
        
        # Sell button  
        sell_btn = ctk.CTkButton(
            action_frame,
            text="Sell",
            width=50,
            height=28,
            fg_color=COLORS["info"],
            hover_color=COLORS["info_hover"],
            command=lambda url=opportunity.get("steam_url"): self.open_url(url)
        )
        sell_btn.pack(side="left", padx=2)
    
    def get_profit_color(self, profit_percentage):
        """Get color based on profit percentage"""
        if profit_percentage >= 4:
            return COLORS["profit_high"]
        elif profit_percentage >= 3:
            return COLORS["profit_medium"]
        elif profit_percentage >= 2:
            return COLORS["profit_low"]
        else:
            return COLORS["warning"]
    
    def open_url(self, url):
        """Open URL in browser"""
        if url:
            webbrowser.open(url)
    
    def apply_filter(self):
        """Apply minimum profit filter"""
        try:
            self.min_profit = float(self.filter_entry.get())
            self.refresh_opportunities()
        except ValueError:
            print("Invalid profit value")
    
    def refresh_opportunities(self):
        """Refresh opportunities from profitability engine"""
        def calculate():
            self.app.profitability_controller.calculate_opportunities(
                min_profit=self.min_profit,
                callback=self.on_calculation_complete
            )
        
        def on_start():
            # Update UI to show calculating
            for widget in self.opportunities_frame.winfo_children():
                widget.destroy()
            
            ctk.CTkLabel(
                self.opportunities_frame,
                text="Calculating opportunities...",
                font=ctk.CTkFont(size=14),
                text_color=COLORS["text_secondary"]
            ).pack(pady=50)
        
        # Start calculation
        on_start()
        run_in_background(self, calculate)
    
    def on_calculation_complete(self, status, data):
        """Handle calculation completion"""
        self.after(0, self._update_after_calculation, status, data)
    
    def _update_after_calculation(self, status, data):
        """Update UI after calculation"""
        if status == "success":
            self.display_opportunities()
            self.update_summary_cards()
        else:
            # Show error
            for widget in self.opportunities_frame.winfo_children():
                widget.destroy()
            
            ctk.CTkLabel(
                self.opportunities_frame,
                text=f"Error calculating opportunities: {data}",
                font=ctk.CTkFont(size=14),
                text_color=COLORS["error"]
            ).pack(pady=50)
    
    def refresh(self):
        """Refresh page data"""
        self.display_opportunities()
        self.update_summary_cards()
    
    def start_auto_refresh(self):
        """Start auto-refresh timer"""
        if self.auto_refresh:
            self.refresh()
            self.after(self.refresh_interval, self.start_auto_refresh)