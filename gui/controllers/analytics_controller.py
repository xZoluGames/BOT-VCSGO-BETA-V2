# Analytics Controller

import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class AnalyticsController:
    def __init__(self):
        self.data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
        self.analytics_data = {}
        
        self.load_analytics_data()
    
    def load_analytics_data(self):
        """Load analytics data from various sources"""
        try:
            # Load profitability history
            self.load_profitability_history()
            
            # Load scraper performance data
            self.load_scraper_performance()
            
            # Generate summary metrics
            self.generate_summary_metrics()
            
        except Exception as e:
            print(f"Error loading analytics data: {e}")
    
    def load_profitability_history(self):
        """Load historical profitability data"""
        try:
            profitability_file = os.path.join(self.data_path, "profitability_data.json")
            if os.path.exists(profitability_file):
                with open(profitability_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                self.analytics_data["profitability_history"] = data
                print(f"Loaded profitability history: {len(data)} entries")
            else:
                self.analytics_data["profitability_history"] = {}
                
        except Exception as e:
            print(f"Error loading profitability history: {e}")
            self.analytics_data["profitability_history"] = {}
    
    def load_scraper_performance(self):
        """Load scraper performance data from individual JSON files"""
        try:
            scraper_data = {}
            
            # List of expected data files
            data_files = [
                "bitskins_data.json", "waxpeer_data.json", "skinport_data.json",
                "steam_market_data.json", "csdeals_data.json", "empire_data.json",
                "shadowpay_data.json", "lisskins_data.json", "tradeit_data.json",
                "rapidskins_data.json", "manncostore_data.json", "marketcsgo_data.json",
                "skindeck_data.json", "skinout_data.json", "white_data.json",
                "cstrade_data.json", "steam_listing_data.json"
            ]
            
            for filename in data_files:
                file_path = os.path.join(self.data_path, filename)
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                        scraper_name = filename.replace("_data.json", "")
                        scraper_data[scraper_name] = {
                            "item_count": len(data) if isinstance(data, list) else 0,
                            "last_updated": datetime.fromtimestamp(os.path.getmtime(file_path)),
                            "file_size_mb": os.path.getsize(file_path) / (1024 * 1024)
                        }
                        
                    except Exception as e:
                        print(f"Error loading {filename}: {e}")
            
            self.analytics_data["scraper_performance"] = scraper_data
            print(f"Loaded scraper performance data for {len(scraper_data)} scrapers")
            
        except Exception as e:
            print(f"Error loading scraper performance: {e}")
            self.analytics_data["scraper_performance"] = {}
    
    def generate_summary_metrics(self):
        """Generate summary analytics metrics"""
        try:
            metrics = {
                "total_items_scraped": 0,
                "total_opportunities_found": 0,
                "avg_profit_percentage": 0,
                "best_profit_opportunity": 0,
                "active_scrapers": 0,
                "data_freshness_hours": 0,
                "platform_coverage": 0
            }
            
            # Calculate from scraper performance
            scraper_perf = self.analytics_data.get("scraper_performance", {})
            metrics["total_items_scraped"] = sum(
                data.get("item_count", 0) for data in scraper_perf.values()
            )
            metrics["active_scrapers"] = len(scraper_perf)
            
            # Calculate data freshness
            if scraper_perf:
                newest_update = max(
                    data.get("last_updated", datetime.min) 
                    for data in scraper_perf.values()
                )
                hours_diff = (datetime.now() - newest_update).total_seconds() / 3600
                metrics["data_freshness_hours"] = round(hours_diff, 1)
            
            # Calculate from profitability history
            prof_history = self.analytics_data.get("profitability_history", {})
            if prof_history:
                # Get latest profitability data
                latest_timestamp = max(prof_history.keys())
                latest_data = prof_history[latest_timestamp]
                
                opportunities = latest_data.get("opportunities", [])
                if opportunities:
                    metrics["total_opportunities_found"] = len(opportunities)
                    
                    profit_percentages = [
                        opp.get("profit_percent", 0) for opp in opportunities
                    ]
                    metrics["avg_profit_percentage"] = round(
                        sum(profit_percentages) / len(profit_percentages), 2
                    )
                    metrics["best_profit_opportunity"] = round(max(profit_percentages), 2)
            
            # Platform coverage (estimate)
            metrics["platform_coverage"] = min(100, metrics["active_scrapers"] * 5)
            
            self.analytics_data["summary_metrics"] = metrics
            
        except Exception as e:
            print(f"Error generating summary metrics: {e}")
            self.analytics_data["summary_metrics"] = {}
    
    def get_summary_metrics(self):
        """Get summary analytics metrics"""
        return self.analytics_data.get("summary_metrics", {})
    
    def get_profit_trends(self, days=7):
        """Get profit trends over specified days"""
        try:
            prof_history = self.analytics_data.get("profitability_history", {})
            
            # Filter data by date range
            cutoff_date = datetime.now() - timedelta(days=days)
            trends = []
            
            for timestamp_str, data in prof_history.items():
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp >= cutoff_date:
                        opportunities = data.get("opportunities", [])
                        total_opportunities = len(opportunities)
                        avg_profit = 0
                        
                        if opportunities:
                            profits = [opp.get("profit_percent", 0) for opp in opportunities]
                            avg_profit = sum(profits) / len(profits)
                        
                        trends.append({
                            "date": timestamp.strftime("%Y-%m-%d %H:%M"),
                            "opportunities": total_opportunities,
                            "avg_profit": round(avg_profit, 2)
                        })
                        
                except Exception as e:
                    print(f"Error parsing timestamp {timestamp_str}: {e}")
                    continue
            
            # Sort by date
            trends.sort(key=lambda x: x["date"])
            return trends
            
        except Exception as e:
            print(f"Error getting profit trends: {e}")
            return []
    
    def get_scraper_performance_summary(self):
        """Get scraper performance summary"""
        try:
            scraper_perf = self.analytics_data.get("scraper_performance", {})
            
            summary = []
            for scraper_name, data in scraper_perf.items():
                summary.append({
                    "name": scraper_name.replace("_", " ").title(),
                    "items": data.get("item_count", 0),
                    "last_updated": data.get("last_updated", datetime.min).strftime("%Y-%m-%d %H:%M"),
                    "size_mb": round(data.get("file_size_mb", 0), 2),
                    "status": "Active" if data.get("item_count", 0) > 0 else "Inactive"
                })
            
            # Sort by item count (descending)
            summary.sort(key=lambda x: x["items"], reverse=True)
            return summary
            
        except Exception as e:
            print(f"Error getting scraper performance summary: {e}")
            return []
    
    def get_platform_distribution(self):
        """Get distribution of opportunities by platform"""
        try:
            prof_history = self.analytics_data.get("profitability_history", {})
            
            if not prof_history:
                return []
            
            # Get latest data
            latest_timestamp = max(prof_history.keys())
            latest_data = prof_history[latest_timestamp]
            opportunities = latest_data.get("opportunities", [])
            
            # Count by platform
            platform_counts = defaultdict(int)
            for opp in opportunities:
                buy_platform = opp.get("buy_platform", "Unknown")
                platform_counts[buy_platform] += 1
            
            # Convert to list
            distribution = [
                {"platform": platform, "count": count}
                for platform, count in platform_counts.items()
            ]
            
            # Sort by count (descending)
            distribution.sort(key=lambda x: x["count"], reverse=True)
            return distribution
            
        except Exception as e:
            print(f"Error getting platform distribution: {e}")
            return []
    
    def get_performance_metrics(self):
        """Get overall performance metrics"""
        try:
            metrics = self.get_summary_metrics()
            
            # Calculate additional performance indicators
            performance = {
                "efficiency_score": 0,
                "data_quality_score": 0,
                "opportunity_rate": 0,
                "coverage_score": 0
            }
            
            # Efficiency score (based on opportunities per item)
            if metrics.get("total_items_scraped", 0) > 0:
                performance["opportunity_rate"] = round(
                    (metrics.get("total_opportunities_found", 0) / metrics.get("total_items_scraped", 1)) * 100, 3
                )
                performance["efficiency_score"] = min(100, performance["opportunity_rate"] * 1000)
            
            # Data quality score (based on freshness and active scrapers)
            freshness_hours = metrics.get("data_freshness_hours", 24)
            freshness_score = max(0, 100 - (freshness_hours * 2))  # Penalty for old data
            active_ratio = min(100, metrics.get("active_scrapers", 0) * 5)
            performance["data_quality_score"] = round((freshness_score + active_ratio) / 2, 1)
            
            # Coverage score
            performance["coverage_score"] = metrics.get("platform_coverage", 0)
            
            return performance
            
        except Exception as e:
            print(f"Error getting performance metrics: {e}")
            return {}
    
    def export_analytics_report(self, format="json"):
        """Export analytics report"""
        try:
            report = {
                "generated_at": datetime.now().isoformat(),
                "summary_metrics": self.get_summary_metrics(),
                "profit_trends": self.get_profit_trends(30),  # Last 30 days
                "scraper_performance": self.get_scraper_performance_summary(),
                "platform_distribution": self.get_platform_distribution(),
                "performance_metrics": self.get_performance_metrics()
            }
            
            if format == "json":
                return json.dumps(report, indent=2)
            else:
                # Could add CSV, Excel formats here
                return report
                
        except Exception as e:
            print(f"Error exporting analytics report: {e}")
            return None
    
    def refresh_analytics(self):
        """Refresh all analytics data"""
        self.load_analytics_data()
    def load_scraper_data(self, filename):
        """Load data from a scraper JSON file"""
        try:
            filepath = os.path.join(self.data_path, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:  # ← Agregar encoding='utf-8'
                    return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
        return []
    def get_total_items_analyzed(self):
        """Get total items analyzed across all platforms"""
        total = 0
        for filename in os.listdir(self.data_path):
            if filename.endswith('_data.json') and not filename.startswith('profitability'):
                try:
                    filepath = os.path.join(self.data_path, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            total += len(data)
                except:
                    pass
        return total