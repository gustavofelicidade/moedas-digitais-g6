"""Deterministic, LangGraph-independent behavioral and temporal wallet features.

All metrics in this module describe observable historical transaction patterns.
Automation indicators are strictly behavioral proxies (cadence, burstiness,
circadian dispersion) and never prove AI authorship or fraud.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

CANONICAL_ALIASES = {
    "tx_hash": ("TxHash", "tx_hash", "txhash", "hash"),
    "timestamp": ("TimeStamp", "timestamp", "block_timestamp", "time"),
    "wallet_from": ("From", "wallet_from", "from", "sender"),
    "wallet_to": ("To", "wallet_to", "to", "receiver"),
    "amount": ("Value", "amount", "value"),
    "is_error": ("isError", "is_error", "iserror", "error"),
}


def _resolve_col(df: pd.DataFrame, canonical: str) -> str | None:
    for candidate in CANONICAL_ALIASES.get(canonical, (canonical,)):
        if candidate in df.columns:
            return candidate
    return None


def _shannon_entropy_normalized(counts: np.ndarray, n_bins: int = 24) -> float | None:
    total = counts.sum()
    if total <= 0 or n_bins <= 1:
        return None
    probs = counts[counts > 0] / total
    entropy = -float(np.sum(probs * np.log(probs)))
    return round(entropy / math.log(n_bins), 4)


def compute_wallet_features(
    tx: pd.DataFrame,
    wallet_from: str,
    wallet_to: str,
    *,
    source_rows: int = 0,
    as_of: str | None = None,
    min_error_obs: int = 20,
    recipient_seen_override: bool | None = None,
) -> dict[str, Any]:
    """Compute volume, counterparty concentration, error rate, and temporal cadence features."""
    wallet_from_norm = str(wallet_from).strip().lower()
    wallet_to_norm = str(wallet_to).strip().lower()

    tx_col = _resolve_col(tx, "tx_hash")
    ts_col = _resolve_col(tx, "timestamp")
    to_col = _resolve_col(tx, "wallet_to")
    val_col = _resolve_col(tx, "amount")
    err_col = _resolve_col(tx, "is_error")

    n_rows = int(len(tx))
    if n_rows == 0:
        return {
            "wallet_from": wallet_from_norm,
            "wallet_to": wallet_to_norm,
            "source_rows": int(source_rows),
            "as_of_applied": as_of,
            "n_rows": 0,
            "n_unique_tx_hashes": 0,
            "duplicate_row_ratio": 0.0,
            "n_receivers": 0,
            "recipient_seen": bool(recipient_seen_override) if recipient_seen_override is not None else False,
            "recipient_tx_count": 0,
            "recipient_share": 0.0,
            "new_recipient_ratio": None,
            "top_receiver_share": None,
            "recipient_hhi": None,
            "n_active_days": 0,
            "window_days": None,
            "valid_error_observations": 0,
            "error_count": 0,
            "historical_error_rate": None,
            "error_rate_reliable": False,
            "median_amount": None,
            "p75_amount": None,
            "p95_amount": None,
            "max_amount": None,
            "iqr_amount": None,
            "total_amount": None,
            "first_seen": None,
            "last_seen": None,
            "temporal_cadence": {
                "median_inter_tx_seconds": None,
                "min_inter_tx_seconds": None,
                "p10_inter_tx_seconds": None,
                "rapid_fire_ratio": None,
                "burstiness_index": None,
                "active_hours_utc": 0,
                "hourly_entropy_normalized": None,
                "tx_per_active_day": None,
            },
            "automation_proxy": {
                "flagged": False,
                "signals": [],
                "disclaimer": "behavioral_proxy_not_ai_proof",
            },
        }

    # Deduplicate by TxHash when available for transaction-level metrics
    if tx_col is not None:
        unique_tx = tx.drop_duplicates(subset=[tx_col]).copy()
        n_unique_hashes = int(tx[tx_col].nunique(dropna=True))
    else:
        unique_tx = tx.copy()
        n_unique_hashes = n_rows

    dup_ratio = round(max(0.0, 1.0 - (n_unique_hashes / n_rows)), 4) if n_rows > 0 else 0.0

    # Value metrics (computed over tx rows to preserve compatibility with existing prototype)
    values = pd.to_numeric(tx[val_col], errors="coerce").dropna() if val_col else pd.Series(dtype=float)
    if not values.empty:
        p25_val = float(values.quantile(0.25))
        p75_val = float(values.quantile(0.75))
        median_amount = float(values.median())
        p95_amount = float(values.quantile(0.95))
        max_amount = float(values.max())
        iqr_amount = float(p75_val - p25_val)
        total_amount = float(values.sum())
    else:
        median_amount = p75_val = p95_amount = max_amount = iqr_amount = total_amount = None

    # Error metrics with explicit denominator and minimum observation check
    errors = pd.to_numeric(tx[err_col], errors="coerce").dropna() if err_col else pd.Series(dtype=float)
    valid_err_obs = int(len(errors))
    error_count = int((errors > 0).sum()) if valid_err_obs > 0 else 0
    historical_error_rate = float(errors.mean()) if valid_err_obs > 0 else None
    error_rate_reliable = valid_err_obs >= min_error_obs

    # Counterparty & destination concentration metrics
    if to_col is not None:
        receivers_series = tx[to_col].dropna().astype(str).str.lower()
        n_receivers = int(receivers_series.nunique())
        recipient_tx_count = int((receivers_series == wallet_to_norm).sum())
        recipient_seen = (
            bool(recipient_seen_override)
            if recipient_seen_override is not None
            else (recipient_tx_count > 0)
        )
        recipient_share = round(recipient_tx_count / len(receivers_series), 4) if len(receivers_series) > 0 else 0.0
        new_recipient_ratio = round(n_receivers / len(receivers_series), 4) if len(receivers_series) > 0 else None
        if len(receivers_series) > 0:
            shares = receivers_series.value_counts(normalize=True)
            top_receiver_share = round(float(shares.iloc[0]), 4)
            recipient_hhi = round(float((shares ** 2).sum()), 4)
        else:
            top_receiver_share = None
            recipient_hhi = None
    else:
        n_receivers = 0
        recipient_tx_count = 0
        recipient_seen = bool(recipient_seen_override) if recipient_seen_override is not None else False
        recipient_share = 0.0
        new_recipient_ratio = None
        top_receiver_share = None
        recipient_hhi = None

    # Temporal & automation proxy metrics
    if ts_col is not None:
        raw_ts = tx[ts_col]
        num_ts = pd.to_numeric(raw_ts, errors="coerce")
        if num_ts.notna().mean() > 0.8:
            dates = pd.to_datetime(num_ts, unit="s", utc=True, errors="coerce")
        else:
            dates = pd.to_datetime(raw_ts, utc=True, errors="coerce")
        valid_dates = dates.dropna()
    else:
        valid_dates = pd.Series(dtype="datetime64[ns, UTC]")

    if not valid_dates.empty:
        first_seen_dt = valid_dates.min()
        last_seen_dt = valid_dates.max()
        first_seen = first_seen_dt.isoformat()
        last_seen = last_seen_dt.isoformat()
        n_active_days = int(valid_dates.dt.date.nunique())
        window_days = round(max(0.0, (last_seen_dt - first_seen_dt).total_seconds() / 86400.0), 2)

        # Sort unique transaction timestamps for inter-arrival cadence
        if tx_col is not None and ts_col is not None:
            u_num_ts = pd.to_numeric(unique_tx[ts_col], errors="coerce")
            if u_num_ts.notna().mean() > 0.8:
                u_dates = pd.to_datetime(u_num_ts, unit="s", utc=True, errors="coerce").dropna().sort_values()
            else:
                u_dates = pd.to_datetime(unique_tx[ts_col], utc=True, errors="coerce").dropna().sort_values()
        else:
            u_dates = valid_dates.sort_values()

        hour_counts = u_dates.dt.hour.value_counts().reindex(range(24), fill_value=0).to_numpy()
        active_hours_utc = int((hour_counts > 0).sum())
        hourly_entropy = _shannon_entropy_normalized(hour_counts, n_bins=24)
        tx_per_active_day = round(len(u_dates) / max(1, n_active_days), 2)

        if len(u_dates) >= 2:
            deltas = u_dates.diff().dt.total_seconds().dropna()
            # Filter strictly non-negative deltas
            deltas = deltas[deltas >= 0]
            if not deltas.empty:
                median_dt = round(float(deltas.median()), 2)
                min_dt = round(float(deltas.min()), 2)
                p10_dt = round(float(deltas.quantile(0.10)), 2)
                rapid_fire_ratio = round(float((deltas <= 60.0).mean()), 4)
                mean_dt = float(deltas.mean())
                std_dt = float(deltas.std(ddof=0))
                burstiness = (
                    round((std_dt - mean_dt) / (std_dt + mean_dt), 4)
                    if (std_dt + mean_dt) > 0
                    else 0.0
                )
            else:
                median_dt = min_dt = p10_dt = rapid_fire_ratio = burstiness = None
        else:
            median_dt = min_dt = p10_dt = rapid_fire_ratio = burstiness = None
    else:
        first_seen = last_seen = window_days = None
        n_active_days = 0
        active_hours_utc = 0
        hourly_entropy = None
        tx_per_active_day = None
        median_dt = min_dt = p10_dt = rapid_fire_ratio = burstiness = None

    # Behavioral automation proxy evaluation (requires >= 20 unique transactions)
    automation_signals: list[str] = []
    if n_unique_hashes >= 20:
        if rapid_fire_ratio is not None and rapid_fire_ratio >= 0.30:
            automation_signals.append(
                f"Alta cadência sub-minuto ({rapid_fire_ratio:.1%} das transações com Δt <= 60s)"
            )
        if hourly_entropy is not None and hourly_entropy >= 0.88 and active_hours_utc >= 20:
            automation_signals.append(
                f"Atividade contínua 24h (entropia horária {hourly_entropy:.2f} em {active_hours_utc}/24h UTC)"
            )
        if tx_per_active_day is not None and tx_per_active_day >= 50.0:
            automation_signals.append(
                f"Volume diário elevado ({tx_per_active_day:.1f} txs/dia ativo)"
            )

    return {
        "wallet_from": wallet_from_norm,
        "wallet_to": wallet_to_norm,
        "source_rows": int(source_rows),
        "as_of_applied": as_of,
        "n_rows": n_rows,
        "n_unique_tx_hashes": n_unique_hashes,
        "duplicate_row_ratio": dup_ratio,
        "n_receivers": n_receivers,
        "recipient_seen": recipient_seen,
        "recipient_tx_count": recipient_tx_count,
        "recipient_share": recipient_share,
        "new_recipient_ratio": new_recipient_ratio,
        "top_receiver_share": top_receiver_share,
        "recipient_hhi": recipient_hhi,
        "n_active_days": n_active_days,
        "window_days": window_days,
        "valid_error_observations": valid_err_obs,
        "error_count": error_count,
        "historical_error_rate": historical_error_rate,
        "error_rate_reliable": error_rate_reliable,
        "median_amount": median_amount,
        "p75_amount": p75_val,
        "p95_amount": p95_amount,
        "max_amount": max_amount,
        "iqr_amount": iqr_amount,
        "total_amount": total_amount,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "temporal_cadence": {
            "median_inter_tx_seconds": median_dt,
            "min_inter_tx_seconds": min_dt,
            "p10_inter_tx_seconds": p10_dt,
            "rapid_fire_ratio": rapid_fire_ratio,
            "burstiness_index": burstiness,
            "active_hours_utc": active_hours_utc,
            "hourly_entropy_normalized": hourly_entropy,
            "tx_per_active_day": tx_per_active_day,
        },
        "automation_proxy": {
            "flagged": len(automation_signals) > 0,
            "signals": automation_signals,
            "disclaimer": "behavioral_proxy_not_ai_proof",
        },
    }
