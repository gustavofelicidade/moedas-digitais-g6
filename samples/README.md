# Amostras para reprodutibilidade

Este pacote contém apenas dados auxiliares para executar a demonstração. O total
dos arquivos deste diretório deve permanecer abaixo de 5.000.000 bytes.

## Conteúdo e proveniência

- `ethereum/first_order_df.csv`: histórico completo das cinco carteiras com mais
  `TxHash` distintos no CSV local, mais a carteira usada no cenário de rotina
  (`0x3cbd2e6143f057bd49ffb4c7058217a5900c35d3`). É uma seleção intencional para demonstrar perfis;
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
