# OONCA — risco e responsabilização em operações on-chain

Projeto do Grupo 6 para o 7º Datathon de Moedas Digitais FGV.

**Tema:** Agentes de IA e operações on-chain: stablecoins, governança e responsabilização.

O projeto explora como uma organização pode revisar uma operação on-chain antes da assinatura e registrar as evidências, regras e responsáveis pela decisão. O protótipo não assina nem envia transações.

## Problema e pergunta

A blockchain registra endereços, valores, horários e resultados técnicos. Por si só, ela não registra qual operador, agente, versão de modelo ou política autorizou uma operação. O OONCA demonstra uma camada de triagem pré-assinatura e trilha de auditoria para expor essa lacuna.

> Como um agente de apoio pode sinalizar riscos observáveis antes da assinatura e registrar as evidências e responsabilidades associadas à decisão?

## O que foi construído

### OONCA: triagem pré-assinatura

O fluxo LangGraph em `app/agent/` reúne histórico de carteira, calcula sinais comportamentais, aplica regras determinísticas e gera uma explicação. Uma análise pode resultar em `APPROVE`, `REVIEW` ou `BLOCK`; o LLM é opcional e não decide o resultado. O score é heurístico, não uma probabilidade de fraude.

Com o dataset local completo, a EDA usa 254.973 linhas de transações Ethereum, 102.149 `TxHash` distintos, 37.241 carteiras de origem e uma janela de 30/11/2016 a 18/05/2019. `isError == 1` aparece em 6,13% das linhas e indica falha operacional, não fraude. O dataset contém linhas repetidas por `TxHash`; frequência e cadência precisam deduplicar de acordo com a métrica.

Os metadados locais cobrem 500 carteiras e foram consultados posteriormente via RPC/ENS. Não identificam necessariamente o operador histórico. A unidade de `Value` não é confirmada na documentação disponível; por isso não tratamos esse campo como valor USD nem como prova de fraude.

### Monitor SNAP de stablecoins

