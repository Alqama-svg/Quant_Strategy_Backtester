"""
Helper functions for QuantX V4.9 Intraday Mean-Reversion Backtest
"""

import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

def ensure_dir(path: str):
    """Create directory if it doesn’t exist."""
    os.makedirs(path, exist_ok=True)

def save_json(data: dict, path: str):
    """Save dictionary as JSON file."""
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def load_json(path: str):
    """Load JSON configuration file."""
    with open(path, "r") as f:
        return json.load(f)

def load_equity_curve(file_path: str) -> pd.Series:
    """Load and return equity curve as a Pandas Series."""
    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    return df.squeeze()

def compute_daily_returns(equity_curve: pd.Series) -> pd.Series:
    """Compute daily returns from equity curve."""
    returns = equity_curve.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    return returns

def plot_equity_curve(equity_curve: pd.Series, output_path: str = None):
    """Plot equity curve and optionally save."""
    plt.figure(figsize=(10, 5))
    plt.plot(equity_curve.index, equity_curve.values, label="Equity", linewidth=2)
    plt.title("QuantX V4.9 — Equity Curve")
    plt.xlabel("Date")
    plt.ylabel("Equity ($)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    if output_path:
        plt.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close()

def format_timestamp(dt: datetime) -> str:
    """Return formatted timestamp as string."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def safe_div(a, b):
    """Safe division avoiding division by zero."""
    return a / b if b != 0 else np.nan