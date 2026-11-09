"""Build the small, attributed sample bundle used to run the delivery notebook."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SAMPLES = ROOT / "samples"
MAX_BUNDLE_BYTES = 5_000_000
ROUTINE_CASE_WALLET = "0x3cbd2e6143f057bd49ffb4c7058217a5900c35d3"


def build() -> int:
    tx_path = DATA / "Ethereum-Transactions-for-Fraud-Detection" / "first_order_df.csv"
    stablecoin_daily = DATA / "ERC20-stablecoins" / "derived" / "token_daily_metrics_V3.csv"
    if not stablecoin_daily.is_file():
        from app.ingestion.stablecoin import aggregate_daily_transfers

        stablecoin_daily.parent.mkdir(parents=True, exist_ok=True)
        aggregate_daily_transfers(
            DATA / "ERC20-stablecoins" / "token_transfers_V3.0.0.csv"
        ).to_csv(stablecoin_daily, index=False)
    tx = pd.read_csv(tx_path)
    tx["From"] = tx["From"].astype("string").str.lower()
    counts = tx.groupby("From")["TxHash"].nunique().sort_values(ascending=False)
    selected = list(counts.head(5).index)
    if ROUTINE_CASE_WALLET in counts.index and ROUTINE_CASE_WALLET not in selected:
        selected.append(ROUTINE_CASE_WALLET)
    sample = tx.loc[tx["From"].isin(selected)].copy()

    files = {
        SAMPLES / "ethereum" / "first_order_df.csv": None,
        SAMPLES / "ethereum" / "wallet_metadata.csv": DATA / "wallet_metadata.csv",
        SAMPLES / "market" / "coin_Ethereum.csv": DATA / "Coin_Ethereum" / "coin_Ethereum.csv",
        SAMPLES / "stablecoin" / "event_data.csv": DATA / "ERC20-stablecoins" / "event_data.csv",
        SAMPLES / "stablecoin" / "price_data.zip": DATA / "ERC20-stablecoins" / "price_data.zip",
        SAMPLES / "stablecoin" / "token_daily_metrics_V3.csv": stablecoin_daily,
    }
    for destination, source in files.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.name == "first_order_df.csv":
            sample.to_csv(destination, index=False)
        elif source and source.is_file():
            shutil.copyfile(source, destination)
        else:
            raise FileNotFoundError(source)

    manifest = f"""# Amostras para reprodutibilidade

Este pacote contém apenas dados auxiliares para executar a demonstração. O total
dos arquivos deste diretório deve permanecer abaixo de 5.000.000 bytes.

## Conteúdo e proveniência

- `ethereum/first_order_df.csv`: histórico completo das cinco carteiras com mais
  `TxHash` distintos no CSV local, mais a carteira usada no cenário de rotina
  (`{ROUTINE_CASE_WALLET}`). É uma seleção intencional para demonstrar perfis;
  **não é uma amostra aleatória nem representativa da rede**.
- `ethereum/wallet_metadata.csv`: metadados locais das carteiras, consultados
  separadamente via RPC/ENS; a cobertura é parcial e reflete o momento da consulta.
- `market/coin_Ethereum.csv`: série diária completa disponível no arquivo original
  (2015-08-08 a 2021-07-06), fonte [Kaggle](https://www.kaggle.com/datasets/sudalairajkumar/cryptocurrencypricehistory?select=coin_Ethereum.csv).
- `stablecoin/event_data.csv`, `stablecoin/price_data.zip` e
  `stablecoin/token_daily_metrics_V3.csv`: catálogo, preços e agregação diária
  derivados do [dataset SNAP Stanford](https://snap.stanford.edu/data/ERC20-stablecoins.html).
  A agregação foi calculada em streaming a partir do arquivo V3.

## Limites de reprodução

As amostras permitem executar as células e reproduzir a demonstração em pequena
escala. Não reproduzem estatísticas calculadas sobre o CSV completo de Ethereum,
nem servem para treinamento ou avaliação estatística. Para refazer os resultados
completos, obtenha os arquivos de origem indicados em `docs/datatype-for-agents-theme.md`.
O monitor do SNAP usa valores diários agregados e não identifica carteiras.

Para regenerar os arquivos a partir dos dados locais:

```bash
python scripts/build_reproducibility_samples.py
```
"""
    manifest_path = SAMPLES / "README.md"
    manifest_path.write_text(manifest, encoding="utf-8")
    total = sum(p.stat().st_size for p in SAMPLES.rglob("*") if p.is_file())
    if total > MAX_BUNDLE_BYTES:
        raise ValueError(f"Pacote excedeu 5 MB: {total:,} bytes")
    return total


if __name__ == "__main__":
    print(f"Pacote gerado: {build():,} bytes (limite: {MAX_BUNDLE_BYTES:,})")
