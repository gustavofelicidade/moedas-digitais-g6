# Monitor de pump and dump do OONCA

O monitor roda em um fluxo LangGraph próprio para reproduzir, em ordem cronológica, negócios de mercado fornecidos em CSV. Cada alerta indica um padrão compatível com o início de um pump. A confirmação de manipulação depende de evidência externa. A explicação é gerada localmente a partir do score e das métricas observadas.

## Dados para carregar

Coloque os arquivos locais em `data/pump_dump/`. A ingestão aceita CSV com cabeçalho. Use o mesmo identificador de mercado nos dois arquivos e informe o par completo, como `VIBE/BTC`.

| Arquivo | Campos | Cobertura |
| --- | --- | --- |
| `trades.csv` | `exchange,symbol,timestamp,price,quantity,side` | Negócios spot executados no par e na exchange de cada evento, com resolução de milissegundo ou melhor. Inclua períodos antes e depois dos eventos e períodos de atividade regular. |
| `events.csv` | `exchange,symbol,timestamp` | Horários documentados do início ou do anúncio de pumps, com eventos em períodos distintos para treino e teste. Guarde também a fonte de cada evento, por exemplo em uma coluna adicional `source`. |

- `timestamp` aceita ISO 8601 ou Unix em milissegundos. Uma data ISO sem fuso é interpretada como UTC. Preserve a ordem do feed quando negócios tiverem o mesmo timestamp.
- `price` é o preço na moeda de cotação e `quantity` é a quantidade na moeda-base. `side` indica o lado agressor (`buy` ou `sell`).
- Inclua `trade_id` quando disponível. O arquivo deve ter IDs únicos por mercado. Deduplicate registros de exportações sobrepostas antes de concatená-las.
- Use a coluna opcional `segment` para separar períodos descontínuos ou lacunas de coleta dentro de um mesmo mercado. Cada segmento pressupõe cobertura contínua. São descartadas as janelas de borda cuja cobertura completa não pode ser inferida dos timestamps. Inclua pelo menos **7 horas de histórico contínuo antes do evento** com a configuração padrão ou **50 minutos** com `--chunk-seconds 5`, mais margem para as bordas. Cubra também o fechamento da janela que contém o evento.
- O [dataset dos autores](https://github.com/SystemsLab-Sapienza/pump-and-dump-dataset#the-dataset) fornece os eventos em `pump_telegram.csv`. Para o CSV canônico, combine `date` e `hour` em UTC e converta `SYM` para `SYM/BTC`. O catálogo registra o horário do anúncio em minutos. Prefira o timestamp original ou um início revisado quando disponíveis, sobretudo para janelas de 5 segundos. Use somente eventos com negócios disponíveis no mesmo par e exchange.
- O [arquivo público da Binance](https://github.com/binance/binance-public-data#spot) disponibiliza `aggTrades`. Converta a unidade original do timestamp para o formato de entrada. Para `isBuyerMaker=true`, o agressor vendeu (`sell`). Para `false`, comprou (`buy`). No exportador dos autores, `amount` corresponde a `quantity`.

Candles OHLCV de um minuto e os CSVs de carteiras do OONCA não trazem a sequência de execuções necessária para calcular as `rush orders`.

## Execução

Na raiz do repositório, após instalar `requirements.txt`:

```bash
python -m app.agent.pump_dump label \
  --trades data/pump_dump/trades.csv --events data/pump_dump/events.csv \
  --output data/pump_dump/labeled.csv

python -m app.agent.pump_dump train \
  --trades data/pump_dump/trades.csv --events data/pump_dump/events.csv \
  --test-from 2018-10-01T00:00:00Z --model-out data/pump_dump/pump.joblib

python -m app.agent.pump_dump detect \
  --trades data/pump_dump/trades_to_score.csv --model data/pump_dump/pump.joblib \
  --output data/pump_dump/detections.csv
```

Escolha `--test-from` conforme a cobertura dos seus dados. Treino e teste precisam conter janelas positivas e negativas. `train` reporta precisão, revocação e F1 por janela após a pausa entre alertas, além de precisão média dos scores antes da pausa. O arquivo salvo contém o modelo ajustado apenas no treino. Use em `detect` o mesmo formato de negócios, com histórico suficiente. Carregue somente modelos locais confiáveis produzidos pelo comando `train`.

## Rotulagem, modelo e avaliação

- O [artigo de La Morgia et al. (2020), seção IV](https://doi.org/10.1109/ICCCN49398.2020.9209660) associa o horário de um sinal documentado à janela correspondente. Aqui, a janela UTC `[chunk_start, chunk_end)` do mesmo par e exchange recebe `label=1`. As demais recebem `0`, ou seja, ausência de evento documentado no arquivo. Um evento que não pode ser rotulado por falta de histórico causa erro. Os rótulos derivam dos eventos fornecidos, sem gerar preços artificiais.
- São calculadas nove features da seção IV e da Tabela IV, incluindo estatísticas móveis da contagem de negócios, volume cotado, preços e `rush orders`. Para a última, conta-se uma ocorrência por milissegundo com pelo menos dois fills de compra agressora. A leitura por contagem segue a Figura 6 e o [código complementar dos autores](https://github.com/SystemsLab-Sapienza/pump-and-dump-dataset/blob/master/features.py). As features são calculadas no fechamento da janela, usando o histórico até aquele fechamento.
- O classificador binário usa LightGBM com até 200 árvores, profundidade máxima 4 e até 16 folhas por árvore. Os pesos balanceados são calculados só com os rótulos do treino. O teste é cronológico, com exclusão de janelas que compartilhem histórico entre treino e teste. O score do modelo não é calibrado. Execute `train` para gerar um artefato LightGBM a partir dos seus CSVs.
- O limiar inicial de alerta é `0.5`, configurável em `train`. Após `SUSPECTED_PUMP`, o monitor suprime novos alertas por 30 minutos no mesmo par e exchange. A saída também inclui `NO_ALERT` e `COOLDOWN`. A pausa vale dentro de cada execução de `detect`.