O notebook da entrega usa o [dataset ERC20 Stablecoins da SNAP Stanford](https://snap.stanford.edu/data/ERC20-stablecoins.html), com transferências, preços diários e eventos de mercado para USDT, USDC, DAI, UST e PAX. O V3 foi agregado por dia e token em streaming. Com um limiar exploratório de 2% de desvio intradiário de US$ 1, o painel sinalizou 179 dias-token: 177 para UST e um dia para cada USDT e PAX.

Esse resultado ilustra monitoramento retrospectivo do estresse de paridade, em especial a crise de UST em 2022. Não confirma fraude, não identifica carteiras e não fornece preço ou liquidez em tempo real. A agregação diária também não atribui o alerta a uma operação individual.

### Monitor de pump and dump

`app/agent/pump_dump.py` implementa uma trilha experimental separada com LightGBM, features de negócios e horários documentados de eventos. Ainda requer dados de trades e eventos no formato descrito em [`docs/pump-dump-agent.md`](docs/pump-dump-agent.md); o modelo não foi treinado ou avaliado com os arquivos atuais do projeto. O Kaggle `coin_Ethereum.csv` contém OHLCV diário e serve apenas como contexto de mercado, não como entrada desse detector.

## Principais achados e implicações

- Os históricos de carteiras e resultados de execução são heterogêneos; médias globais escondem diferenças entre carteiras. Quantis e cadência ajudam a organizar uma revisão, condicionados a amostra suficiente.
- Entre as 30 carteiras mais ativas, 27 acionam os limiares demonstrativos de proxy comportamental. Como não há rótulos confirmados de bots ou agentes de IA, essa proporção **não mede eficácia** e não prova automação; aponta a necessidade de calibrar regras e manter revisão humana.
- Em cenários hipotéticos executados com histórico observado, o OONCA aprova um destino recorrente de baixo valor, solicita revisão para destino novo/valor atípico e proxy de automação, e bloqueia uma violação explícita de política. Essas saídas demonstram o fluxo das regras, não uma validação de detecção de fraude.
- A trilha de auditoria proposta registra operação, política, operador, evidências e hash SHA-256. O protótipo demonstra o formato técnico; uma instituição ainda precisaria vincular esses campos a identidades, aprovações e processos reais.

## Arquitetura

```text
app/
├── agent/          # grafo OONCA e monitor independente de pump and dump
├── audit/          # trilha de decisão e hash de evidências
├── features/       # comportamento de carteiras e monitor SNAP
├── ingestion/      # datasets, schemas e repositórios
├── models/         # política de risco e classificador LightGBM experimental
├── nodes/          # etapas LangGraph
├── tools/          # consultas auxiliares
└── visualization/  # painel de decisão
```

## Executar

Requer Python 3.12 ou compatível com as dependências listadas em `requirements.txt`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
jupyter lab
```

Abra `notebooks/entregavel_datathon_fgv.ipynb`. O notebook usa os datasets completos em `data/` quando presentes; caso contrário, usa `samples/` e identifica essa amostra como não representativa. Ele não cria dados sintéticos silenciosamente.

Para executar uma análise do agente pela CLI, com os dados completos em `data/`:

```bash
python -m app.agent \
  --from 0x3cbd2e6143f057bd49ffb4c7058217a5900c35d3 \
  --to 0x8d12a197cb00d4747a1fe03395095ce2a5cc6819 \
  --amount 0.001 \
  --operator-id demo \
  --as-of 2019-05-19T00:00:00Z \
  --no-llm
```

Para uma explicação via OpenRouter, configure `OPENROUTER_API_KEY` no ambiente ou em `.env` e remova `--no-llm`. O agente continua responsável por calcular a recomendação; o LLM só explica as evidências recebidas.

## Reprodutibilidade e dados

O guia do Datathon recomenda materiais suplementares para transparência e reprodutibilidade, embora não sejam obrigatórios. Por isso, o repositório inclui `samples/`, um pacote determinístico com menos de 5 MB, e `scripts/build_reproducibility_samples.py` para recriá-lo a partir dos arquivos locais.

A amostra de transações preserva o histórico completo das cinco carteiras com mais `TxHash` distintos e da carteira usada no cenário de rotina. É uma seleção de casos, não uma amostra estatística da rede. Permite executar os fluxos e inspecionar exemplos, mas os resultados agregados da entrega foram calculados com o CSV local completo; a amostra não os reproduz.

| Fonte | Uso no projeto | Arquivos completos locais |
|---|---|---|
| [Ethereum Transactions for Fraud Detection (Kaggle)](https://www.kaggle.com/datasets/chaitya0623/ethereum-transactions-for-fraud-detection) | histórico de transações para EDA e perfil de carteiras | `data/Ethereum-Transactions-for-Fraud-Detection/` |
| [ERC20 Stablecoins (SNAP Stanford)](https://snap.stanford.edu/data/ERC20-stablecoins.html) | preços, eventos e transferências para monitoramento retrospectivo | `data/ERC20-stablecoins/` |
| [Cryptocurrency Historical Prices (Kaggle)](https://www.kaggle.com/datasets/sudalairajkumar/cryptocurrencypricehistory?select=coin_Ethereum.csv) | contexto diário de preço/volatilidade do ETH | `data/Coin_Ethereum/coin_Ethereum.csv` |
| `wallet_metadata.csv` | enriquecimento parcial via RPC/ENS | `data/wallet_metadata.csv` |

Os arquivos originais e grandes ficam em `data/`, ignorado pelo Git. Para regenerar as amostras, coloque as fontes nos caminhos acima e execute:

```bash
python scripts/build_reproducibility_samples.py
```

O manifesto em [`samples/README.md`](samples/README.md) descreve seleção, proveniência e limitações. Para reproduzir resultados completos, obtenha os arquivos-fonte indicados na tabela e siga as instruções do notebook.

## Limitações

- Os dados não identificam de forma confiável agentes de IA, operadores ou intenção fraudulenta.
- Proxies temporais não distinguem automaticamente bots de serviços legítimos, exchanges ou contratos.
- O monitor SNAP é histórico e diário; não está integrado à decisão pré-assinatura nem usa liquidez contemporânea.
- O monitor de pump and dump precisa de trades e rótulos de eventos apropriados; OHLCV diário não atende ao contrato de dados.
- Não há dados de governança integrados nesta versão.
- O agente não assina, transmite ou bloqueia transações on-chain; qualquer revisão/decisão final é humana.

## Roteiro da apresentação (10 slides)

1. **Uma operação on-chain precisa de contexto e responsável**
2. **O livro-razão mostra o que aconteceu, não quem autorizou**
3. **Pergunta do projeto: como revisar antes da assinatura?**
4. **Dados distintos para históricos, stablecoins e mercado**
5. **O histórico Ethereum mostra concentração, repetição e falhas**
6. **Proxies de automação sinalizam revisão, não identidade**
7. **OONCA transforma evidências em uma decisão auditável**
8. **A crise de UST testa o monitor retrospectivo de paridade**
9. **Pump and dump: uma trilha complementar ainda sem trades**
10. **O que aprendemos, limites e próximos passos**

## Referências

- [Guia de abertura e critérios do 7º Datathon](docs/Desafio_de_Dados_FGV_7_Abertura.pdf)
- [Descrição do OONCA e escopo](docs/operator-on-chain-agent.md)
- [Tipos de dados e proveniência](docs/datatype-for-agents-theme.md)
- [Monitor de pump and dump](docs/pump-dump-agent.md)
- [Notebook de entrega](notebooks/entregavel_datathon_fgv.ipynb)
- [Notebook exploratório](notebooks/eda-gustavo.ipynb)
