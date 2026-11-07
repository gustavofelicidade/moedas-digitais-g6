"""Run a hypothetical operation from the command line."""

import argparse
import json
from decimal import Decimal

from app.agent.graph import analyze
from app.audit.trail import append_audit_log
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
    parser.add_argument("--operator-id", help="Identificador opcional do operador/mesa para trilha de auditoria")
    parser.add_argument("--policy-id", default="default_triage_v2", help="Identificador da política de triagem")
    parser.add_argument("--audit-log", help="Caminho opcional de arquivo JSONL para persistir o registro de auditoria")
    parser.add_argument("--no-llm", action="store_true", help="Explicação local sem OpenRouter")
    args = parser.parse_args()
    operation = ProposedOperation.from_values(
        args.sender,
        args.recipient,
        args.amount,
        args.operation,
        args.asset,
        args.as_of,
        operator_id=args.operator_id,
        policy_id=args.policy_id,
    )
    policy = RiskPolicy(max_amount_eth=args.max_eth, policy_id=args.policy_id)
    result = analyze(operation, policy=policy, use_llm=not args.no_llm)
    if args.audit_log and "audit_record" in result:
        append_audit_log(result["audit_record"], args.audit_log)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
