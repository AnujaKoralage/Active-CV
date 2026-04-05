import argparse
import yaml
import time
import os
import pandas as pd
from datetime import datetime
from src.strategy.signals import EMAMomentumSignal
from src.strategy.risk_manager import RiskManager
from src.strategy.engine import StrategyEngine
from src.execution.oanda_adapter import OandaV20Adapter
from src.monitoring.app import app, update_state
import uvicorn
import threading
from dotenv import load_dotenv

load_dotenv()

def fetch_and_resample(adapter, pair, granularity, count=100):
    candles = adapter.get_candles(pair, granularity, count)
    if not candles:
        return None

    df = pd.DataFrame([{
        "timestamp": pd.to_datetime(c["time"]),
        "open": float(c["mid"]["o"]),
        "high": float(c["mid"]["h"]),
        "low": float(c["mid"]["l"]),
        "close": float(c["mid"]["c"]),
        "volume": int(c["volume"])
    } for c in candles])
    df.set_index("timestamp", inplace=True)
    return df

def run_live(config_path: str, paper: bool = False):
    # Load config
    with open(config_path, 'r') as f:
        config_full = yaml.safe_load(f)
        active_preset = config_full.get("active_preset", "conservative")
        config = config_full['presets'][active_preset]
        config.update({k: v for k, v in config_full.items() if k != 'presets'})

    # Initialize components
    signal = EMAMomentumSignal()
    risk = RiskManager(config)
    execution = OandaV20Adapter(
        api_key=os.getenv("OANDA_API_KEY", ""),
        account_id=os.getenv("OANDA_ACCOUNT_ID", ""),
        sandbox=paper
    )
    engine = StrategyEngine(signal, risk, execution, config)

    # Start FastAPI in a background thread
    dashboard_thread = threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": "0.0.0.0", "port": config.get("dashboard_port", 8000)},
        daemon=True
    )
    dashboard_thread.start()

    print(f"Starting {'PAPER' if paper else 'LIVE'} agent. Dashboard at http://localhost:{config.get('dashboard_port', 8000)}")

    pair = config.get("pair", "EUR_USD")

    # Main live loop
    try:
        while True:
            # 1. Fetch latest candles from OANDA (M1 for tick, M5 and H1 for state)
            m1_data = fetch_and_resample(execution, pair, "M1", 50)
            m5_data = fetch_and_resample(execution, pair, "M5", 50)
            h1_data = fetch_and_resample(execution, pair, "H1", 50)

            if m1_data is not None and m5_data is not None and h1_data is not None:
                current_tick = m1_data.iloc[-1]
                engine.run_tick(current_tick, m5_data, h1_data)

                # Update Dashboard State
                update_state({
                    "equity": execution.get_account_equity(),
                    "open_positions": execution.get_open_positions(),
                    "is_gated": engine.is_gated,
                    "adx_h1": engine._get_last_adx(h1_data) # Add helper to engine or status
                })

            time.sleep(10) # Poll every 10 seconds for sandbox stability
    except KeyboardInterrupt:
        print("Shutting down...")
        engine._flatten_cycle("MANUAL_SHUTDOWN")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--paper", action="store_true")
    args = parser.parse_args()
    run_live(args.config, args.paper)
