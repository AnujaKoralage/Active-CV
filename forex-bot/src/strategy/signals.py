import pandas as pd
from typing import Dict, Any, List
from .base import Signal
from ..utils.indicators import calculate_ema

class EMAMomentumSignal(Signal):
    """
    Signal logic: M5 price crosses EMA20 or simple momentum threshold.
    """
    def __init__(self, ema_period: int = 20, momentum_threshold: float = 0.0001):
        self.ema_period = ema_period
        self.momentum_threshold = momentum_threshold
        self.bars: List[pd.Series] = []
        self.history: List[float] = [] # stores closes

    def on_bar(self, bar: pd.Series) -> None:
        self.bars.append(bar)
        self.history.append(bar['close'])
        # Keep a buffer of at least ema_period * 2
        if len(self.bars) > self.ema_period * 2:
            self.bars.pop(0)
            self.history.pop(0)

    def generate_signal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if len(self.history) < self.ema_period:
            return {"direction": "NONE", "confidence": 0.0}

        closes = pd.Series(self.history)
        ema = calculate_ema(closes, self.ema_period)

        current_close = closes.iloc[-1]
        prev_close = closes.iloc[-2]
        current_ema = ema.iloc[-1]

        # Momentum check: simple change
        momentum = (current_close - prev_close) / prev_close

        direction = "NONE"
        confidence = 0.0

        if current_close > current_ema and momentum > self.momentum_threshold:
            direction = "LONG"
            confidence = 1.0
        elif current_close < current_ema and momentum < -self.momentum_threshold:
            direction = "SHORT"
            confidence = 1.0

        return {"direction": direction, "confidence": confidence}
