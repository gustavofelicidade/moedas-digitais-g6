"""Utilities for enriching Ethereum wallet addresses with ENS metadata.

The class in this module is intentionally read-only: it resolves public ENS
records and appends the results to a local metadata table. It never sends
transactions or writes to the blockchain.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import pandas as pd
from dotenv import load_dotenv


DEFAULT_TEXT_KEYS = (
    "description",
    "url",
    "avatar",
    "email",
    "location",
    "com.twitter",
    "com.github",
)

METADATA_COLUMNS = (
    "wallet_address",
    "network",
    "wallet_type",
    "ens_name",
    "ens_forward_match",
    "ens_description",
    "ens_url",
    "ens_avatar",
    "ens_email",
    "ens_location",
    "ens_twitter",
    "ens_github",
    "contract_code_bytes",
    "lookup_status",
    "source",
    "source_url",
    "observed_at",
    "error",
)


@dataclass
class ENSRecord:
    """One wallet-level ENS enrichment record."""

    wallet_address: str
    network: str = "ethereum"
    wallet_type: str | None = None
    ens_name: str | None = None
    ens_forward_match: bool | None = None
    ens_description: str | None = None
    ens_url: str | None = None
    ens_avatar: str | None = None
    ens_email: str | None = None
    ens_location: str | None = None
    ens_twitter: str | None = None
    ens_github: str | None = None
    contract_code_bytes: int | None = None
    lookup_status: str = "ok"
    source: str = "ENS/web3.py"
    source_url: str = "https://web3py.readthedocs.io/en/stable/ens_overview.html"
    observed_at: str | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class ENSSupport:
    """Resolve ENS and basic on-chain metadata for Ethereum addresses.

    Parameters
    ----------
    rpc_url:
        An Ethereum JSON-RPC endpoint, for example an Infura, Alchemy or
        public endpoint URL. Required when ``web3_instance`` is not supplied.
    web3_instance:
        Optional already-configured ``web3.Web3`` object, useful for tests or
        applications that already manage their provider.
    network:
        Label written to the output table.
    metadata_path:
        Default append destination for wallet metadata.
    """

    def __init__(
        self,
        rpc_url: str | None = None,
        web3_instance=None,
        network: str = "ethereum",
        metadata_path: str | Path = "data/wallet_metadata.csv",
    ) -> None:
        # Carrega .env do diretório de execução sem sobrescrever variáveis já
        # exportadas no ambiente do processo.
        project_env = Path(__file__).resolve().parents[1] / ".env"
        load_dotenv(project_env)
        try:
            from web3 import Web3
            from ens import ENS
        except ImportError as exc:
            raise ImportError(
                "ENS support requires web3.py. Install dependencies with "
                "`pip install -r requirements.txt`."
            ) from exc

        if web3_instance is None:
            rpc_url = rpc_url or os.getenv("ETH_RPC_URL")
            if not rpc_url:
                raise ValueError(
                    "Informe rpc_url ou defina ETH_RPC_URL no ambiente/.env."
                )
            web3_instance = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30}))

        self.w3 = web3_instance
        self.ens = ENS.from_web3(web3_instance)
        self.network = network
        self.metadata_path = Path(metadata_path)

    def normalize_address(self, address: str) -> str:
        """Validate an EVM address and return its checksum representation."""
        address = str(address).strip()
        if not self.w3.is_address(address):
            raise ValueError(f"Endereço Ethereum inválido: {address!r}")
        return self.w3.to_checksum_address(address)

    def _read_text_records(self, ens_name: str, text_keys: Sequence[str]) -> dict[str, str | None]:
        records: dict[str, str | None] = {}
        for key in text_keys:
            try:
                records[key] = self.ens.get_text(ens_name, key) or None
            except Exception:
                records[key] = None
        return records

    def lookup_address(
        self,
        address: str,
        text_keys: Sequence[str] = DEFAULT_TEXT_KEYS,
    ) -> ENSRecord:
        """Resolve one address, without raising for normal RPC/ENS misses."""
        checksum_address = self.normalize_address(address)
        observed_at = datetime.now(timezone.utc).isoformat()

        try:
            code = self.w3.eth.get_code(checksum_address)
            code_bytes = len(code)
            wallet_type = "contract" if code_bytes > 0 else "eoa"
        except Exception as exc:
            code_bytes = None
            wallet_type = None
            code_error = str(exc)

        record = ENSRecord(
            wallet_address=checksum_address,
            network=self.network,
            wallet_type=wallet_type,
            contract_code_bytes=code_bytes,
            observed_at=observed_at,
        )

        try:
            ens_name = self.ens.name(checksum_address)
            if ens_name:
                forward_address = self.ens.address(ens_name)
                forward_match = bool(
                    forward_address
                    and self.normalize_address(forward_address).lower() == checksum_address.lower()
                )
                record.ens_name = ens_name if forward_match else None
                record.ens_forward_match = forward_match
                if forward_match:
                    text = self._read_text_records(ens_name, text_keys)
                    record.ens_description = text.get("description")
                    record.ens_url = text.get("url")
                    record.ens_avatar = text.get("avatar")
                    record.ens_email = text.get("email")
                    record.ens_location = text.get("location")
                    record.ens_twitter = text.get("com.twitter")
                    record.ens_github = text.get("com.github")
            else:
                record.lookup_status = "no_ens_name"
        except Exception as exc:
            record.lookup_status = "rpc_or_ens_error"
            record.error = str(exc)

        if wallet_type is None and 'code_error' in locals():
            record.error = "; ".join(filter(None, [record.error, code_error]))
            if record.lookup_status == "ok":
                record.lookup_status = "partial_error"
        return record

    def append_records(
        self,
        records: Iterable[ENSRecord | Mapping],
        output_path: str | Path | None = None,
    ) -> pd.DataFrame:
        """Append records to CSV and return the normalized rows written."""
        path = Path(output_path or self.metadata_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [r.to_dict() if isinstance(r, ENSRecord) else dict(r) for r in records]
        frame = pd.DataFrame(rows).reindex(columns=METADATA_COLUMNS)
        if frame.empty:
            return frame
        frame.to_csv(path, mode="a", header=not path.exists(), index=False)
        return frame

    def enrich_addresses(
        self,
        addresses: Iterable[str],
        text_keys: Sequence[str] = DEFAULT_TEXT_KEYS,
        output_path: str | Path | None = None,
        skip_existing: bool = True,
    ) -> pd.DataFrame:
        """Resolve unique addresses and append them to ``wallet_metadata.csv``."""
        path = Path(output_path or self.metadata_path)
        unique_addresses = []
        seen = set()
        for address in addresses:
            try:
                normalized = self.normalize_address(address)
            except ValueError:
                continue
            key = normalized.lower()
            if key not in seen:
                seen.add(key)
                unique_addresses.append(normalized)

        existing = set()
        if skip_existing and path.exists():
            existing_df = pd.read_csv(path, usecols=lambda c: c == "wallet_address")
            existing = set(existing_df["wallet_address"].dropna().astype(str).str.lower())

        records = [
            self.lookup_address(address, text_keys=text_keys)
            for address in unique_addresses
            if address.lower() not in existing
        ]
        return self.append_records(records, output_path=path)

    def enrich_dataframe(
        self,
        frame: pd.DataFrame,
        address_col: str = "wallet_from",
        text_keys: Sequence[str] = DEFAULT_TEXT_KEYS,
        output_path: str | Path | None = None,
        skip_existing: bool = True,
    ) -> pd.DataFrame:
        """Enrich addresses from a DataFrame and append one row per wallet."""
        if address_col not in frame.columns:
            raise KeyError(f"Coluna não encontrada: {address_col}")
        return self.enrich_addresses(
            frame[address_col].dropna().tolist(),
            text_keys=text_keys,
            output_path=output_path,
            skip_existing=skip_existing,
        )
