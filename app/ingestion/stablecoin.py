"""Streaming readers for the SNAP ERC-20 stablecoin dataset."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pandas as pd


TOKEN_CONTRACTS = {
    "USDT": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "USDC": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "DAI": "0x6b175474e89094c44da98b954eedeac495271d0f",
    "UST": "0xa47c8bf37f92abed4a126bda807a7b7498661acd",
    "PAX": "0x8e870d67f660d95d5be530380d0ec0bd388289e1",
}
CONTRACT_TOKENS = {address: token for token, address in TOKEN_CONTRACTS.items()}
PRICE_FILES = {
    "dai": "DAI", "pax": "PAX", "usdc": "USDC", "usdt": "USDT", "ustc": "UST"
}


def read_market_context(data_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load daily USD prices from the small ZIP and the dataset's event catalogue."""
    root = Path(data_dir)
    price_frames = []
    with ZipFile(root / "price_data.zip") as archive:
        for stem, token in PRICE_FILES.items():
            frame = pd.read_csv(archive.open(f"price_data/{stem}_price_data.csv"))
            frame["token"] = token
            frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="s", utc=True)
            frame["date"] = frame["timestamp"].dt.floor("D")
            price_frames.append(frame)
    prices = pd.concat(price_frames, ignore_index=True)
    # The provided event catalogue contains a Windows-1252 punctuation byte.
    events = pd.read_csv(root / "event_data.csv", encoding="cp1252")
    events["timestamp"] = pd.to_datetime(events["timestamp"], unit="s", utc=True)
    events["date"] = events["timestamp"].dt.floor("D")
    # SNAP uses `ustc` in its event table for TerraUSD (UST).
    events["token"] = events["stablecoin"].replace({"ustc": "UST"}).str.upper()
    return prices, events


def aggregate_daily_transfers(
    csv_path: str | Path, *, chunksize: int = 500_000
) -> pd.DataFrame:
    """Aggregate transfer count and token quantity by token and UTC day.

    Reads the multi-gigabyte SNAP CSV in chunks and keeps only the five stablecoins
    used by this analysis. Values are token quantities as represented by SNAP.
    """
    totals: dict[tuple[str, object], list[float]] = {}
    usecols = ["time_stamp", "contract_address", "value"]
    for chunk in pd.read_csv(csv_path, usecols=usecols, chunksize=chunksize):
        chunk["token"] = chunk["contract_address"].str.lower().map(CONTRACT_TOKENS)
        chunk = chunk.loc[chunk["token"].notna()].copy()
        if chunk.empty:
            continue
        chunk["date"] = pd.to_datetime(chunk["time_stamp"], unit="s", utc=True).dt.floor("D")
        chunk["value"] = pd.to_numeric(chunk["value"], errors="coerce")
        grouped = chunk.groupby(["token", "date"], observed=True).agg(
            transfer_count=("time_stamp", "size"),
            transfer_amount=("value", "sum"),
        )
        for (token, date), row in grouped.iterrows():
            key = (token, date)
            # Counts and value are exactly additive. Endpoint counts are lower bounds
            # when the same address occurs in more than one input chunk.
            bucket = totals.setdefault(key, [0.0, 0.0])
            bucket[0] += row["transfer_count"]
            bucket[1] += row["transfer_amount"]
    if not totals:
        return pd.DataFrame(columns=["token", "date", "transfer_count", "transfer_amount"])
    result = pd.DataFrame(
        [(token, date, *values) for (token, date), values in totals.items()],
        columns=["token", "date", "transfer_count", "transfer_amount"],
    )
    return result.sort_values(["date", "token"], ignore_index=True)
