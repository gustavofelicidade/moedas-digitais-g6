"""Run a hypothetical operation from the command line."""

import argparse
import json
from decimal import Decimal

from app.agent.graph import analyze
from app.ingestion.schema import ProposedOperation
from app.models.risk import RiskPolicy


def main():
    parser = argparse.ArgumentParser(description="Analisa uma operação hipotética sem assinar ou enviar transações")
    parser.add_argument("--from", dest="sender", required=True)
    parser.add_argument("--to", dest="recipient", required=True)
    parser.add_argument("--amount", required=True, help="Valor em ETH para transferências ETH")
    parser.add_argument("--operation", default="transfer")
    parser.add_argument("--asset", default="ETH")
    parser.add_argument("--as-of", help="Data ISO com fuso; usa apenas linhas anteriores a ela")
    parser.add_argument("--max-eth", type=Decimal, help="Limite explícito para bloquear valores em ETH")
    parser.add_argument("--no-llm", action="store_true", help="Explicação local sem OpenRouter")
    args = parser.parse_args()
    operation = ProposedOperation.from_values(args.sender, args.recipient, args.amount,
                                              args.operation, args.asset, args.as_of)
    result = analyze(operation, policy=RiskPolicy(max_amount_eth=args.max_eth),
                     use_llm=not args.no_llm)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
