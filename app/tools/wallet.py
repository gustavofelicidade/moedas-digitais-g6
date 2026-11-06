"""Local, read-only wallet profile tool."""

from app.ingestion.repository import WalletRepository


def wallet_profile_tool(repository: WalletRepository, operation: dict) -> dict:
    return repository.profile(operation["wallet_from"], operation["wallet_to"], operation.get("as_of"))
