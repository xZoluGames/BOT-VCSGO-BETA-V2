# Chart Components

import customtkinter as ctk
from gui.config.constants import COLORS, FONT_SIZES, CHART_COLORS
import tkinter as tk

class SimpleChart(ctk.CTkFrame):
    def __init__(self, parent, title, chart_type="line"):
        super().__init__(parent, fg_color=COLORS["card"], corner_radius=10)
        self.title = title
        self.chart_type = chart_type
        self.data = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup chart UI"""
        # Title
        title_label = ctk.CTkLabel(
            self,
            text=self.title,
            font=ctk.CTkFont(size=FONT_SIZES["subtitle"], weight="bold"),
            text_color=COLORS["text"]
        )
        title_label.pack(pady=(20, 10))
        
        # Chart canvas
        self.canvas = tk.Canvas(
            self,
            width=400,
            height=200,
            bg=COLORS["card"],
            highlightthickness=0
        )
        self.canvas.pack(pady=(0, 20), padx=20)
        
        # Draw placeholder
        self.draw_placeholder()
    
    def draw_placeholder(self):
        """Draw placeholder chart"""
        self.canvas.delete("all")
        
        # Draw axes
        self.canvas.create_line(50, 180, 350, 180, fill=COLORS["border"], width=2)  # X-axis
        self.canvas.create_line(50, 20, 50, 180, fill=COLORS["border"], width=2)   # Y-axis
        
        # Draw sample data
        if self.chart_type == "line":
            self.draw_line_chart()
        elif self.chart_type == "bar":
            self.draw_bar_chart()
    
    def draw_line_chart(self):
        """Draw line chart"""
        # Sample data points
        points = [(70, 150), (120, 100), (170, 130), (220, 80), (270, 120), (320, 60)]
        
        # Draw line
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            self.canvas.create_line(x1, y1, x2, y2, fill=COLORS["primary"], width=3)
        
        # Draw points
        for x, y in points:
            self.canvas.create_oval(x-3, y-3, x+3, y+3, fill=COLORS["primary"], outline="white", width=2)
    
    def draw_bar_chart(self):
        """Draw bar chart"""
        # Sample data
        bars = [80, 120, 60, 140, 100, 160]
        bar_width = 30
        spacing = 45
        
        for i, height in enumerate(bars):
            x = 70 + i * spacing
            y = 180 - height
            color = CHART_COLORS[i % len(CHART_COLORS)]
            
            self.canvas.create_rectangle(
                x, y, x + bar_width, 180,
                fill=color, outline="white", width=1
            )
    
    def update_data(self, new_data):
        """Update chart with new data"""
        self.data = new_data
        self.draw_placeholder()  # For now, just redraw placeholder

class MetricsGrid(ctk.CTkFrame):
    def __init__(self, parent, metrics_data):
        super().__init__(parent, fg_color="transparent")
        self.metrics_data = metrics_data
        self.metric_labels = {}
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup metrics grid"""
        # Create grid of metrics
        for i, (key, value) in enumerate(self.metrics_data.items()):
            row = i // 4
            col = i % 4
            
            # Metric card
            metric_frame = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=8)
            metric_frame.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
            
            # Configure grid weight
            self.grid_columnconfigure(col, weight=1)
            
            # Metric label
            key_label = ctk.CTkLabel(
                metric_frame,
                text=key.replace("_", " ").title(),
                font=ctk.CTkFont(size=FONT_SIZES["small"]),
                text_color=COLORS["text_secondary"]
            )
            key_label.pack(pady=(10, 5))
            
            # Value label
            value_label = ctk.CTkLabel(
                metric_frame,
                text=str(value),
                font=ctk.CTkFont(size=FONT_SIZES["subtitle"], weight="bold"),
                text_color=COLORS["primary"]
            )
            value_label.pack(pady=(0, 10))
            
            # Store reference for updates
            self.metric_labels[key] = value_label
    
    def update_metric(self, key, new_value):
        """Update a specific metric"""
        if key in self.metric_labels:
            self.metric_labels[key].configure(text=str(new_value))
    
    def update_all_metrics(self, new_data):
        """Update all metrics"""
        for key, value in new_data.items():
            self.update_metric(key, value)