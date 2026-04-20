from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd


SCAN_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "NFLX",
    "AMD", "INTC", "PLTR", "UBER", "SPY", "QQQ", "IWM",
    "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD"
]

ASSET_LABELS = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "AMZN": "Amazon",
    "META": "Meta",
    "GOOGL": "Alphabet",
    "TSLA": "Tesla",
    "NFLX": "Netflix",
    "AMD": "AMD",
    "INTC": "Intel",
    "PLTR": "Palantir",
    "UBER": "Uber",
    "SPY": "S&P 500 ETF",
    "QQQ": "Nasdaq 100 ETF",
    "IWM": "Russell 2000 ETF",
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "SOL-USD": "Solana",
    "XRP-USD": "XRP",
    "ADA-USD": "Cardano",
}


def safe_pct_change(current: float | None, previous: float | None) -> float:
    if current is None or previous is None or previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100.0


def _clean_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "Close" not in df.columns:
        return pd.DataFrame(columns=["Close"])

    out = df.copy()
    out = out.dropna(subset=["Close"])
    out = out.sort_index()
    return out[["Close"]]


def _price_at_or_before(df: pd.DataFrame, target_time) -> float | None:
    if df.empty:
        return None

    eligible = df[df.index <= target_time]
    if eligible.empty:
        return None
    return float(eligible["Close"].iloc[-1])


def _consistency_score(close: pd.Series, bars: int = 8) -> float:
    if close is None or len(close) < bars + 1:
        return 0.0

    recent = close.tail(bars + 1).pct_change().dropna()
    if recent.empty:
        return 0.0

    positive = (recent > 0).sum()
    negative = (recent < 0).sum()
    dominant = max(positive, negative)
    return float(dominant / len(recent))


def _volatility_value(close: pd.Series, bars: int = 24) -> float:
    if close is None or len(close) < bars + 1:
        return 0.0

    recent = close.tail(bars).pct_change().dropna() * 100.0
    if recent.empty:
        return 0.0

    swing = float(recent.abs().mean())
    return swing


def classify_volatility(volatility_pct: float) -> str:
    if volatility_pct < 0.35:
        return "Low volatility 🟢"
    if volatility_pct < 0.90:
        return "Medium volatility 🟡"
    return "High volatility 🔴"


def classify_trend(change_1h: float, change_24h: float, consistency: float) -> str:
    if change_1h > 0.35 and change_24h > 0.80 and consistency >= 0.60:
        return "Bullish 📈"
    if change_1h < -0.35 and change_24h < -0.80 and consistency >= 0.60:
        return "Bearish 📉"
    return "Neutral ➖"


def suggestion_tag(score: float, change_1h: float, change_24h: float, volatility_pct: float) -> str:
    if change_1h > 0.8 and score > 0.90:
        return "High activity ⚡"
    if volatility_pct < 0.60 and change_24h > 0.5:
        return "Stable growth 🟢"
    return "Momentum rising 📈"


def compute_suggestion_score(
    change_1h: float,
    change_24h: float,
    momentum_acceleration: float,
    consistency: float,
    volatility_pct: float,
) -> float:
    short_component = np.clip(change_1h / 2.5, -1.0, 1.0)
    medium_component = np.clip(change_24h / 6.0, -1.0, 1.0)
    momentum_component = np.clip(momentum_acceleration / 1.5, -1.0, 1.0)
    consistency_component = np.clip((consistency - 0.5) * 2.0, -1.0, 1.0)
    volatility_penalty = np.clip(volatility_pct / 2.0, 0.0, 1.0)

    score = (
        0.35 * short_component
        + 0.30 * medium_component
        + 0.20 * momentum_component
        + 0.15 * consistency_component
        - 0.20 * volatility_penalty
    )
    return float(score)


def analyze_market_frame(df: pd.DataFrame) -> dict[str, Any]:
    df = _clean_frame(df)
    if df.empty:
        return {
            "latest_price": None,
            "change_1h": 0.0,
            "change_24h": 0.0,
            "change_5m": 0.0,
            "consistency": 0.0,
            "trend": "Neutral ➖",
            "volatility_pct": 0.0,
            "volatility": "Low volatility 🟢",
            "suggestion_score": 0.0,
            "suggestion_tag": "Stable growth 🟢",
        }

    now = df.index[-1]
    latest_price = float(df["Close"].iloc[-1])

    price_5m = _price_at_or_before(df, now - timedelta(minutes=5))
    price_1h = _price_at_or_before(df, now - timedelta(hours=1))
    price_24h = _price_at_or_before(df, now - timedelta(hours=24))

    change_5m = safe_pct_change(latest_price, price_5m)
    change_1h = safe_pct_change(latest_price, price_1h)
    change_24h = safe_pct_change(latest_price, price_24h)

    consistency = _consistency_score(df["Close"], bars=8)
    volatility_pct = _volatility_value(df["Close"], bars=24)
    volatility = classify_volatility(volatility_pct)
    trend = classify_trend(change_1h, change_24h, consistency)

    hourly_from_daily = change_24h / 24.0 if change_24h != 0 else 0.0
    momentum_acceleration = change_1h - hourly_from_daily

    score = compute_suggestion_score(
        change_1h=change_1h,
        change_24h=change_24h,
        momentum_acceleration=momentum_acceleration,
        consistency=consistency,
        volatility_pct=volatility_pct,
    )

    tag = suggestion_tag(score, change_1h, change_24h, volatility_pct)

    return {
        "latest_price": latest_price,
        "change_1h": change_1h,
        "change_24h": change_24h,
        "change_5m": change_5m,
        "consistency": consistency,
        "trend": trend,
        "volatility_pct": volatility_pct,
        "volatility": volatility,
        "suggestion_score": score,
        "suggestion_tag": tag,
    }