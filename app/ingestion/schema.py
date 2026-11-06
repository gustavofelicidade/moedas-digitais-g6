"""Input contract for a proposed Ethereum operation."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class ProposedOperation:
    wallet_from: str
    wallet_to: str
    amount: Decimal
    operation: str = "transfer"
    asset: str = "ETH"
    as_of: datetime | None = None

    @classmethod
    def from_values(cls, wallet_from: str, wallet_to: str, amount: str | float,
                    operation: str = "transfer", asset: str = "ETH",
                    as_of: datetime | str | None = None) -> "ProposedOperation":
        from web3 import Web3

        if not Web3.is_address(wallet_from) or not Web3.is_address(wallet_to):
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
        return cls(wallet_from.lower(), wallet_to.lower(), value, operation, asset, as_of)

    def as_state(self) -> dict:
        data = asdict(self)
        data["amount"] = str(self.amount)
        data["as_of"] = self.as_of.isoformat() if self.as_of else None
        return data
