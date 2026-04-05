# Rescue Path B: Runbook

## Configuration Guide
The main configuration file is `config/config.yaml`. It contains two presets: `conservative` and `aggressive`.

### Conservative (Live Default)
- `base_lot`: 0.01
- `lot_multiplier`: 0.8 (Anti-martingale)
- `max_adds`: 3
- `portfolio_stop_pct`: 0.05 (5% equity)
- `min_capital_recommendation`: $15,000

### Aggressive (Paper Only)
- `base_lot`: 0.02
- `lot_multiplier`: 1.0 (Fixed sizing)
- `max_adds`: 4
- `portfolio_stop_pct`: 0.07 (7% equity)
- `min_capital_recommendation`: $30,000

## Strategy Breakdown
### 1. Directional Signal
Located in `src/strategy/signals.py`. Uses an M5 momentum filter (EMA 20 cross).
### 2. Pyramiding Trigger
New legs added on 0.5 * ATR(M5) retracement from the last entry price.
### 3. Trend/Regime Gating
Uses H1 timeframe. ADX(14) > 30 OR price outside 20EMA volatility band (0.5 * ATR) blocks new cycles. Hysteresis re-enables at ADX < 25.
### 4. Risk & Exits
- **Portfolio Stop**: 5% of cycle equity.
- **Trailing Stop**: Aggregate ATR-based trail (1.0 * ATR).
- **Time Decay**: Auto-flatten after 6 hours.
- **Rollover**: Auto-flatten 60 mins before 5:00 PM EST.

## Monitoring
FastAPI serves a dashboard on port 8000.
- `GET /api/status`: Returns JSON status.
- `GET /`: Returns the HTML dashboard.

## Logging
- `logs/trading.log`: Rotating log file for events.
- `logs/audit_trail.json`: Detailed JSON record of all trades/flattens.
