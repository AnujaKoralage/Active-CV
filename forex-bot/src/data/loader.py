import pandas as pd
import os
from typing import Optional, List

class DataLoader:
    """Loads CSV 1m/tick data for backtesting."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data: Optional[pd.DataFrame] = None

    def load(self, pair: str = "EURUSD"):
        """Load data and ensure required columns exist."""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Data file {self.filepath} not found.")

        # Expecting: timestamp, open, high, low, close, volume
        self.data = pd.read_csv(self.filepath)
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        self.data.set_index('timestamp', inplace=True)
        return self.data

    def get_resampled(self, timeframe: str = "5min"):
        """Resample data to target timeframe (e.g., M5, H1)."""
        if self.data is None:
            self.load()

        ohlc_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        return self.data.resample(timeframe).agg(ohlc_dict).dropna()
