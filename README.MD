# 7º Datathon de Moedas Digitais FGV — Grupo 6

Projeto do **Grupo 6: Rio de Janeiro I** para o 7º Desafio de Dados (Datathon) de Moedas Digitais da FGV, realizado pelo Centro de Estudos FGV Digital Finance / FGV EESP.

## Equipe

- Arick Jurdan dos Reis — `arickjurdan.20221@poli.ufrj.br`
- Bruno Lins — `linsbruno21@gmail.com`
- Giulia Tafuri Rodrigues da Silva — `giutafuri@gmail.com`
- Gustavo Felicidade da Costa — `gustavofelicidade@outlook.com`

## Contexto do desafio

O tema do Datathon é livre. A escolha será avaliada pela pertinência e pelo caráter inovador da solução. Entre os temas sugeridos no material de abertura estão:

- comovimentos entre criptomoedas e outros ativos;
- formação e performance de carteiras;
- índices de atenção e sentimento;
- sustentabilidade energética de criptomoedas;
- artificialidades, fraudes e movimentos anormais;
- impactos de avanços e retrocessos regulatórios;
- CBDCs e sua interpelação com tokens descentralizados;
- DeFi, NFTs, tokenização de ativos do mundo real (RWAs), stablecoins e Crypto Treasury companies;
- blockchain e IA agêntica;
- previsões de preço, volume e volatilidade;
- segurança, ataques, comportamento de mercado e melhorias de protocolos.

## Tema em avaliação pelo Grupo 6

### Tema principal provisório

**Agentes de IA e operações on-chain: stablecoins, governança e responsabilização.**

Pergunta inicial:

> Como agentes de IA que executam ou recomendam operações on-chain alteram o perfil de atividade, risco e responsabilização em protocolos que movimentam stablecoins e participam de governança?

O trabalho deverá distinguir evidências de automação simples, bots, multisigs e agentes de IA. Não devemos atribuir autonomia ou uso de IA a uma carteira sem evidência observável.

### Tema alternativo

**Moedas Digitais de Bancos Centrais (CBDCs) e interpelação com tokens descentralizados.**

A decisão final do grupo ainda está pendente. O notebook atual está preparado para iniciar a investigação do tema de agentes de IA e operações on-chain, mas poderá ser adaptado caso o grupo escolha CBDCs.

## Plano de investigação atual

As hipóteses iniciais são:

1. agentes mais automatizados podem concentrar volume, número de operações ou poder de voto em poucas carteiras;
2. falhas, reversões, custos de gas e interações com contratos não verificados podem se concentrar em agentes, protocolos ou períodos específicos;
3. a rastreabilidade de uma ação até o agente, carteira, modelo, operador ou política pode variar entre operações;
4. operações com stablecoins e votos de governança podem apresentar padrões diferentes dos demais fluxos on-chain.

Estas hipóteses serão revisadas depois da escolha da fonte de dados, da rede e da unidade de observação.

## Dados

Ainda não há dataset no repositório. Para o tema principal, o conjunto ideal deve conter ações on-chain ou eventos de governança, com o maior número possível dos seguintes campos:

| Bloco | Campos desejáveis | Finalidade |
|---|---|---|
| Tempo e rede | `timestamp`, `chain`, `block_number` | período, sazonalidade e comparação entre redes |
| Identidade | `agent_id`, `wallet_from`, `wallet_to`, `operator_id` | rastreabilidade e concentração |
| Ação | `tx_hash`, `action_type`, `protocol`, `contract_address`, `method` | classificação das operações |
| Valor e custo | `asset`, `amount`, `amount_usd`, `gas_usd` | volume, custo e stablecoins |
| Resultado | `success`, `status`, `error`, `reverted` | falhas e risco operacional |
| Governança | `proposal_id`, `vote`, `voting_power`, `delegated_power` | participação e concentração de poder |
| Responsabilização | `model_version`, `policy_id`, `approval_id`, `human_review`, `trigger` | auditoria e atribuição |

O material de abertura sugere, entre outras possibilidades, dados históricos e intradiários do Kaggle, dados de opções da Deribit, CoinMarketCap, CoinGecko e APIs de exchanges como a Binance. Para o tema de agentes, também será necessário buscar dados indexados de transações, eventos de contratos e governança, observando licença, limites de uso e reprodutibilidade.

## Estrutura do repositório

```text
.
├── docs/
│   └── Desafio_de_Dados_FGV_7_Abertura.pdf
├── notebooks/
│   └── eda-gustavo.ipynb
├── data/                 # dataset local; não versionar dados sensíveis ou muito grandes
├── requirements.txt
└── README.MD
```

### Notebook atual

[`notebooks/eda-gustavo.ipynb`](notebooks/eda-gustavo.ipynb) contém uma EDA data-ready que:

