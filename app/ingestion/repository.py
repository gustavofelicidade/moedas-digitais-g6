"""Read the existing transaction dataset and ENS metadata for one wallet."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TX_PATH = ROOT / "data/Ethereum-Transactions-for-Fraud-Detection/first_order_df.csv"
DEFAULT_METADATA_PATH = ROOT / "data/wallet_metadata.csv"


class WalletRepository:
    def __init__(self, tx_path: str | Path = DEFAULT_TX_PATH,
                 metadata_path: str | Path = DEFAULT_METADATA_PATH):
        self.tx_path = Path(tx_path)
        self.metadata_path = Path(metadata_path)

    def profile(self, wallet_from: str, wallet_to: str, as_of: str | None = None) -> dict:
        if not self.tx_path.is_file():
            raise FileNotFoundError(self.tx_path)
        sender_parts = []
        recipient_seen = False
        total_rows = 0
        cutoff = pd.Timestamp(as_of) if as_of else None
        columns = ["TxHash", "TimeStamp", "From", "To", "Value", "isError"]
        for chunk in pd.read_csv(self.tx_path, usecols=columns, chunksize=100_000):
            chunk["From"] = chunk["From"].astype("string").str.lower()
            chunk["To"] = chunk["To"].astype("string").str.lower()
            if cutoff is not None:
                chunk = chunk[pd.to_datetime(chunk["TimeStamp"], unit="s", utc=True) < cutoff]
            total_rows += len(chunk)
            sender = chunk[chunk["From"] == wallet_from]
            if not sender.empty:
                recipient_seen |= bool(sender["To"].eq(wallet_to).any())
                sender_parts.append(sender)
        tx = pd.concat(sender_parts, ignore_index=True) if sender_parts else pd.DataFrame(columns=columns)
        values = pd.to_numeric(tx["Value"], errors="coerce")
        errors = pd.to_numeric(tx["isError"], errors="coerce")
        dates = pd.to_datetime(tx["TimeStamp"], unit="s", utc=True, errors="coerce")
        metadata = self._metadata(wallet_from)
        return {
            "wallet_from": wallet_from,
            "source_rows": total_rows,
            "n_rows": len(tx),
            "n_unique_tx_hashes": int(tx["TxHash"].nunique()),
            "n_receivers": int(tx["To"].nunique()),
            "n_active_days": int(dates.dt.date.nunique()),
            "historical_error_rate": float(errors.mean()) if errors.notna().any() else None,
            "median_amount": float(values.median()) if values.notna().any() else None,
            "p95_amount": float(values.quantile(.95)) if values.notna().any() else None,
            "total_amount": float(values.sum()) if values.notna().any() else None,
            "first_seen": dates.min().isoformat() if dates.notna().any() else None,
            "last_seen": dates.max().isoformat() if dates.notna().any() else None,
            "recipient_seen": recipient_seen,
            "wallet_metadata": metadata,
            "dataset": str(self.tx_path),
        }

    def _metadata(self, wallet: str) -> dict | None:
        if not self.metadata_path.is_file():
            return None
        table = pd.read_csv(self.metadata_path, dtype=str, low_memory=False)
        matches = table[table["wallet_address"].str.lower() == wallet]
        if matches.empty:
            return None
        record = matches.iloc[-1]
        return {key: (None if pd.isna(record.get(key)) else str(record[key]))
                for key in ("wallet_type", "ens_name", "ens_location", "lookup_status", "observed_at")}
