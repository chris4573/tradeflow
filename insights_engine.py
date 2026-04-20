from __future__ import annotations

from typing import Any


ASSET_CATEGORIES = {
    "AAPL": "Tech stocks",
    "MSFT": "Tech stocks",
    "NVDA": "Tech stocks",
    "GOOGL": "Tech stocks",
    "META": "Tech stocks",
    "AMZN": "Tech stocks",
    "TSLA": "EV / growth stocks",
    "AMD": "Tech stocks",
    "INTC": "Tech stocks",
    "PLTR": "Tech stocks",
    "NFLX": "Media / tech",
    "UBER": "Transport / tech",
    "SPY": "ETF",
    "QQQ": "ETF",
    "IWM": "ETF",
    "BTC-USD": "Crypto",
    "ETH-USD": "Crypto",
    "SOL-USD": "Crypto",
    "XRP-USD": "Crypto",
    "ADA-USD": "Crypto",
}


def safe_pct_change(current: float | None, previous: float | None) -> float:
    if current is None or previous is None or previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100.0


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def get_asset_category(ticker: str) -> str:
    return ASSET_CATEGORIES.get(ticker, "Other")


def get_asset_category_mix_from_allocations(allocation_rows: list[dict[str, Any]]) -> dict[str, float]:
    category_totals: dict[str, float] = {}

    for row in allocation_rows:
        ticker = row.get("Ticker", "")
        percent = float(row.get("Percent", 0))
        category = get_asset_category(ticker)
        category_totals[category] = category_totals.get(category, 0.0) + percent

    return dict(sorted(category_totals.items(), key=lambda item: item[1], reverse=True))


def best_category_label(allocation_rows: list[dict[str, Any]]) -> str:
    mix = get_asset_category_mix_from_allocations(allocation_rows)
    if not mix:
        return "No dominant sector yet"
    top_category = next(iter(mix))
    return f"Strong performance in {top_category.lower()} 🔥"


def volatility_level_from_pct(volatility_pct: float) -> str:
    if volatility_pct < 0.35:
        return "Low volatility 🟢"
    if volatility_pct < 0.90:
        return "Medium volatility 🟡"
    return "High volatility 🔴"


def trend_label_from_history(history_rows: list[dict[str, Any]]) -> str:
    if len(history_rows) < 2:
        return "Flat / limited history ➖"

    first_value = float(history_rows[0].get("value", 0))
    last_value = float(history_rows[-1].get("value", 0))

    if first_value <= 0:
        return "Flat / limited history ➖"

    pct = ((last_value - first_value) / first_value) * 100.0

    if pct > 1.0:
        return "Portfolio trend up 📈"
    if pct < -1.0:
        return "Portfolio trend down 📉"
    return "Portfolio trend neutral ➖"


def compare_asset_strength(left_metrics: dict[str, Any], right_metrics: dict[str, Any]) -> str:
    left_score = (
        float(left_metrics.get("change_1h", 0)) * 0.35
        + float(left_metrics.get("change_24h", 0)) * 0.35
        + float(left_metrics.get("change_7d", 0)) * 0.30
        - float(left_metrics.get("volatility_pct", 0)) * 0.20
    )

    right_score = (
        float(right_metrics.get("change_1h", 0)) * 0.35
        + float(right_metrics.get("change_24h", 0)) * 0.35
        + float(right_metrics.get("change_7d", 0)) * 0.30
        - float(right_metrics.get("volatility_pct", 0)) * 0.20
    )

    if left_score > right_score + 0.15:
        return "Left asset performing better recently 🏆"
    if right_score > left_score + 0.15:
        return "Right asset performing better recently 🏆"
    return "Both assets are performing similarly recently 🤝"


def performance_score(
    total_change_pct: float,
    win_rate_pct: float,
    consistency_ratio: float,
) -> int:
    score = (
        50
        + total_change_pct * 4.0
        + (win_rate_pct - 50.0) * 0.5
        + (consistency_ratio * 20.0)
    )
    return int(round(clamp(score, 0, 100)))


def trade_win_rate(current_sales: list[dict[str, Any]]) -> tuple[int, int, float]:
    if not current_sales:
        return 0, 0, 0.0

    wins = 0
    losses = 0

    for sale in current_sales:
        pl = float(sale.get("Realized P/L", 0))
        if pl >= 0:
            wins += 1
        else:
            losses += 1

    total = wins + losses
    win_rate = (wins / total) * 100.0 if total else 0.0
    return wins, losses, win_rate


def best_and_worst_assets_from_portfolio_rows(portfolio_rows: list[dict[str, Any]]) -> tuple[str, str]:
    if not portfolio_rows:
        return "No data", "No data"

    sorted_rows = sorted(
        portfolio_rows,
        key=lambda row: float(row.get("Unrealized P/L", 0)),
        reverse=True,
    )

    best = sorted_rows[0]
    worst = sorted_rows[-1]

    best_text = f"{best.get('Ticker', 'Unknown')} ({float(best.get('Unrealized P/L', 0)):+.2f}$)"
    worst_text = f"{worst.get('Ticker', 'Unknown')} ({float(worst.get('Unrealized P/L', 0)):+.2f}$)"
    return best_text, worst_text


def portfolio_change_summary(history_rows: list[dict[str, Any]], lookback_points: int) -> tuple[float, float]:
    if len(history_rows) < 2:
        return 0.0, 0.0

    last_value = float(history_rows[-1].get("value", 0))
    ref_index = max(0, len(history_rows) - 1 - lookback_points)
    ref_value = float(history_rows[ref_index].get("value", 0))

    if ref_value <= 0:
        return 0.0, 0.0

    value_change = last_value - ref_value
    pct_change = (value_change / ref_value) * 100.0
    return value_change, pct_change


def consistency_ratio_from_history(history_rows: list[dict[str, Any]]) -> float:
    if len(history_rows) < 3:
        return 0.0

    positives = 0
    negatives = 0

    for i in range(1, len(history_rows)):
        prev_val = float(history_rows[i - 1].get("value", 0))
        curr_val = float(history_rows[i].get("value", 0))
        if curr_val > prev_val:
            positives += 1
        elif curr_val < prev_val:
            negatives += 1

    total = positives + negatives
    if total == 0:
        return 0.0

    return max(positives, negatives) / total


def risk_level_from_behavior(
    allocation_rows: list[dict[str, Any]],
    current_sales: list[dict[str, Any]],
    portfolio_rows: list[dict[str, Any]],
) -> str:
    if not allocation_rows and not current_sales and not portfolio_rows:
        return "Low risk 🟢"

    concentration = 0.0
    if allocation_rows:
        concentration = max(float(row.get("Percent", 0)) for row in allocation_rows)

    trade_count = len(current_sales)
    avg_abs_pl = 0.0
    if portfolio_rows:
        values = [abs(float(row.get("Unrealized P/L", 0))) for row in portfolio_rows]
        avg_abs_pl = sum(values) / len(values) if values else 0.0

    if concentration >= 65 or trade_count >= 15 or avg_abs_pl >= 25:
        return "High risk 🔴"
    if concentration >= 40 or trade_count >= 6 or avg_abs_pl >= 10:
        return "Medium risk 🟡"
    return "Low risk 🟢"