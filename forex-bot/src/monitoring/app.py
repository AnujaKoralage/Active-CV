from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, Any, List
import os

app = FastAPI()

# Global state to be updated by the engine
trading_state = {
    "open_positions": [],
    "equity": 0.0,
    "pnl": 0.0,
    "adds_used": 0,
    "max_adds": 0,
    "adx_h1": 0.0,
    "is_gated": False,
    "alerts": []
}

@app.get("/api/status")
async def get_status():
    return trading_state

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    with open(os.path.join(os.path.dirname(__file__), "index.html"), "r") as f:
        return f.read()

def update_state(data: Dict[str, Any]):
    global trading_state
    trading_state.update(data)
