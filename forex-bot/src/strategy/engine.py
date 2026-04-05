import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, time
import pytz
from ..strategy.base import Signal
from ..strategy.risk_manager import RiskManager
from ..execution.base import ExecutionAdapter
from ..utils.indicators import calculate_adx, calculate_ema, calculate_atr
from ..utils.logger import get_trading_logger, get_audit_trail

logger = get_trading_logger()
audit = get_audit_trail()

class StrategyEngine:
    """
    Orchestrates the trading cycle, trend/regime gating, and rollover logic.
    """
    def __init__(self, signal: Signal, risk: RiskManager, execution: ExecutionAdapter, config: Dict[str, Any]):
        self.signal = signal
        self.risk = risk
        self.execution = execution
        self.config = config

        self.pair = config.get("pair", "EUR_USD")
        self.timeframe_entry = config.get("timeframe_entry", "M5")
        self.timeframe_filter = config.get("timeframe_filter", "H1")

        self.adx_threshold_entry = config.get("adx_threshold_entry", 30)
        self.adx_threshold_reenable = config.get("adx_threshold_reenable", 25)
        self.is_gated = False

        self.max_hold_hours = config.get("max_hold_hours", 6)
        self.pre_rollover_block_min = config.get("pre_rollover_block_min", 60)
        self.flatten_pre_rollover = config.get("flatten_pre_rollover", True)

        self.cycle_start_time: Optional[datetime] = None
        self.initial_equity: float = 0.0
        self.trailing_stop: float = 0.0

    def run_tick(self, m1_bar: pd.Series, m5_data: pd.DataFrame, h1_data: pd.DataFrame):
        """Processes one M1/tick update."""
        current_time = m1_bar.name
        current_price = m1_bar['close']

        # 1. Update Signal and Risk internal states
        # Typically called on bar close, but here we provide context

        # 2. Check Portfolio-level stops (Hard stop and Trailing stop)
        if self.risk.current_cycle_side:
            current_equity = self.execution.get_account_equity()
            if self.risk.check_portfolio_stop(current_equity, self.initial_equity):
                self._flatten_cycle("HARD_STOP")
                return

            # Trailing stop update (using M5 ATR)
            atr_m5 = calculate_atr(m5_data['high'], m5_data['low'], m5_data['close']).iloc[-1]
            self.trailing_stop = self.risk.calculate_trailing_stop(
                current_price, atr_m5, self.risk.current_cycle_side, self.trailing_stop
            )

            if (self.risk.current_cycle_side == "LONG" and current_price <= self.trailing_stop) or \
               (self.risk.current_cycle_side == "SHORT" and current_price >= self.trailing_stop):
                self._flatten_cycle("TRAILING_STOP")
                return

            # 3. Check Time-decay and Rollover
            if self._is_rollover_approaching(current_time) and self.flatten_pre_rollover:
                self._flatten_cycle("ROLLOVER")
                return

            if self.cycle_start_time and (current_time - self.cycle_start_time).total_seconds() > self.max_hold_hours * 3600:
                self._flatten_cycle("TIME_DECAY")
                return

            # 4. Check for pyramiding (Add legs)
            if len(self.risk.virtual_legs) < self.risk.max_adds:
                last_entry = self.risk.virtual_legs[-1]['entry_price']
                if self.risk.should_add_leg(current_price, last_entry, atr_m5, self.risk.current_cycle_side):
                    self._add_leg(current_price, atr_m5)

        else:
            # 5. Entry Logic (No active cycle)
            if self._is_gated_by_trend(h1_data):
                return

            if self._is_rollover_approaching(current_time):
                return

            # Update signal with current M5 bar if it just closed
            # For simplicity, we assume engine receives latest resampled data
            self.signal.on_bar(m5_data.iloc[-1])
            sig = self.signal.generate_signal({"price": current_price})

            if sig["direction"] != "NONE":
                atr_m5 = calculate_atr(m5_data['high'], m5_data['low'], m5_data['close']).iloc[-1]
                if self._check_cost_edge(atr_m5):
                    self._start_cycle(sig["direction"], current_price, atr_m5, current_time)

    def _get_last_adx(self, h1_data: pd.DataFrame) -> float:
        if len(h1_data) < 20: return 0.0
        return calculate_adx(h1_data['high'], h1_data['low'], h1_data['close']).iloc[-1]

    def _is_gated_by_trend(self, h1_data: pd.DataFrame) -> bool:
        """ADX(14) and 20EMA on H1 trend/regime filter."""
        if len(h1_data) < 20: return True

        adx = self._get_last_adx(h1_data)
        ema = calculate_ema(h1_data['close'], 20).iloc[-1]
        atr = calculate_atr(h1_data['high'], h1_data['low'], h1_data['close']).iloc[-1]

        price = h1_data['close'].iloc[-1]
        k = self.config.get("ema_band_k", 0.5)
        outside_band = abs(price - ema) > (k * atr)

        # Hysteresis for ADX
        if adx > self.adx_threshold_entry or outside_band:
            self.is_gated = True
        elif adx < self.adx_threshold_reenable and not outside_band:
            self.is_gated = False

        return self.is_gated

    def _is_rollover_approaching(self, current_time: datetime) -> bool:
        """5:00 PM EST rollover check."""
        est = pytz.timezone('US/Eastern')
        if current_time.tzinfo is None:
            current_time = pytz.utc.localize(current_time)
        time_est = current_time.astimezone(est).time()
        # Block 60 mins before 17:00
        if time_est >= time(16, 0) and time_est < time(17, 0):
            return True
        return False

    def _check_cost_edge(self, atr_m5: float) -> bool:
        """Cost-aware pre-entry check."""
        avg_spread = self.execution.get_avg_spread(self.pair)
        est_slippage = 0.00005 # configurable
        # expected_orders_remaining: worst case max_adds
        expected_orders = self.risk.max_adds + 1
        rt_cost = (expected_orders * avg_spread) + (expected_orders * est_slippage)

        # Expected edge: based on ATR or historical signal alpha
        # For now, use a factor of ATR as minimum edge
        expected_edge = atr_m5 * 1.5
        safety_factor = 1.2
        return expected_edge > (rt_cost * safety_factor)

    def _start_cycle(self, side: str, price: float, atr_m5: float, timestamp: datetime):
        lot = self.risk.l0
        res = self.execution.place_order(self.pair, side, lot, f"init_{timestamp.timestamp()}")
        if res:
            self.risk.current_cycle_side = side
            self.risk.add_virtual_leg(res['fill_price'], lot, atr_m5, timestamp)
            self.initial_equity = self.execution.get_account_equity()
            self.cycle_start_time = timestamp
            self.trailing_stop = 0.0 # Will be set on next tick
            logger.info(f"Started {side} cycle at {res['fill_price']}")
            audit.log_event("CYCLE_START", {"side": side, "price": res['fill_price'], "lot": lot})

    def _add_leg(self, price: float, atr_m5: float):
        prev_lot = self.risk.virtual_legs[-1]['lot']
        lot = self.risk.calculate_next_lot(prev_lot, atr_m5)
        side = self.risk.current_cycle_side
        res = self.execution.place_order(self.pair, side, lot, f"add_{len(self.risk.virtual_legs)}")
        if res:
            self.risk.add_virtual_leg(res['fill_price'], lot, atr_m5, datetime.utcnow())
            logger.info(f"Added {side} leg at {res['fill_price']} lot {lot}")
            audit.log_event("LEG_ADD", {"side": side, "price": res['fill_price'], "lot": lot})

    def _flatten_cycle(self, reason: str):
        self.execution.flatten_all(self.pair)
        logger.info(f"Cycle flattened. Reason: {reason}")
        audit.log_event("CYCLE_FLATTEN", {"reason": reason})
        self.risk.reset_cycle()
        self.cycle_start_time = None
        self.initial_equity = 0.0
