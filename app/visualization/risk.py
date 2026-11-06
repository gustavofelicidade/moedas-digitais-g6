"""Notebook-friendly plots for a completed assessment."""


def plot_assessment(result: dict):
    import matplotlib.pyplot as plt

    assessment = result["assessment"]
    fig, ax = plt.subplots(figsize=(7, 1.8))
    score = assessment["risk_score"]
    ax.barh(["Risco heurístico"], [score], color={"APPROVE": "#2a9d8f", "REVIEW": "#e9c46a", "BLOCK": "#e76f51"}[assessment["decision"]])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Pontuação de regras (não é probabilidade de fraude)")
    ax.text(min(score + 2, 95), 0, str(score), va="center")
    fig.tight_layout()
    return fig
