import os
import json
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import ExecutionAdapter

class OandaV20Adapter(ExecutionAdapter):
    """
    OANDA v20 REST API execution adapter using standard requests.
    Handles virtual-leg tracking and netting/hedging differences.
    """
    def __init__(self, api_key: str, account_id: str, sandbox: bool = True):
        self.api_key = api_key
        self.account_id = account_id
        self.sandbox = sandbox
        self.base_url = "https://api-fxpractice.oanda.com" if sandbox else "https://api-fxtrade.oanda.com"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.virtual_legs: List[Dict[str, Any]] = []

    def place_order(self, pair: str, side: str, lot: float, client_id: str) -> Optional[Dict[str, Any]]:
        units = int(lot * 100000)
        if side == "SHORT":
            units = -units

        data = {
            "order": {
                "units": str(units),
                "instrument": pair,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT",
                "clientExtensions": {
                    "id": client_id,
                    "tag": "rescue_path_b"
                }
            }
        }

        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/orders"
            resp = requests.post(url, headers=self.headers, json=data, timeout=10)
            resp.raise_for_status()
            res_json = resp.json()

            fill = res_json.get("orderFillTransaction")
            if fill:
                fill_details = {
                    "pair": pair,
                    "side": side,
                    "lot": lot,
                    "fill_price": float(fill["price"]),
                    "client_id": client_id,
                    "timestamp": datetime.utcnow(),
                    "id": fill["id"]
                }
                self.virtual_legs.append(fill_details)
                return fill_details
        except Exception as e:
            print(f"OANDA Order Error: {e}")
        return None

    def flatten_all(self, pair: str) -> bool:
        """Close all positions for the pair."""
        try:
            # First, cancel pending orders
            # Then close the position
            url = f"{self.base_url}/v3/accounts/{self.account_id}/positions/{pair}/close"
            # OANDA requires specifying which side to close if both exist, but we are single-side
            data = {"longUnits": "ALL"} if any(l['side'] == "LONG" for l in self.virtual_legs) else {"shortUnits": "ALL"}
            resp = requests.put(url, headers=self.headers, json=data, timeout=10)
            resp.raise_for_status()
            self.virtual_legs = []
            return True
        except Exception as e:
            print(f"OANDA Flatten Error: {e}")
        return False

    def get_market_price(self, pair: str) -> float:
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing?instruments={pair}"
            resp = requests.get(url, headers=self.headers, timeout=5)
            resp.raise_for_status()
            prices = resp.json().get("prices", [])
            if prices:
                bid = float(prices[0]["bids"][0]["price"])
                ask = float(prices[0]["asks"][0]["price"])
                return (bid + ask) / 2
        except Exception as e:
            print(f"OANDA Price Error: {e}")
        return 0.0

    def get_account_equity(self) -> float:
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/summary"
            resp = requests.get(url, headers=self.headers, timeout=5)
            resp.raise_for_status()
            summary = resp.json().get("account", {})
            return float(summary.get("NAV", 0.0))
        except Exception as e:
            print(f"OANDA Equity Error: {e}")
        return 0.0

    def get_open_positions(self) -> List[Dict[str, Any]]:
        return self.virtual_legs

    def get_avg_spread(self, pair: str) -> float:
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing?instruments={pair}"
            resp = requests.get(url, headers=self.headers, timeout=5)
            resp.raise_for_status()
            prices = resp.json().get("prices", [])
            if prices:
                bid = float(prices[0]["bids"][0]["price"])
                ask = float(prices[0]["asks"][0]["price"])
                return ask - bid
        except Exception as e:
            pass
        return 0.00015

    def get_candles(self, pair: str, granularity: str, count: int = 50) -> Optional[List[Dict[str, Any]]]:
        """Fetch historical candles."""
        try:
            url = f"{self.base_url}/v3/instruments/{pair}/candles"
            params = {"granularity": granularity, "count": count}
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json().get("candles", [])
        except Exception as e:
            print(f"OANDA Candle Error: {e}")
        return None
