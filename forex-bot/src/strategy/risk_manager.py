import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime

class RiskManager:
    """
    Handles pyramiding, sizing, retrace triggers, portfolio stops, and trailing stops.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.l0 = config.get("base_lot", 0.01)
        self.r = config.get("lot_multiplier", 0.8)
        self.max_adds = config.get("max_adds", 3)
        self.sizing_mode = config.get("sizing_mode", "fixed-fraction") # "fixed-fraction" or "atr-risk"
        self.risk_per_add_usd = config.get("risk_per_add_usd", 10)
        self.pip_value = config.get("pip_value", 10.0) # standard lot $10 per pip for EURUSD

        self.portfolio_stop_pct = config.get("portfolio_stop_pct", 0.05)
        self.trailing_stop_atr_mult = config.get("trailing_stop_atr_mult", 1.0)

        self.virtual_legs: List[Dict[str, Any]] = []
        self.peak_equity = 0.0
        self.current_cycle_side: Optional[str] = None # "LONG" or "SHORT"

    def check_portfolio_stop(self, current_equity: float, initial_equity: float) -> bool:
        """Check if 5% equity cycle stop-loss has been hit."""
        drawdown = (initial_equity - current_equity) / initial_equity
        if drawdown >= self.portfolio_stop_pct:
            return True
        return False

    def calculate_next_lot(self, prev_lot: float, atr_m5: float = 0.0) -> float:
        """Calculate lot size for the next add."""
        if self.sizing_mode == "fixed-fraction":
            return round(prev_lot * self.r, 2)
        elif self.sizing_mode == "atr-risk":
            # lot = risk_per_add_usd / (ATR_pips * pip_value)
            # Assuming atr_m5 is in price units, convert to pips (e.g. 0.0001 = 1 pip)
            atr_pips = atr_m5 / 0.0001
            if atr_pips <= 0:
                return self.l0
            lot = self.risk_per_add_usd / (atr_pips * self.pip_value)
            # Ensure it doesn't increase if we want anti-martingale
            return min(round(lot, 2), prev_lot)
        return self.l0

    def should_add_leg(self, current_price: float, last_entry_price: float, atr_m5: float, side: str) -> bool:
        """Check if price retraced by 0.5 * ATR(14, M5)."""
        retrace_distance = 0.5 * atr_m5
        if side == "LONG":
            # Add buy if price moved DOWN from last entry
            return current_price <= (last_entry_price - retrace_distance)
        elif side == "SHORT":
            # Add sell if price moved UP from last entry
            return current_price >= (last_entry_price + retrace_distance)
        return False

    def calculate_trailing_stop(self, current_price: float, atr_m5: float, side: str, prev_trailing_stop: float) -> float:
        """Calculate aggregate trailing stop based on ATR."""
        trail_dist = self.trailing_stop_atr_mult * atr_m5
        if side == "LONG":
            new_stop = current_price - trail_dist
            return max(new_stop, prev_trailing_stop) if prev_trailing_stop > 0 else new_stop
        elif side == "SHORT":
            new_stop = current_price + trail_dist
            return min(new_stop, prev_trailing_stop) if prev_trailing_stop > 0 else new_stop
        return 0.0

    def add_virtual_leg(self, entry_price: float, lot: float, atr_used: float, timestamp: datetime):
        self.virtual_legs.append({
            "entry_price": entry_price,
            "lot": lot,
            "atr_used": atr_used,
            "timestamp": timestamp
        })

    def reset_cycle(self):
        self.virtual_legs = []
        self.current_cycle_side = None
        self.peak_equity = 0.0
