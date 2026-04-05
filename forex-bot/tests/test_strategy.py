import unittest
import pandas as pd
from src.utils.indicators import calculate_atr, calculate_ema, calculate_adx
from src.strategy.risk_manager import RiskManager

class TestIndicators(unittest.TestCase):
    def test_atr(self):
        high = pd.Series([10.0, 11.0, 12.0, 11.5])
        low = pd.Series([9.0, 9.5, 10.0, 10.5])
        close = pd.Series([9.5, 10.5, 11.0, 11.2])
        atr = calculate_atr(high, low, close, period=2)
        self.assertFalse(pd.isna(atr.iloc[-1]))

class TestRiskManager(unittest.TestCase):
    def setUp(self):
        self.config = {
            "base_lot": 0.01,
            "lot_multiplier": 0.8,
            "max_adds": 3,
            "sizing_mode": "fixed-fraction",
            "portfolio_stop_pct": 0.05
        }
        self.risk = RiskManager(self.config)

    def test_fixed_fraction_sizing(self):
        lot = self.risk.calculate_next_lot(0.1)
        self.assertEqual(lot, 0.08)

    def test_retrace_trigger_long(self):
        # ATR = 0.0010, retrace = 0.0005
        should_add = self.risk.should_add_leg(1.0994, 1.1000, 0.0010, "LONG")
        self.assertTrue(should_add)

        should_not_add = self.risk.should_add_leg(1.0996, 1.1000, 0.0010, "LONG")
        self.assertFalse(should_not_add)

    def test_portfolio_stop(self):
        stop_hit = self.risk.check_portfolio_stop(9400, 10000)
        self.assertTrue(stop_hit) # 6% drawdown

        stop_not_hit = self.risk.check_portfolio_stop(9600, 10000)
        self.assertFalse(stop_not_hit) # 4% drawdown

if __name__ == "__main__":
    unittest.main()
