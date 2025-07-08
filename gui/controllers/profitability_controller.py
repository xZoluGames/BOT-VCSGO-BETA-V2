# gui/controllers/profitability_controller.py

import os
import sys
import json
import threading
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class ProfitabilityController:
    def __init__(self):
        self.data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "data", 
            "profitability_data.json"
        )
        self.opportunities = []
        self.callbacks = []
        self.is_calculating = False
        
    def get_opportunities(self):
        """Get current profitability opportunities from file"""
        try:
            if os.path.exists(self.data_path):
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    if 'current' in data and 'opportunities' in data['current']:
                        self.opportunities = data['current']['opportunities']
                        return self.opportunities
            return []
        except Exception as e:
            print(f"Error loading profitability data: {e}")
            return []
    
    def calculate_opportunities(self, min_profit=1.0, callback=None):
        """Run profitability engine to calculate new opportunities"""
        if self.is_calculating:
            print("Already calculating opportunities...")
            return
        
        # Add callback if provided
        if callback:
            self.callbacks.append(callback)
        
        # Run in thread
        thread = threading.Thread(
            target=self._run_profitability_engine,
            args=(min_profit,),  # ← Aquí está pasando 1.0 como porcentaje
            daemon=True
        )
        thread.start()
    
    def _run_profitability_engine(self, min_profit):
        """Thread worker to run profitability engine"""
        try:
            self.is_calculating = True
            
            # Import and run the profitability engine
            from core.profitability_engine import ProfitabilityEngine
            
            engine = ProfitabilityEngine()
            engine.calculate_opportunities(min_profit_percentage=min_profit)
            
            # Reload opportunities
            self.get_opportunities()
            
            # Notify callbacks
            for callback in self.callbacks:
                try:
                    callback("success", len(self.opportunities))
                except:
                    pass
                    
        except Exception as e:
            print(f"Error calculating opportunities: {e}")
            
            # Notify callbacks of error
            for callback in self.callbacks:
                try:
                    callback("error", str(e))
                except:
                    pass
                    
        finally:
            self.is_calculating = False
            self.callbacks.clear()
    
    def get_statistics(self):
        """Get profitability statistics"""
        try:
            if os.path.exists(self.data_path):
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    
                    stats = {
                        "total_opportunities": 0,
                        "best_profit": 0,
                        "avg_profit": 0,
                        "last_calculation": None
                    }
                    
                    if 'current' in data:
                        current = data['current']
                        stats["total_opportunities"] = current.get("total_opportunities", 0)
                        stats["last_calculation"] = current.get("timestamp")
                        
                        if current.get("opportunities"):
                            profits = [opp.get("profit_percentage", 0) for opp in current["opportunities"]]
                            if profits:
                                stats["best_profit"] = max(profits) * 100
                                stats["avg_profit"] = (sum(profits) / len(profits)) * 100
                    
                    return stats
                    
            return {}
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}
    def get_opportunities_filtered(self, min_profit=1.0):
        """Get opportunities filtered by minimum profit percentage"""
        all_opportunities = self.get_opportunities()
        filtered = [
            opp for opp in all_opportunities 
            if opp.get("profit_percentage_display", 0) >= min_profit
        ]
        return filtered