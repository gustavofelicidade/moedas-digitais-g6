# OONCA — operador on-chain com apoio de IA

## Tema definido

**Agentes de IA e operações on-chain: stablecoins, governança e responsabilização.**

O OONCA será apresentado como um agente de monitoramento e apoio à decisão para operadores que preparam operações on-chain. Ele reúne evidências, calcula indicadores determinísticos e explica os motivos para uma recomendação. Nesta etapa, não assina nem envia transações.

## O que o primeiro protótipo faz

Com `first_order_df.csv` e `wallet_metadata.csv`, o protótipo:

- perfila o histórico de uma carteira de origem;
- verifica se o destino já apareceu no histórico observado;
- calcula taxa histórica de `isError`, valores e atividade;
- acrescenta tipo de carteira quando existe metadata;
- pontua alguns sinais e retorna `APPROVE`, `REVIEW` ou `BLOCK`;
- usa opcionalmente o LLM para explicar a decisão calculada pelas regras.

O protótipo **não resolve nem confirma uma fraude específica**. A pontuação atual é uma heurística demonstrativa, não uma probabilidade de fraude. `isError` representa falha/reversão conforme o dataset, não fraude. `BLOCK` só é retornado quando uma regra explícita de limite configurada pelo usuário é violada. `APPROVE` significa apenas que as regras atuais não solicitaram revisão.

O dataset cobre transações Ethereum de 2016 a 2019 e não identifica token, stablecoin, protocolo, função do contrato, gas, valor em USD, fraude confirmada, agente de IA ou operador. `wallet_type` e ENS foram consultados posteriormente, no estado atual da rede. Portanto, o primeiro protótipo serve para demonstrar uma triagem baseada em histórico, não para afirmar comportamento contemporâneo nem detectar agentes de IA.

## Quais abusos ou fraudes são alvos futuros

São hipóteses de detecção, condicionadas a dados apropriados. Um alerta aponta um padrão compatível com risco; investigação adicional é necessária antes de chamá-lo de fraude.

| Hipótese | Evidências/dados necessários | Estado |
|---|---|---|
| Transferência incomum ou destino novo | histórico por carteira, valor, destinatário e política de limite | Triagem parcial já existe para ETH |
| Uso anômalo de stablecoin ou movimentação em torno de depeg | eventos ERC-20, identificação de token e série histórica de preço/liquidez | Ainda sem dados |
| Wash trading ou volume artificial em DEX | swaps decodificados, pool/token, participantes e sequência temporal | Ainda sem dados |
| Ataque ou captura de governança | propostas, votos, poder delegado, delegações, quórum e execução | Ainda sem dados |
| Rug pull, exploit ou desvio de fundos | eventos/trace de contratos, fluxo de ativos e rótulos de incidentes validados | Ainda sem dados |
| Automação suspeita ou operação de agente | sequência temporal, repetição, calldata, identificação validada e logs de decisão | Apenas proxies comportamentais; não prova IA |
| Falha operacional ou violação de política | status de execução, gas, limites, aprovação e identidade do operador | Erros históricos parcialmente disponíveis; política/auditoria ausentes |

## MVP recomendado para o hackathon

Construir uma demonstração de **revisão prévia de uma operação com stablecoin**. O operador informa carteira de origem, destino, token, valor e operação proposta. O agente retorna evidências observadas, indicadores, recomendação e explicação auditável. Inicialmente, a recomendação deve priorizar `REVIEW` quando faltam dados ou contexto.

Fluxo desejado:

```text
operação proposta
       ↓
validação do formato e identificação do token/operação
       ↓
consulta de histórico e metadata disponível
       ↓
features e regras explícitas de risco
       ↓
APPROVE / REVIEW / BLOCK + evidências e limitações
       ↓
explicação em linguagem natural pelo LLM
```

O LLM explica os resultados recebidos; não cria rótulos de fraude, não inventa evidência e não substitui as regras de decisão. Cada análise deve preservar fonte, período coberto, timestamp de consulta, regra aplicada e dados ausentes.

## Trabalho que pode começar agora

### Trilha Bruno — features e contrato de dados

Implementar em `app/features/` funções determinísticas e independentes de LangGraph para calcular, por carteira e janela temporal:

1. volume e número de operações;
2. destinos únicos e proporção de destinos novos;
3. taxa de erro, com denominador e quantidade mínima de observações;
4. intervalo entre transações, atividade por janela e concentração temporal;
5. mediana e percentis do valor, sem converter para USD sem preço e unidade confirmados.

As funções recebem DataFrame com colunas canônicas e devolvem valores e metadados da janela usada. Separar cálculo de features de score/política; não atribuir fraude, IA, identidade ou região. Usar `first_order_df.csv` para validar a integração inicial. Registrar denominadores, tratamento de linhas repetidas e dados ausentes.



### Trilha de dados — primeira extensão stablecoin

Em paralelo, escolher uma rede e um protocolo ou stablecoin para delimitar a coleta. Procurar ao menos:

- transferências ERC-20 com timestamp/bloco, hash, `from`, `to`, contrato do token e valor bruto;
- metadados do token (decimais, símbolo, endereço e rede);
- preço histórico em USD para a mesma rede temporal;
- se o foco for DeFi, eventos de swap/pool ou chamadas decodificadas;
- documentação de fonte, licença, janela temporal, extração e cobertura.

Não é necessário baixar todos os conjuntos de dados antes de avançar. Primeiro validar um recorte pequeno e reproduzível. A integração não deve chamar qualquer transferência de stablecoin de “compra”: a operação precisa ser classificada por evento/contrato.

## Papéis sugeridos para os diretórios

- `app/ingestion/`: leitura, normalização e DTOs/contratos de dados.
- `app/features/`: medidas e sinais derivados, sem política de decisão.
- `app/models/`: modelos estatísticos ou de ML treinados e avaliados com dados rotulados.
- `app/tools/`: adaptadores que nodes podem invocar (perfil de carteira, consulta de protocolo etc.).
- `app/nodes/`: passos LangGraph para coleta, análise, decisão e explicação.
- `app/agent/`: composição do grafo e interface pública/CLI.
- `app/visualization/`: gráficos e visualização de evidências.

## Critérios para chamar uma saída de detector

Antes de apresentar qualquer componente como detector de fraude, definir evento-alvo e rótulo verificável, período de observação, unidade analítica, features disponíveis no momento da decisão, baseline, métricas de avaliação e custo de falsos positivos. Sem rótulos confiáveis, apresentar como monitoramento de anomalias ou triagem de risco operacional.

## Evolução posterior

1. Completar features comportamentais e harmonizar schema.
2. Adicionar dataset de eventos de stablecoin e preço histórico alinhado.
3. Criar regras explicáveis de operação com stablecoins e avaliar alertas.
4. Adicionar dados de governança em trilha separada.
5. Acrescentar logs de agente, versão de modelo, política e aprovação humana para responsabilização.
6. Só estudar execução/assinatura após existir integração explícita, limites, revisão e ambiente de teste.
