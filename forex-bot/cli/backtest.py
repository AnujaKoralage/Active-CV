import argparse
import yaml
import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from src.data.loader import DataLoader
from src.strategy.signals import EMAMomentumSignal
from src.strategy.risk_manager import RiskManager
from src.strategy.engine import StrategyEngine
from src.execution.backtest_adapter import BacktestAdapter

def calculate_metrics(equity_series, risk_free_rate=0.0):
    returns = equity_series.pct_change().dropna()
    if returns.empty:
        return {}

    win_rate = len(returns[returns > 0]) / len(returns) if len(returns) > 0 else 0
    sharpe = (returns.mean() - risk_free_rate) / returns.std() * np.sqrt(252 * 24 * 60) # Scaled for M1

    # Max Drawdown
    peak = equity_series.expanding(min_periods=1).max()
    drawdown = (equity_series - peak) / peak
    mdd = drawdown.min()

    expectancy = returns.mean()

    return {
        "final_equity": float(equity_series.iloc[-1]),
        "total_return": float((equity_series.iloc[-1] - equity_series.iloc[0]) / equity_series.iloc[0]),
        "win_rate": float(win_rate),
        "sharpe_ratio": float(sharpe),
        "max_drawdown": float(mdd),
        "expectancy": float(expectancy)
    }

def run_backtest(data_path: str, config_path: str, out_path: str):
    # Load config
    with open(config_path, 'r') as f:
        config_full = yaml.safe_load(f)
        active_preset = config_full.get("active_preset", "conservative")
        config = config_full['presets'][active_preset]
        config.update({k: v for k, v in config_full.items() if k != 'presets'})

    # Initialize components
    dl = DataLoader(data_path)
    m1_data = dl.load()
    m5_data = dl.get_resampled("5min")
    h1_data = dl.get_resampled("1H")

    signal = EMAMomentumSignal()
    risk = RiskManager(config)
    execution = BacktestAdapter(
        initial_equity=config.get("min_capital_recommendation", 15000),
        base_spread=0.0001,
        slippage_pct=0.05
    )
    engine = StrategyEngine(signal, risk, execution, config)

    # Execution loop
    equity_history = []
    timestamps = []

    for idx, m5_bar in m5_data.iterrows():
        m1_ticks = m1_data.loc[idx : idx + timedelta(minutes=4)]
        h1_slice = h1_data.loc[:idx]

        for t_idx, m1_tick in m1_ticks.iterrows():
            execution.set_market_state(m1_tick['close'], t_idx)
            engine.run_tick(m1_tick, m5_data.loc[:idx], h1_slice)

            equity_history.append(execution.get_account_equity())
            timestamps.append(t_idx)

    # Compile results
    equity_series = pd.Series(equity_history, index=timestamps)
    metrics = calculate_metrics(equity_series)

    full_output = {
        "metrics": metrics,
        "equity_curve": equity_series.to_dict()
    }

    # Save results
    with open(out_path, 'w') as f:
        json.dump(full_output, f, indent=2)

    print(f"Backtest complete. Final Equity: {execution.get_account_equity():.2f}")
    print(f"Metrics: {json.dumps(metrics, indent=2)}")
    print(f"Results saved to {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--out", default="backtest_results.json")
    args = parser.parse_args()
    run_backtest(args.data, args.config, args.out)
