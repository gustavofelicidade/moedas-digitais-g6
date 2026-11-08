"""Read the existing transaction dataset and ENS metadata for sender and recipient wallets."""

from pathlib import Path

import pandas as pd

from app.features.wallet_behavior import compute_wallet_features

ROOT = Path(__file__).resolve().parents[2]


def _resolve_default_path(relative_path: str) -> Path:
    local_candidate = ROOT / relative_path
    if local_candidate.is_file():
        return local_candidate
    # Fallback when running inside a git worktree whose data/ directory lives in the main repo
    git_file = ROOT / ".git"
    if git_file.is_file():
        try:
            content = git_file.read_text(encoding="utf-8").strip()
            if content.startswith("gitdir:"):
                gitdir = Path(content.split("gitdir:", 1)[1].strip())
                main_repo = gitdir.parents[2]
                worktree_candidate = main_repo / relative_path
                if worktree_candidate.is_file():
                    return worktree_candidate
        except Exception:
            pass
    return local_candidate


DEFAULT_TX_PATH = _resolve_default_path("data/Ethereum-Transactions-for-Fraud-Detection/first_order_df.csv")
DEFAULT_METADATA_PATH = _resolve_default_path("data/wallet_metadata.csv")


class WalletRepository:
    def __init__(
        self,
        tx_path: str | Path = DEFAULT_TX_PATH,
        metadata_path: str | Path = DEFAULT_METADATA_PATH,
    ):
        self.tx_path = Path(tx_path)
        self.metadata_path = Path(metadata_path)

    def profile(self, wallet_from: str, wallet_to: str, as_of: str | None = None) -> dict:
        if not self.tx_path.is_file():
            raise FileNotFoundError(self.tx_path)
        wallet_from_norm = wallet_from.strip().lower()
        wallet_to_norm = wallet_to.strip().lower()

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
            sender = chunk[chunk["From"] == wallet_from_norm]
            if not sender.empty:
                recipient_seen |= bool(sender["To"].eq(wallet_to_norm).any())
                sender_parts.append(sender)

        tx = pd.concat(sender_parts, ignore_index=True) if sender_parts else pd.DataFrame(columns=columns)
        features = compute_wallet_features(
            tx,
            wallet_from_norm,
            wallet_to_norm,
            source_rows=total_rows,
            as_of=as_of,
            recipient_seen_override=recipient_seen,
        )
        sender_meta = self._metadata(wallet_from_norm)
        recipient_meta = self._metadata(wallet_to_norm)
        features["wallet_metadata"] = sender_meta
        features["recipient_metadata"] = recipient_meta
        features["dataset"] = str(self.tx_path)
        return features

    def _metadata(self, wallet: str) -> dict | None:
        if not self.metadata_path.is_file():
            return None
        table = pd.read_csv(self.metadata_path, dtype=str, low_memory=False)
        matches = table[table["wallet_address"].str.lower() == wallet.lower()]
        if matches.empty:
            return None
        record = matches.iloc[-1]
        keys = (
            "wallet_type",
            "ens_name",
            "ens_location",
            "contract_code_bytes",
            "lookup_status",
            "observed_at",
        )
        return {
            key: (None if pd.isna(record.get(key)) else str(record[key]))
            for key in keys
            if key in record or key in ("wallet_type", "ens_name", "ens_location", "lookup_status", "observed_at")
        }
