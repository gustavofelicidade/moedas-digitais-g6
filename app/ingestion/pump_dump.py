"""CSV input contracts for market trades and documented pump starts."""

from pathlib import Path

import pandas as pd


MARKET = ["exchange", "symbol"]


def parse_timestamp(values: pd.Series) -> pd.Series:
    """Read ISO timestamps (UTC if unspecified) or integer Unix milliseconds."""
    values = values.astype("string").str.strip()
    milliseconds = values.str.fullmatch(r"[0-9]+", na=False)
    parsed = pd.to_datetime(
        values.where(~milliseconds), format="ISO8601", utc=True, errors="coerce"
    ).dt.as_unit("ns").copy()
    parsed.loc[milliseconds] = pd.to_datetime(
        pd.to_numeric(values[milliseconds], errors="coerce"), unit="ms", utc=True, errors="coerce"
    )
    if parsed.isna().any():
        raise ValueError("timestamp inválido; use ISO 8601 ou Unix em milissegundos")
    return parsed


def _read(path: str | Path, required: list[str]) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype="string", keep_default_na=False)
    missing = set(required) - set(frame)
    if missing:
        raise ValueError(f"{path}: faltam as colunas {', '.join(sorted(missing))}")
    if frame.empty:
        raise ValueError(f"{path}: o arquivo não contém registros")
    for column in MARKET:
        frame[column] = frame[column].str.strip()
        if frame[column].eq("").any():
            raise ValueError(f"{path}: {column} precisa ser preenchido")
    frame["exchange"] = frame["exchange"].str.lower()
    frame["symbol"] = frame["symbol"].str.upper()
    frame["timestamp"] = parse_timestamp(frame["timestamp"])
    return frame


def read_trades(path: str | Path) -> pd.DataFrame:
    trades = _read(path, [*MARKET, "timestamp", "price", "quantity", "side"])
    for column in ["price", "quantity"]:
        trades[column] = pd.to_numeric(trades[column], errors="coerce").astype(float)
        if (~trades[column].between(0, float("inf"), inclusive="neither")).any():
            raise ValueError(f"{path}: {column} deve ser finito e maior que zero")
    trades["side"] = trades["side"].str.strip().str.lower()
    if (~trades["side"].isin(["buy", "sell"])).any():
        raise ValueError(f"{path}: side deve ser buy ou sell, do ponto de vista do agressor")
    if "segment" not in trades:
        trades["segment"] = "0"
    trades["segment"] = trades["segment"].str.strip()
    if trades["segment"].eq("").any():
        raise ValueError(f"{path}: segment precisa ser preenchido em todas as linhas")
    if "trade_id" in trades:
        trades["trade_id"] = trades["trade_id"].str.strip()
        if trades["trade_id"].eq("").any() or trades.duplicated([*MARKET, "trade_id"]).any():
            raise ValueError(f"{path}: trade_id deve ser preenchido e único por mercado")
    return trades


def read_events(path: str | Path) -> pd.DataFrame:
    return _read(path, [*MARKET, "timestamp"])
