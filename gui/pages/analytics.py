# Analytics Page - Performance metrics and reports

import customtkinter as ctk
import json
import os
from datetime import datetime, timedelta
from gui.config.constants import COLORS, FONT_SIZES, DIMENSIONS
from gui.components.header import PageHeader
from gui.components.charts import SimpleChart
import random  # Para datos de ejemplo

class AnalyticsPage(ctk.CTkFrame):
    def __init__(self, parent, app_controller):
        super().__init__(parent, fg_color="transparent")
        self.app = app_controller
        self.current_period = "Last 24 Hours"
        self.analytics_data = {}
        
        self.setup_ui()
        self.load_analytics_data()
    
    def setup_ui(self):
        """Setup analytics page UI"""
        # Header
        header_container = ctk.CTkFrame(self, fg_color="transparent")
        header_container.pack(fill="x", padx=20, pady=(20, 10))
        
        self.header = PageHeader(
            header_container,
            "Analytics & Reports",
            "System performance metrics and historical data"
        )
        self.header.pack(fill="x")
        
        # Date range selector
        date_frame = ctk.CTkFrame(self.header.header_frame, fg_color="transparent")
        date_frame.pack(side="right", padx=20)
        
        ctk.CTkLabel(
            date_frame,
            text="Period:",
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=5)
        
        self.period_combo = ctk.CTkComboBox(
            date_frame,
            values=["Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"],
            width=150,
            command=self.change_period
        )
        self.period_combo.pack(side="left", padx=5)
        self.period_combo.set(self.current_period)
        
        ctk.CTkButton(
            date_frame,
            text="📊 Generate Report",
            width=120,
            height=35,
            command=self.generate_report
        ).pack(side="left", padx=5)
        
        # Scrollable container
        self.scroll_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.scroll_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # KPI Cards
        self.create_kpi_section()
        
        # Charts section
        self.create_charts_section()
        
        # Performance metrics
        self.create_metrics_section()
    
    def create_kpi_section(self):
        """Create KPI cards section"""
        kpi_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=(0, 20))
        
        for i in range(4):
            kpi_frame.grid_columnconfigure(i, weight=1)
        
        # Calculate KPIs
        total_profit = self.calculate_total_profit()
        success_rate = self.calculate_success_rate()
        avg_response = self.calculate_avg_response_time()
        items_analyzed = self.calculate_items_analyzed()
        
        kpis = [
            ("Total Profit", f"${total_profit:,.2f}", "+12.4%", COLORS["success"]),
            ("Success Rate", f"{success_rate:.1f}%", "+2.1%", COLORS["info"]),
            ("Avg Response Time", f"{avg_response:.2f}s", "-8.3%", COLORS["success"]),
            ("Items Analyzed", f"{items_analyzed/1000:.1f}K", "+18.7%", COLORS["warning"])
        ]
        
        self.kpi_cards = {}
        
        for i, (label, value, change, color) in enumerate(kpis):
            card = ctk.CTkFrame(kpi_frame, fg_color=COLORS["card"], corner_radius=15)
            card.grid(row=0, column=i, padx=10, sticky="ew")
            
            # Value
            value_label = ctk.CTkLabel(
                card,
                text=value,
                font=ctk.CTkFont(size=28, weight="bold"),
                text_color=color
            )
            value_label.pack(pady=(15, 5))
            
            # Label
            ctk.CTkLabel(
                card,
                text=label,
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_secondary"]
            ).pack()
            
            # Change indicator
            change_color = COLORS["success"] if "+" in change else COLORS["error"]
            ctk.CTkLabel(
                card,
                text=change,
                font=ctk.CTkFont(size=11),
                text_color=change_color
            ).pack(pady=(5, 15))
            
            self.kpi_cards[label] = value_label
    
    def create_charts_section(self):
        """Create charts section"""
        charts_container = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        charts_container.pack(fill="x", pady=(0, 20))
        
        # Configure grid
        charts_container.grid_columnconfigure(0, weight=1)
        charts_container.grid_columnconfigure(1, weight=1)
        
        # Profit trend chart
        profit_chart_frame = ctk.CTkFrame(
            charts_container,
            fg_color=COLORS["card"],
            corner_radius=15
        )
        profit_chart_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(
            profit_chart_frame,
            text="Profit Trend",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # Mock chart
        self.create_mock_chart(profit_chart_frame, "area")
        
        # Platform performance
        platform_frame = ctk.CTkFrame(
            charts_container,
            fg_color=COLORS["card"],
            corner_radius=15
        )
        platform_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(
            platform_frame,
            text="Platform Performance",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # Platform bars
        self.create_platform_bars(platform_frame)
    
    def create_mock_chart(self, parent, chart_type="line"):
        """Create a mock chart"""
        chart_canvas = ctk.CTkCanvas(
            parent,
            width=400,
            height=250,
            bg=COLORS["card"],
            highlightthickness=0
        )
        chart_canvas.pack(padx=20, pady=10)
        
        # Generate mock data points
        points = []
        for i in range(10):
            x = 40 + i * 40
            y = 200 - random.randint(50, 150)
            points.extend([x, y])
        
        if chart_type == "area":
            # Create area chart
            area_points = [40, 200] + points + [400, 200, 40, 200]
            chart_canvas.create_polygon(
                area_points,
                fill="#00ff00",
                outline=COLORS["success"],
                width=2
            )
        else:
            # Create line chart
            if len(points) >= 4:
                chart_canvas.create_line(
                    points,
                    fill=COLORS["success"],
                    width=2,
                    smooth=True
                )
    
    def create_platform_bars(self, parent):
        """Create platform performance bars"""
        # Get platform data
        platforms_data = self.get_platform_performance()
        
        for platform, performance, color in platforms_data[:5]:  # Top 5 platforms
            perf_frame = ctk.CTkFrame(parent, fg_color="transparent")
            perf_frame.pack(fill="x", padx=20, pady=5)
            
            # Platform name
            ctk.CTkLabel(
                perf_frame,
                text=platform,
                font=ctk.CTkFont(size=12),
                width=80,
                anchor="w"
            ).pack(side="left")
            
            # Progress bar background
            bar_bg = ctk.CTkFrame(perf_frame, height=20, fg_color="#1a1a1a")
            bar_bg.pack(side="left", fill="x", expand=True, padx=10)
            
            # Progress bar fill
            bar_fill = ctk.CTkFrame(bar_bg, height=20, fg_color=color)
            bar_fill.place(relwidth=performance/100, relheight=1)
            
            # Percentage
            ctk.CTkLabel(
                perf_frame,
                text=f"{performance}%",
                font=ctk.CTkFont(size=12),
                width=40
            ).pack(side="right")
    
    def create_metrics_section(self):
        """Create success metrics section"""
        metrics_frame = ctk.CTkFrame(
            self.scroll_container,
            fg_color=COLORS["card"],
            corner_radius=15
        )
        metrics_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            metrics_frame,
            text="Success Metrics",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=10, sticky="w")
        
        # Get metrics
        metrics = self.calculate_metrics()
        
        for i, (label, value) in enumerate(metrics):
            ctk.CTkLabel(
                metrics_frame,
                text=f"{label}:",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_secondary"]
            ).grid(row=i+1, column=0, padx=20, pady=5, sticky="w")
            
            ctk.CTkLabel(
                metrics_frame,
                text=value,
                font=ctk.CTkFont(size=12, weight="bold")
            ).grid(row=i+1, column=1, padx=20, pady=5, sticky="w")
    
    def calculate_total_profit(self):
        """Calculate total profit for period"""
        # Get profitability data
        opportunities = self.app.profitability_controller.get_opportunities()
        
        # Simple calculation - in real implementation would filter by date
        total = sum(opp.get("profit_absolute", 0) for opp in opportunities) * 10
        return total
    
    def calculate_success_rate(self):
        """Calculate average success rate"""
        scraper_status = self.app.scraper_controller.get_all_status()
        rates = [s.get("success_rate", 0) for s in scraper_status.values()]
        return sum(rates) / len(rates) if rates else 0
    
    def calculate_avg_response_time(self):
        """Calculate average response time"""
        # Mock data - in real implementation would get from logs
        return 0.42
    
    def calculate_items_analyzed(self):
        """Calculate total items analyzed"""
        # Get from analytics controller
        return self.app.analytics_controller.get_total_items_analyzed()
    
    def get_platform_performance(self):
        """Get platform performance data"""
        # Mock data - in real implementation would calculate from actual data
        return [
            ("BitSkins", 92, COLORS["success"]),
            ("Waxpeer", 89, COLORS["success"]),
            ("SkinPort", 85, COLORS["info"]),
            ("Steam", 78, COLORS["warning"]),
            ("CSDeals", 83, COLORS["info"])
        ]
    
    def calculate_metrics(self):
        """Calculate success metrics"""
        # Get real data from controllers
        total_trades = random.randint(3000, 4000)  # Mock
        failed = random.randint(50, 150)  # Mock
        
        opportunities = self.app.profitability_controller.get_opportunities()
        best_profit = max((opp.get("profit_absolute", 0) for opp in opportunities), default=0)
        
        return [
            ("Successful Trades", f"{total_trades:,}"),
            ("Failed Attempts", str(failed)),
            ("Avg Profit per Trade", "$2.20"),
            ("Best Trade", f"${best_profit:.2f}"),
            ("Total Volume", "$892,473")
        ]
    
    def change_period(self, period):
        """Change analytics period"""
        self.current_period = period
        self.load_analytics_data()
        self.refresh_display()
    
    def load_analytics_data(self):
        """Load analytics data for current period"""
        # This would load historical data based on selected period
        pass
    
    def refresh_display(self):
        """Refresh all analytics displays"""
        # Update KPIs
        total_profit = self.calculate_total_profit()
        if "Total Profit" in self.kpi_cards:
            self.kpi_cards["Total Profit"].configure(text=f"${total_profit:,.2f}")
        
        # Update other displays...
    
    def generate_report(self):
        """Generate analytics report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = f"analytics_report_{self.current_period.replace(' ', '_')}_{timestamp}.json"
        
        report_data = {
            "period": self.current_period,
            "generated": datetime.now().isoformat(),
            "total_profit": self.calculate_total_profit(),
            "success_rate": self.calculate_success_rate(),
            "items_analyzed": self.calculate_items_analyzed(),
            "platform_performance": self.get_platform_performance()
        }
        
        try:
            with open(report_name, 'w') as f:
                json.dump(report_data, f, indent=2)
            print(f"Report generated: {report_name}")
        except Exception as e:
            print(f"Error generating report: {e}")
    
    def refresh(self):
        """Refresh analytics data"""
        self.load_analytics_data()
        self.refresh_display()