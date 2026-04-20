from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any


def load_alert_store(path: str) -> dict[str, Any]:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"users": {}}


def save_alert_store(path: str, store: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)


def _ensure_user(store: dict[str, Any], username: str) -> None:
    if "users" not in store:
        store["users"] = {}

    if username not in store["users"]:
        store["users"][username] = {
            "snapshots": {},
            "events": []
        }


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _event_exists_recently(
    events: list[dict[str, Any]],
    ticker: str,
    kind: str,
    now: datetime,
    minutes: int = 4,
) -> bool:
    threshold = now - timedelta(minutes=minutes)
    for event in reversed(events[-30:]):
        if event.get("ticker") != ticker or event.get("kind") != kind:
            continue
        try:
            event_time = _parse_ts(event["timestamp"])
        except Exception:
            continue
        if event_time >= threshold:
            return True
    return False


def _latest_snapshot_before(
    snapshots: list[dict[str, Any]],
    now: datetime,
    minutes_back: int,
) -> dict[str, Any] | None:
    target = now - timedelta(minutes=minutes_back)
    eligible = [s for s in snapshots if _parse_ts(s["timestamp"]) <= target]
    if not eligible:
        return None
    return eligible[-1]


def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100.0


def update_price_and_generate_alerts(
    store: dict[str, Any],
    username: str,
    ticker: str,
    price: float,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    _ensure_user(store, username)

    if now is None:
        now = datetime.utcnow()

    user_block = store["users"][username]
    snapshots = user_block["snapshots"].setdefault(ticker, [])
    events = user_block["events"]

    snapshots.append({
        "timestamp": now.isoformat(),
        "price": float(price),
    })

    cutoff = now - timedelta(minutes=15)
    snapshots[:] = [s for s in snapshots if _parse_ts(s["timestamp"]) >= cutoff]

    new_events: list[dict[str, Any]] = []

    snap_1m = _latest_snapshot_before(snapshots, now, 1)
    snap_2m = _latest_snapshot_before(snapshots, now, 2)
    snap_5m = _latest_snapshot_before(snapshots, now, 5)

    checks = []

    if snap_1m:
        change_1m = _pct_change(price, float(snap_1m["price"]))
        if change_1m >= 0.5:
            checks.append(("slight_rise", "Slight rise 📈", change_1m))
        elif change_1m <= -0.5:
            checks.append(("slight_drop", "Slight drop 📉", change_1m))

    if snap_5m:
        change_5m = _pct_change(price, float(snap_5m["price"]))
        if change_5m >= 1.5:
            checks.append(("strong_upward", "Strong upward movement ⚡", change_5m))
        elif change_5m <= -1.5:
            checks.append(("sharp_decline", "Sharp decline ⚠️", change_5m))

    if snap_2m:
        change_short = _pct_change(price, float(snap_2m["price"]))
        if change_short >= 1.0:
            checks.append(("spike_up", "Spike up 📈", change_short))
        elif change_short <= -1.0:
            checks.append(("drop_down", "Drop down 📉", change_short))

    for kind, message, pct in checks:
        if _event_exists_recently(events, ticker, kind, now):
            continue

        event = {
            "ticker": ticker,
            "kind": kind,
            "message": message,
            "pct_change": round(float(pct), 3),
            "timestamp": now.isoformat(),
        }
        events.append(event)
        new_events.append(event)

    user_block["events"] = events[-100:]
    return new_events


def get_recent_events(store: dict[str, Any], username: str, limit: int = 12) -> list[dict[str, Any]]:
    _ensure_user(store, username)
    events = store["users"][username]["events"]
    return list(reversed(events[-limit:]))