- formula a pergunta e as hipóteses iniciais;
- documenta o contrato de dados;
- procura CSV, Parquet e JSON em `data/`;
- padroniza aliases de colunas;
- diagnostica tipos, valores ausentes, duplicidades e período;
- calcula métricas de atividade, stablecoins, custos, falhas e rastreabilidade;
- prepara análises de concentração e atividade temporal;
- explicita limitações quando o dataset ainda não foi carregado.

## Como executar

### Protótipo OONCA

O agente em `app/agent` avalia uma operação **hipotética** antes da assinatura. A sequência LangGraph é `collect_evidence → assess_risk → explain`: lê `first_order_df.csv` em blocos, consulta `wallet_metadata.csv`, calcula regras de triagem e opcionalmente pede ao OpenRouter uma explicação em português. O LLM não decide o resultado. A pontuação é uma heurística demonstrativa, não uma probabilidade de fraude.

Na raiz do projeto, após instalar `requirements.txt`:

```bash
python -m app.agent --from 0xc2d7cf95645d33006175b78989035c7c9061d3f9 --to 0x002f0c8119c16d310342d869ca8bf6ace34d9c39 --amount 0.5 --no-llm
```

Remova `--no-llm` para usar a chave `OPENROUTER_API_KEY` já configurada em `.env`. O modelo padrão é `deepseek/deepseek-v4.1-flash-1017`; a variável `OPENROUTER_MODEL` permite trocá-lo. Use `--as-of 2018-01-01T00:00:00Z` para simular a análise apenas com transações anteriores à data e `--max-eth 1` para uma regra explícita de bloqueio. O [notebook do agente](notebooks/agent_oonca.ipynb) importa as mesmas funções e mostra um gráfico da decisão.

O CSV representa uma amostra histórica, com linhas que podem repetir `TxHash`. A entrada atual só suporta comparar valores de transferências ETH com o campo `Value`; essa unidade deve ser confirmada com a documentação de origem do dataset antes de uso operacional. ENS e `wallet_type` são metadados consultados posteriormente às transações. Faltam informações de token, contrato chamado, gas, operador, rótulo de fraude e autorização humana. `APPROVE` significa apenas que as regras deste protótipo não pediram revisão. O agente não assina nem envia transações.

Na raiz do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Depois, abra o notebook em Jupyter ou VS Code e coloque o dataset em `data/`:

```bash
jupyter lab
```

O notebook seleciona automaticamente o primeiro arquivo compatível encontrado em `data/`. Para escolher um arquivo específico, defina `DATA_FILE` na célula de ingestão.

## Entrega

- formato: apresentação em PDF;
- limite: até 10 slides;
- prazo: **8 de novembro de 2026, até 23h59 (horário de Brasília)**;
- envio: [formulário oficial](https://forms.gle/gpF8ZbTd5QM1rGmW9);
- código e materiais suplementares são recomendados para transparência e reprodutibilidade, embora não sejam obrigatórios.

## Critérios de avaliação

Segundo o material de abertura, a banca avaliará:

- relevância do problema;
- adequação metodológica;
- qualidade da solução e do material apresentado;
- criatividade;
- análise das implicações dos resultados — o que aprendemos e por que isso é importante.

## Cronograma

| Data | Evento |
|---|---|
| 8/11/2026, 23h59 | encerramento do formulário de envio |
| 12/11/2026 | divulgação das equipes finalistas |
| 16/11/2026 | apresentação da final, online |
| 19/11/2026 | divulgação das equipes vencedoras |
| 25/11/2026, 19h | apresentação das soluções vencedoras no 2º Blockchain Day FGV, em São Paulo |

## Próximos passos

- [ ] Confirmar o tema final entre agentes de IA/on-chain e CBDCs.
- [ ] Definir a unidade de observação, a rede e a janela temporal.
- [ ] Selecionar uma fonte de dados com licença, cobertura e acesso adequados.
- [ ] Registrar fonte, data de extração, filtros e limitações.
- [ ] Executar a EDA com o primeiro dataset em `data/`.
- [ ] Transformar os achados em uma narrativa de até 10 slides.
- [ ] Solicitar mentoria, se necessário, pelo e-mail `digitalfinance@fgv.br`, dando crédito aos mentores na apresentação final.

## Referências do desafio

- [Material de abertura do 7º Datathon](docs/Desafio_de_Dados_FGV_7_Abertura.pdf)
- [Página do evento da FGV EESP](https://eesp.fgv.br/evento/7o-desafio-de-dados-datathon-de-moedas-digitais-da-fgv-eesp)
- [E-book Criptofinanças Avançadas — FGV EESP](https://eesp.fgv.br/sites/eesp.fgv.br/files/criptofinancas_avancadas_-_fgv_eesp_-_ed._2024_1.pdf)
