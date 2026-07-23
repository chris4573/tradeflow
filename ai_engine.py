from __future__ import annotations

from typing import Any


def clamp(value: float, low: float, high: float) -> float:
    """Keep a number between a minimum and maximum value."""
    return max(low, min(high, value))


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float safely."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def pct_change(current: float, previous: float) -> float:
    """Calculate percentage change safely."""
    current = safe_float(current)
    previous = safe_float(previous)

    if previous == 0:
        return 0.0

    return ((current - previous) / previous) * 100.0


def classify_trade_idea(score: float) -> str:
    """Turn a numeric score into a readable trade label."""
    score = safe_float(score)

    if score >= 70:
        return "Strong Buy"
    if score >= 55:
        return "Buy / Momentum"
    if score >= 40:
        return "Watch"
    return "Avoid / Weak"


def build_reason_list(
    change_1h: float,
    change_24h: float,
    change_7d: float,
    momentum_accel: float,
    volatility_pct: float,
    consistency_score: float,
    volume_score: float,
) -> list[str]:
    """Build a short list explaining the score."""
    reasons: list[str] = []

    if change_1h > 0:
        reasons.append("Short-term momentum is positive")

    if change_24h > 0:
        reasons.append("The 24-hour trend is positive")

    if change_7d > 0:
        reasons.append("The 7-day trend is positive")

    if momentum_accel > 0:
        reasons.append("Momentum is accelerating")

    if volatility_pct < 1.2:
        reasons.append("Volatility is relatively controlled")

    if consistency_score > 0.55:
        reasons.append("Price action looks consistent")

    if volume_score > 0.15:
        reasons.append("Recent trading volume is stronger")

    if not reasons:
        reasons.append("The setup looks weak right now")

    return reasons[:4]


def score_trade_idea(
    change_1h: float = 0.0,
    change_24h: float = 0.0,
    change_7d: float = 0.0,
    volatility_pct: float = 0.0,
    consistency_score: float = 0.0,
    volume_score: float = 0.0,
) -> dict[str, Any]:
    """
    Score a possible trade idea from 0 to 100.

    All arguments have defaults so the function will not crash if
    one value is missing from app.py.
    """

    change_1h = safe_float(change_1h)
    change_24h = safe_float(change_24h)
    change_7d = safe_float(change_7d)
    volatility_pct = max(0.0, safe_float(volatility_pct))
    consistency_score = clamp(safe_float(consistency_score), 0.0, 1.0)
    volume_score = clamp(safe_float(volume_score), -1.0, 1.0)

    momentum_accel = change_1h - (change_24h / 24.0)

    trend_score = (
        change_1h * 10.0
        + change_24h * 3.2
        + change_7d * 1.8
    )

    acceleration_score = momentum_accel * 12.0
    consistency_bonus = consistency_score * 22.0
    volume_bonus = volume_score * 18.0
    volatility_penalty = max(0.0, volatility_pct - 0.7) * 18.0

    raw_score = (
        50.0
        + trend_score
        + acceleration_score
        + consistency_bonus
        + volume_bonus
        - volatility_penalty
    )

    score = clamp(raw_score, 0.0, 100.0)
    confidence = int(round(clamp(score, 1.0, 99.0)))

    reasons = build_reason_list(
        change_1h=change_1h,
        change_24h=change_24h,
        change_7d=change_7d,
        momentum_accel=momentum_accel,
        volatility_pct=volatility_pct,
        consistency_score=consistency_score,
        volume_score=volume_score,
    )

    return {
        "score": round(score, 2),
        "confidence": confidence,
        "label": classify_trade_idea(score),
        "momentum_accel": round(momentum_accel, 3),
        "reasons": reasons,
    }