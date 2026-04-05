from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd

class Signal(ABC):
    """Abstract Base Class for trading signals."""

    @abstractmethod
    def on_bar(self, bar: pd.Series) -> None:
        """Update internal state with a new bar."""
        pass

    @abstractmethod
    def generate_signal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a trading signal based on current state.
        Returns a dict: {"direction": "LONG"/"SHORT"/"NONE", "confidence": 0.0-1.0}
        """
        pass
