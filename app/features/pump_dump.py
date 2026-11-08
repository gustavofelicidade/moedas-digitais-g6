"""Causal trade-window features and pump labels from La Morgia et al. (2020)."""

import pandas as pd

from app.ingestion.pump_dump import MARKET


# Fast and best-F1 configurations reported in section IV-C.
WINDOW_MINUTES = {5: 50, 25: 420}
FEATURES = [
    "std_rush_orders", "avg_rush_orders", "std_trades", "std_volume", "avg_volume",
    "std_price", "avg_price", "avg_price_max", "avg_price_min",
]


def build_features(trades: pd.DataFrame, chunk_seconds: int) -> pd.DataFrame:
    frequency = f"{chunk_seconds}s"
    window = pd.Timedelta(minutes=WINDOW_MINUTES[chunk_seconds])
    window_chunks = window // pd.Timedelta(seconds=chunk_seconds)
    pieces = []
    for (exchange, symbol), market in trades.groupby(MARKET, sort=False):
        market = market.sort_values("timestamp", kind="stable")
        previous_end = None
        for segment, part in market.groupby("segment", sort=False):
            first, last = part["timestamp"].iloc[[0, -1]]
            if previous_end is not None and first <= previous_end:
                raise ValueError(f"Segmentos sobrepostos em {exchange} {symbol}")
            previous_end = last
            # Exclude boundary buckets whose full coverage cannot be inferred.
            start, end = first.ceil(frequency), last.floor(frequency)
            if end - start < window:
                continue

            part = part.assign(
                chunk_start=part["timestamp"].dt.floor(frequency),
                quote_volume=part["price"] * part["quantity"],
            )
            chunks = part.groupby("chunk_start").agg(
                trades=("price", "size"), volume=("quote_volume", "sum"),
                close=("price", "last"), high=("price", "max"), low=("price", "min"),
            )
            # Count timestamps with multiple aggressive buy fills, once per millisecond.
            buys = part.loc[part["side"].eq("buy"), "timestamp"].dt.floor("ms")
            rush_times = buys.value_counts().loc[lambda counts: counts.gt(1)].index
            chunks["rush_orders"] = rush_times.floor(frequency).value_counts()
            grid = pd.date_range(start, end, freq=frequency, inclusive="left", name="chunk_start")
            chunks = chunks.reindex(chunks.index.union(grid)).sort_index()
            chunks[["trades", "volume", "rush_orders"]] = chunks[["trades", "volume", "rush_orders"]].fillna(0)
            close_source = chunks.index.to_series().where(chunks["close"].notna()).ffill()
            chunks["close"] = chunks["close"].ffill()
            chunks["high"] = chunks["high"].fillna(chunks["close"])
            chunks["low"] = chunks["low"].fillna(chunks["close"])
            buckets = chunks.loc[grid]
            rolling = buckets.rolling(window_chunks)
            features = pd.DataFrame({
                "std_rush_orders": rolling["rush_orders"].std(),
                "avg_rush_orders": rolling["rush_orders"].mean(),
                "std_trades": rolling["trades"].std(),
                "std_volume": rolling["volume"].std(),
                "avg_volume": rolling["volume"].mean(),
                "std_price": rolling["close"].std(),
                "avg_price": rolling["close"].mean(),
                "avg_price_max": rolling["high"].mean(),
                "avg_price_min": rolling["low"].mean(),
            })
            features["history_start"] = close_source.loc[grid].shift(window_chunks - 1)
            features = features.dropna().reset_index()
            features["chunk_end"] = features["chunk_start"] + pd.Timedelta(seconds=chunk_seconds)
            pieces.append(features.assign(exchange=exchange, symbol=symbol, segment=segment))

    if not pieces:
        raise ValueError(f"Histórico insuficiente para uma janela completa de {window}")
    return pd.concat(pieces, ignore_index=True).sort_values(["chunk_start", *MARKET], ignore_index=True)


def label_features(features: pd.DataFrame, events: pd.DataFrame, chunk_seconds: int) -> pd.DataFrame:
    keys = [*MARKET, "chunk_start"]
    starts = events.assign(chunk_start=events["timestamp"].dt.floor(f"{chunk_seconds}s"))
    event_keys = pd.MultiIndex.from_frame(starts[keys]).unique()
    feature_keys = pd.MultiIndex.from_frame(features[keys])
    unmatched = event_keys.difference(feature_keys)
    if len(unmatched):
        exchange, symbol, start = unmatched[0]
        raise ValueError(
            f"{len(unmatched)} janela(s) com evento sem cobertura ou histórico suficiente. "
            f"Primeira ocorrência: {exchange} {symbol} {start.isoformat()}"
        )
    return features.assign(label=feature_keys.isin(event_keys).astype("int8"))
