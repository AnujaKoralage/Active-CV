# Rescue Path B: Safe Anti-Martingale Forex Algo

A production-ready Python forex trading bot implementing a safe, single-side, anti-martingale pyramiding strategy.

## Features
- **Single-side directional scaling**: No opposite-side hedging.
- **Decision Logic**: M5 bars for execution, H1 for trend/regime gating (ADX + EMA).
- **Anti-Martingale Pyramid**: Successive adds decrease or remain constant in size.
- **Risk Management**: Hard portfolio stop-loss (5%), trailing stop (ATR-based), time-decay, and rollover protection.
- **Execution Adapters**: Support for OANDA v20 (live/paper) and Backtest (CSV) with Monte Carlo resampling.
- **Dashboard**: Real-time monitoring via FastAPI and HTML dashboard.

## Installation
1. `cd forex-bot`
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your OANDA credentials.

## Usage
### Backtesting
```bash
python3 cli/backtest.py --data sample/eurusd_1m_sample.csv --config config/config.yaml --out results.json
```

### Paper Trading (OANDA Sandbox)
```bash
python3 cli/paper_run.py --config config/config.yaml
```

### Live Trading
```bash
python3 cli/run_live.py --config config/config.yaml
```

## Deployment
### Docker
```bash
docker-compose up --build -d
```

### Systemd
1. Edit `docs/forex-bot.service` with your user and paths.
2. `sudo cp docs/forex-bot.service /etc/systemd/system/`
3. `sudo systemctl enable forex-bot && sudo systemctl start forex-bot`

## Emergency Flatten
To immediately close all positions:
1. Access the VPS/Server.
2. Run `python3 cli/run_live.py --config config/config.yaml` and interrupt with `Ctrl+C` (the engine is configured to flatten on SIGTERM/SIGINT).
3. Alternatively, use the OANDA mobile app or web portal to "Close All Positions" for the pair.

## Safety Warning
**Never run live without paper testing for 3 months.** Ensure Monte Carlo stress testing shows worst-case 99th percentile drawdown is within your risk tolerance.
