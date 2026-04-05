import random
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import ExecutionAdapter

class BacktestAdapter(ExecutionAdapter):
    """
    Simulated order execution for backtesting.
    Supports slippage, spread, and Monte Carlo resampling.
    """
    def __init__(self, initial_equity: float, base_spread: float = 0.0001, slippage_pct: float = 0.05):
        self.equity = initial_equity
        self.base_spread = base_spread
        self.slippage_pct = slippage_pct
        self.current_price = 0.0
        self.current_timestamp: Optional[datetime] = None
        self.open_positions: List[Dict[str, Any]] = []
        self.history: List[Dict[str, Any]] = []

    def set_market_state(self, price: float, timestamp: datetime):
        self.current_price = price
        self.current_timestamp = timestamp

    def place_order(self, pair: str, side: str, lot: float, client_id: str) -> Optional[Dict[str, Any]]:
        # Monte Carlo resampling for spread and slippage
        effective_spread = self.base_spread * (1 + random.uniform(-0.1, 0.2))
        slippage = self.current_price * self.slippage_pct * random.uniform(0, 0.001)

        fill_price = self.current_price
        if side == "LONG":
            fill_price += (effective_spread / 2) + slippage
        elif side == "SHORT":
            fill_price -= (effective_spread / 2) + slippage

        fill_details = {
            "pair": pair,
            "side": side,
            "lot": lot,
            "fill_price": fill_price,
            "client_id": client_id,
            "timestamp": self.current_timestamp,
            "id": f"sim_{len(self.history)}"
        }
        self.open_positions.append(fill_details)
        self.history.append(fill_details)
        return fill_details

    def flatten_all(self, pair: str) -> bool:
        """Calculate P&L for all positions and update equity."""
        total_pnl = 0.0
        for pos in self.open_positions:
            if pos["pair"] == pair:
                pnl = self.calculate_pnl(pos, self.current_price)
                total_pnl += pnl
        self.equity += total_pnl
        self.open_positions = [p for p in self.open_positions if p["pair"] != pair]
        return True

    def calculate_pnl(self, position: Dict[str, Any], exit_price: float) -> float:
        """P&L = (Exit - Entry) * Lot * 100000 (standard lot) for EURUSD."""
        side_mult = 1 if position["side"] == "LONG" else -1
        pip_value = 100000 # Standard lot
        return (exit_price - position["fill_price"]) * position["lot"] * pip_value * side_mult

    def get_market_price(self, pair: str) -> float:
        return self.current_price

    def get_account_equity(self) -> float:
        # Calculate floating P&L
        floating_pnl = sum([self.calculate_pnl(p, self.current_price) for p in self.open_positions])
        return self.equity + floating_pnl

    def get_open_positions(self) -> List[Dict[str, Any]]:
        return self.open_positions

    def get_avg_spread(self, pair: str) -> float:
        return self.base_spread
