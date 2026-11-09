"""Explainable stablecoin peg monitoring signals; these are not fraud labels."""

import pandas as pd


def build_peg_monitor(
    prices: pd.DataFrame,
    events: pd.DataFrame,
    transfers: pd.DataFrame | None = None,
    *,
    deviation_threshold: float = 0.02,
) -> pd.DataFrame:
    """Join daily price/transfer context and flag material intraday peg deviation."""
    if not 0 < deviation_threshold < 1:
        raise ValueError("deviation_threshold deve estar entre 0 e 1")
    required_prices = {"token", "date", "high", "low", "close"}
    required_events = {"token", "date", "event", "type"}
    if missing := required_prices - set(prices.columns):
        raise ValueError(f"Colunas de preço ausentes: {', '.join(sorted(missing))}")
    if missing := required_events - set(events.columns):
        raise ValueError(f"Colunas de evento ausentes: {', '.join(sorted(missing))}")

    result = prices.loc[prices["token"].ne("WLUNA")].copy()
    for column in ["high", "low", "close"]:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result["low_deviation"] = (1.0 - result["low"]).clip(lower=0)
    result["high_deviation"] = (result["high"] - 1.0).clip(lower=0)
    result["peg_deviation"] = result[["low_deviation", "high_deviation"]].max(axis=1)
    result["peg_alert"] = result["peg_deviation"].ge(deviation_threshold)
    result["status"] = result["peg_alert"].map({True: "REVIEW_PEG_DEVIATION", False: "NO_PEG_ALERT"})

    event_summary = events.groupby(["token", "date"], as_index=False).agg(
        event_count=("event", "size"),
        event_titles=("event", lambda values: " | ".join(map(str, values))),
    )
    result = result.merge(event_summary, on=["token", "date"], how="left")
    result["event_count"] = result["event_count"].fillna(0).astype(int)
    result["event_titles"] = result["event_titles"].fillna("")

    if transfers is not None:
        required_transfers = {"token", "date", "transfer_count", "transfer_amount"}
        if missing := required_transfers - set(transfers.columns):
            raise ValueError(f"Colunas de transferência ausentes: {', '.join(sorted(missing))}")
        result = result.merge(transfers, on=["token", "date"], how="left")
        result["transfer_count"] = result["transfer_count"].fillna(0).astype("int64")
        result["transfer_amount"] = result["transfer_amount"].fillna(0.0)
    else:
        result["transfer_count"] = pd.NA
        result["transfer_amount"] = pd.NA
    result["threshold"] = deviation_threshold
    return result.sort_values(["date", "token"], ignore_index=True)
