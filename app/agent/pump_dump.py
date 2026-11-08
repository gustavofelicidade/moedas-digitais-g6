"""Label, train and run the OONCA market surveillance agent."""

import argparse
import json
from pathlib import Path
from typing import TypedDict

import joblib
import pandas as pd
from langgraph.graph import END, START, StateGraph

from app.features.pump_dump import WINDOW_MINUTES, build_features, label_features
from app.ingestion.pump_dump import parse_timestamp, read_events, read_trades
from app.models.pump_dump import ALERT, PumpModel, train


class PumpState(TypedDict, total=False):
    trades_path: str
    features: pd.DataFrame
    detections: pd.DataFrame


def build_pump_agent(model: PumpModel):
    def collect(state: PumpState) -> dict:
        trades = read_trades(state["trades_path"])
        return {"features": build_features(trades, model.chunk_seconds)}

    def detect(state: PumpState) -> dict:
        return {"detections": model.score(state["features"])}

    def explain(state: PumpState) -> dict:
        detections = state["detections"].copy()
        detections["explanation"] = ""
        for index, row in detections.loc[detections["status"].eq(ALERT)].iterrows():
            detections.at[index, "explanation"] = (
                f"Padrão compatível com início de pump em {row['exchange']} {row['symbol']}. "
                f"Score do detector {row['score']:.3f} (limiar {model.threshold:g}). "
                f"Média de rush orders por janela: {row['avg_rush_orders']:.3f}. "
                f"Desvio padrão da contagem de negócios: {row['std_trades']:.3f}."
            )
        return {"detections": detections}

    graph = StateGraph(PumpState)
    graph.add_node("collect_market_evidence", collect)
    graph.add_node("detect_pump", detect)
    graph.add_node("explain", explain)
    graph.add_edge(START, "collect_market_evidence")
    graph.add_edge("collect_market_evidence", "detect_pump")
    graph.add_edge("detect_pump", "explain")
    graph.add_edge("explain", END)
    return graph.compile()


def main():
    parser = argparse.ArgumentParser(description="Detecta padrões de início de pump em negócios de mercado")
    commands = parser.add_subparsers(dest="command", required=True)

    for command in ("label", "train"):
        sub = commands.add_parser(command)
        sub.add_argument("--trades", type=Path, required=True)
        sub.add_argument("--events", type=Path, required=True)
        sub.add_argument("--chunk-seconds", type=int, choices=WINDOW_MINUTES, default=25)
        if command == "train":
            sub.add_argument("--test-from", required=True, help="Início do período de teste (ISO 8601 UTC)")
            sub.add_argument("--threshold", type=float, default=0.5)
            sub.add_argument("--model-out", type=Path, required=True)
        else:
            sub.add_argument("--output", type=Path, required=True)

    detect = commands.add_parser("detect")
    detect.add_argument("--trades", type=Path, required=True)
    detect.add_argument("--model", type=Path, required=True, help="Artefato local confiável criado por train")
    detect.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    try:
        if args.command == "detect":
            model = joblib.load(args.model)
            result = build_pump_agent(model).invoke({"trades_path": str(args.trades)})
            scored = result["detections"]
            args.output.parent.mkdir(parents=True, exist_ok=True)
            scored.to_csv(args.output, index=False)
            summary = {"chunks": len(scored), "alerts": int(scored["status"].eq(ALERT).sum())}
        else:
            features = build_features(read_trades(args.trades), args.chunk_seconds)
            labeled = label_features(features, read_events(args.events), args.chunk_seconds)
            if args.command == "train":
                cutoff = parse_timestamp(pd.Series([args.test_from])).iloc[0]
                model, summary = train(labeled, args.chunk_seconds, cutoff, args.threshold)
                args.model_out.parent.mkdir(parents=True, exist_ok=True)
                joblib.dump(model, args.model_out)
            else:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                labeled.to_csv(args.output, index=False)
                summary = {"chunks": len(labeled), "positives": int(labeled["label"].sum())}
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Erro: {exc}\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
