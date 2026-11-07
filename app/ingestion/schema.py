"""Input contract for a proposed Ethereum operation."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re

_ETH_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def _is_eth_address(address: str) -> bool:
    if not isinstance(address, str):
        return False
    try:
        from web3 import Web3
        return bool(Web3.is_address(address))
    except ImportError:
        return bool(_ETH_ADDRESS_RE.match(address.strip()))


@dataclass(frozen=True)
class ProposedOperation:
    wallet_from: str
    wallet_to: str
    amount: Decimal
    operation: str = "transfer"
    asset: str = "ETH"
    as_of: datetime | None = None
    operator_id: str | None = None
    agent_id: str | None = "oonca_v1"
    policy_id: str = "default_triage_v2"

    @classmethod
    def from_values(
        cls,
        wallet_from: str,
        wallet_to: str,
        amount: str | float | Decimal,
        operation: str = "transfer",
        asset: str = "ETH",
        as_of: datetime | str | None = None,
        *,
        operator_id: str | None = None,
        agent_id: str | None = "oonca_v1",
        policy_id: str = "default_triage_v2",
    ) -> "ProposedOperation":
        if not _is_eth_address(wallet_from) or not _is_eth_address(wallet_to):
            raise ValueError("wallet_from e wallet_to devem ser endereços Ethereum válidos")
        try:
            value = Decimal(str(amount))
        except InvalidOperation as exc:
            raise ValueError("amount deve ser numérico") from exc
        if not value.is_finite() or value < 0:
            raise ValueError("amount deve ser finito e não negativo")
        if isinstance(as_of, str):
            as_of = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        if as_of is not None:
            if as_of.tzinfo is None:
                raise ValueError("as_of precisa conter fuso horário")
            as_of = as_of.astimezone(timezone.utc)
        operation = operation.strip().lower()
        asset = asset.strip().upper()
        if not operation or not asset:
            raise ValueError("operation e asset são obrigatórios")
        clean_operator = str(operator_id).strip() if operator_id else None
        clean_agent = str(agent_id).strip() if agent_id else None
        clean_policy = str(policy_id).strip() if policy_id else "default_triage_v2"
        return cls(
            wallet_from.lower(),
            wallet_to.lower(),
            value,
            operation,
            asset,
            as_of,
            clean_operator,
            clean_agent,
            clean_policy,
        )

    def as_state(self) -> dict:
        data = asdict(self)
        data["amount"] = str(self.amount)
        data["as_of"] = self.as_of.isoformat() if self.as_of else None
        return data
