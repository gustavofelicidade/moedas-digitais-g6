"""Notebook-friendly plots and multi-panel visual evidence dashboard for OONCA assessments."""

from __future__ import annotations

import textwrap
from typing import Any


DECISION_COLORS = {
    "APPROVE": "#2a9d8f",
    "REVIEW": "#e9c46a",
    "BLOCK": "#e76f51",
}


def plot_operator_dashboard(result: dict[str, Any]):
    """Render a 4-panel visual evidence dashboard for an OONCA operation evaluation."""
    import matplotlib.pyplot as plt

    operation = result.get("operation", {}) or {}
    profile = result.get("profile", {}) or {}
    assessment = result.get("assessment", {}) or {}
    audit_rec = result.get("audit_record", {}) or {}

    decision = assessment.get("decision", "REVIEW")
    score = int(assessment.get("risk_score", 0))
    policy = assessment.get("policy", {}) or {}
    review_threshold = int(policy.get("review_threshold", 35))
    color = DECISION_COLORS.get(decision, "#e9c46a")

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 7.5))
    fig.patch.set_facecolor("#fafafa")
    ax_gauge, ax_rules = axes[0, 0], axes[0, 1]
    ax_amounts, ax_card = axes[1, 0], axes[1, 1]

    # --- Panel 1 (Top-Left): Risk Score Gauge & Decision ---
    ax_gauge.set_facecolor("#ffffff")
    ax_gauge.barh(["Score heurístico"], [100], color="#eeeeee", height=0.45)
    ax_gauge.barh(["Score heurístico"], [score], color=color, height=0.45, edgecolor="#333333", linewidth=0.8)
    ax_gauge.axvline(review_threshold, color="#264653", linestyle="--", linewidth=1.4, label=f"Limiar REVIEW ({review_threshold})")
    ax_gauge.set_xlim(0, 105)
    ax_gauge.set_xlabel("Pontuação de regras (0–100) — NÃO é probabilidade de fraude")
    ax_gauge.set_title(f"1. Decisão de Triagem: {decision} ({score}/100)", fontsize=11, fontweight="bold", loc="left")
    ax_gauge.text(min(score + 2.5, 96), 0, f"{score}/100", va="center", fontweight="bold", fontsize=10, color="#1d3557")
    ax_gauge.legend(loc="lower right", frameon=True, fontsize=8.5)
    ax_gauge.grid(axis="x", linestyle=":", alpha=0.5)

    # --- Panel 2 (Top-Right): Rule Contribution Breakdown ---
    ax_rules.set_facecolor("#ffffff")
    breakdown = assessment.get("rule_breakdown", []) or []
    if breakdown:
        labels = [r["rule_id"] for r in reversed(breakdown)]
        pts = [int(r.get("points", 0)) for r in reversed(breakdown)]
        triggered = [bool(r.get("triggered", False)) for r in reversed(breakdown)]
        bar_colors = ["#e76f51" if trig and p > 0 else ("#f4a261" if trig else "#d8e2dc") for trig, p in zip(triggered, pts)]
        y_pos = range(len(labels))
        ax_rules.barh(list(y_pos), [max(p, 1) if trig else 0 for p, trig in zip(pts, triggered)], color=bar_colors, edgecolor="#555555", linewidth=0.5)
        ax_rules.set_yticks(list(y_pos))
        ax_rules.set_yticklabels(labels, fontsize=8.5)
        max_pt = max([p for p in pts] + [35])
        ax_rules.set_xlim(0, max_pt + 10)
        for idx, (p, trig) in enumerate(zip(pts, triggered)):
            status_txt = f"+{p} pts" if (trig and p > 0) else ("ACIONADA (bloqueio)" if trig else "0")
            ax_rules.text((max(p, 1) if trig else 0) + 0.8, idx, status_txt, va="center", fontsize=8)
    else:
        ax_rules.text(0.5, 0.5, "Sem detalhamento de regras disponível", ha="center", va="center")
    ax_rules.set_xlabel("Pontos adicionados ao score heurístico")
    ax_rules.set_title("2. Decomposição Determinística de Regras", fontsize=11, fontweight="bold", loc="left")
    ax_rules.grid(axis="x", linestyle=":", alpha=0.5)

    # --- Panel 3 (Bottom-Left): Proposed Amount vs Historical Quantiles ---
    ax_amounts.set_facecolor("#ffffff")
    proposed_val = float(operation.get("amount", 0.0) or 0.0)
    median_val = float(profile.get("median_amount", 0.0) or 0.0)
    p75_val = float(profile.get("p75_amount", 0.0) or 0.0)
    p95_val = float(profile.get("p95_amount", 0.0) or 0.0)
    p95_2x = p95_val * 2.0

    amt_labels = ["Mediana hist.", "P75 hist.", "P95 hist.", "Limiar 2x P95", "Valor Proposto"]
    amt_values = [median_val, p75_val, p95_val, p95_2x, proposed_val]
    amt_colors = ["#8ecae6", "#219ebc", "#126782", "#ffb703", color]

    max_eth_str = policy.get("max_amount_eth")
    if max_eth_str is not None:
        try:
            max_eth_val = float(max_eth_str)
            amt_labels.insert(4, "Teto Política")
            amt_values.insert(4, max_eth_val)
            amt_colors.insert(4, "#9d0208")
        except (TypeError, ValueError):
            pass

    ax_amounts.barh(amt_labels, amt_values, color=amt_colors, edgecolor="#333333", linewidth=0.6)
    max_v = max(amt_values + [1e-6])
    ax_amounts.set_xlim(0, max_v * 1.22)
    for idx, val in enumerate(amt_values):
        ax_amounts.text(val + max_v * 0.02, idx, f"{val:.4g}", va="center", fontsize=8.5)
    asset_name = operation.get("asset", "ETH")
    ax_amounts.set_xlabel(f"Valor ({asset_name})")
    ax_amounts.set_title("3. Comparativo de Valor vs. Histórico da Carteira", fontsize=11, fontweight="bold", loc="left")
    ax_amounts.grid(axis="x", linestyle=":", alpha=0.5)

    # --- Panel 4 (Bottom-Right): Behavioral Proxies, Counterfactuals & Audit Card ---
    ax_card.axis("off")
    cadence = profile.get("temporal_cadence", {}) or {}
    auto_proxy = profile.get("automation_proxy", {}) or {}
    counterfactuals = assessment.get("counterfactuals", []) or []
    completeness = audit_rec.get("accountability_completeness", {}) or {}

    rf_ratio = cadence.get("rapid_fire_ratio")
    burst_idx = cadence.get("burstiness_index")
    entropy_val = cadence.get("hourly_entropy_normalized")
    rf_str = f"{rf_ratio:.1%}" if isinstance(rf_ratio, (int, float)) else "N/A"
    burst_str = f"{burst_idx:.2f}" if isinstance(burst_idx, (int, float)) else "N/A"
    ent_str = f"{entropy_val:.2f}" if isinstance(entropy_val, (int, float)) else "N/A"

    lines = [
        "4. Proxies Comportamentais, Contrafactuais & Auditoria",
        "-" * 58,
        f"• Amostra: {profile.get('n_rows', 0)} linhas ({profile.get('n_unique_tx_hashes', 0)} TxHashes únicos) | HHI Dest.: {profile.get('recipient_hhi', 0.0):.2f}",
        f"• Cadência: Rapid-Fire (<=60s)={rf_str} | Burstiness={burst_str} | Entropia={ent_str}",
        f"• Proxy de Automação: {'SINALIZADO' if auto_proxy.get('flagged') else 'Não sinalizado'} (não prova IA)",
        "",
        "Recomendações Contrafactuais (O que mudaria a triagem?):",
    ]
    if counterfactuals:
        for cf in counterfactuals[:3]:
            wrapped = textwrap.wrap(f"  -> {cf}", width=66)
            lines.extend(wrapped[:2])
    else:
        lines.append("  -> Operação dentro dos parâmetros regulares da política atual.")

    sha_short = (audit_rec.get("evidence_sha256") or "N/A")[:16]
    comp_score = completeness.get("score", 0.0)
    lines.extend([
        "",
        "Governança & Rastreabilidade (Accountability):",
        f"• Revisão Humana Obrigatória: {'SIM' if audit_rec.get('human_review_required') else 'NÃO (Aprovação direta)'}",
        f"• Hash SHA-256 Evidência: {sha_short}... | Completude: {comp_score:.0%}",
        f"• Política: {audit_rec.get('policy_id', policy.get('policy_id', 'default'))} | LLM: {result.get('llm_status', 'disabled')}",
    ])

    card_text = "\n".join(lines)
    ax_card.text(
        0.02,
        0.97,
        card_text,
        va="top",
        ha="left",
        fontsize=8.5,
        family="monospace",
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#ffffff", "edgecolor": "#cccccc", "linewidth": 1.0},
    )

    wallet_from = str(operation.get("wallet_from", ""))[:12]
    wallet_to = str(operation.get("wallet_to", ""))[:12]
    fig.suptitle(
        f"OONCA — Painel de Evidências e Governança On-Chain ({wallet_from}... -> {wallet_to}...)",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return fig


def plot_assessment(result: dict[str, Any]):
    """Render assessment visualization (delegates to the 4-panel operator dashboard)."""
    return plot_operator_dashboard(result)
