from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

class ExecutionAdapter(ABC):
    """Abstract Base Class for order execution."""

    @abstractmethod
    def place_order(self, pair: str, side: str, lot: float, client_id: str) -> Optional[Dict[str, Any]]:
        """Place an order and return fill details."""
        pass

    @abstractmethod
    def flatten_all(self, pair: str) -> bool:
        """Close all open positions for a pair."""
        pass

    @abstractmethod
    def get_market_price(self, pair: str) -> float:
        """Get the current market price."""
        pass

    @abstractmethod
    def get_account_equity(self) -> float:
        """Get current account equity."""
        pass

    @abstractmethod
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get a list of open positions."""
        pass

    @abstractmethod
    def get_avg_spread(self, pair: str) -> float:
        """Get the average spread for a pair."""
        pass
