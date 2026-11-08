"""Run a hypothetical operation from the command line."""

import argparse
from decimal import Decimal
import json
from pathlib import Path
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.agent.graph import analyze
from app.audit.trail import append_audit_log
from app.ingestion.repository import DEFAULT_METADATA_PATH, DEFAULT_TX_PATH, WalletRepository
from app.ingestion.schema import ProposedOperation
from app.models.risk import RiskPolicy
from app.visualization.risk import plot_operator_dashboard


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
    parser.add_argument("--save-dashboard", help="Caminho opcional (.png/.pdf) para salvar o painel visual de 4 quadrantes")
    parser.add_argument("--tx-path", default=str(DEFAULT_TX_PATH), help="Caminho opcional para first_order_df.csv")
    parser.add_argument("--metadata-path", default=str(DEFAULT_METADATA_PATH), help="Caminho opcional para wallet_metadata.csv")
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
    repository = WalletRepository(tx_path=args.tx_path, metadata_path=args.metadata_path)
    policy = RiskPolicy(max_amount_eth=args.max_eth, policy_id=args.policy_id)
    result = analyze(operation, repository=repository, policy=policy, use_llm=not args.no_llm)
    if args.audit_log and "audit_record" in result:
        append_audit_log(result["audit_record"], args.audit_log)
    if args.save_dashboard:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        out_path = Path(args.save_dashboard)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig = plot_operator_dashboard(result)
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
