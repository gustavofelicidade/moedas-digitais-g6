# oonca-operator-on-chain-agent

Até o momento, o agente poderia atuar principalmente como um agente de **monitoramento, análise e recomendação** de operações on-chain.

Com os dados disponíveis, ele poderia:

- identificar carteiras mais ativas;
- distinguir EOAs de contratos;
- calcular taxa de erro por carteira;
- detectar concentração de volume;
- encontrar padrões repetitivos ou possíveis sinais de automação;
- monitorar carteiras com muitos destinos;
- calcular primeira e última atividade;
- gerar alertas para comportamentos anômalos;
- ranquear carteiras por risco operacional;
- recomendar investigação de determinadas transações;
- produzir relatórios de atividade por carteira.

Um fluxo possível seria:

```text
transações on-chain
        ↓
perfil das carteiras
        ↓
detecção de padrões e anomalias
        ↓
score de risco
        ↓
alerta ou recomendação
```

Por exemplo, o agente poderia dizer:

> “A carteira X realizou 8.744 operações, interagiu com 48 destinos, possui taxa de erro de 71,45% e apresenta padrão concentrado de atividade. Recomenda-se revisão manual.”

Isso seria uma recomendação baseada em dados, não uma acusação de fraude.

O agente ainda não consegue, com segurança:

- afirmar quem é o operador da carteira;
- identificar a região geográfica do operador;
- afirmar que uma carteira pertence a um agente de IA;
- classificar `isError` como fraude;
- saber qual protocolo foi utilizado;
- votar em governança;
- executar transações;
- movimentar fundos;
- assinar operações.

Para executar operações reais, seriam necessários contratos/protocolos específicos, regras de risco, uma carteira com capacidade de assinatura, limites de valor e, idealmente, aprovação humana. Portanto, o estágio atual é mais adequado para um agente de **observação, auditoria e apoio à decisão**, não para um agente autônomo que movimenta ativos.

O agente seria mais útil **imediatamente antes da assinatura ou execução de uma operação**, mas não necessariamente exigiria revisão humana para cada compra.

### Quando ele seria acionado?

Antes de operações como:

- transferência de ETH ou stablecoins;
- swap em uma DEX;
- depósito ou saque em protocolo DeFi;
- empréstimo ou liquidação;
- mint ou burn de stablecoin;
- interação com contrato novo;
- voto de governança;
- movimentação acima de determinado limite.

O fluxo seria:

```text
operador ou sistema cria a operação
              ↓
agente analisa destino, valor, contrato e histórico
              ↓
agente calcula risco e verifica políticas
              ↓
aprova, bloqueia ou solicita revisão humana
              ↓
transação é assinada e enviada
```

### Seria para cada compra?

Tecnicamente, poderia analisar cada operação, mas a resposta do agente poderia variar:

- operação pequena e conhecida: aprovar automaticamente;
- contrato conhecido, mas valor alto: aprovar com alerta;
- carteira nova ou contrato não verificado: exigir revisão;
- taxa de erro ou comportamento anômalo: bloquear;
- operação incompatível com a política: impedir assinatura.

Assim, o agente funcionaria como um **filtro de risco antes da execução**, e não necessariamente como um aprovador humano de cada transação.

### Como seria usado no hackathon?

Para o hackathon, o mais realista seria apresentar um protótipo que:

1. recebe uma operação hipotética;
2. consulta o histórico da carteira;
3. verifica se a carteira é EOA ou contrato;
4. calcula volume, frequência, contrapartes e taxa de erro;
5. gera um score de risco;
6. retorna uma decisão:

```text
APPROVE
REVIEW
BLOCK
```

Exemplo:

```json
{
  "wallet": "0x...",
  "operation": "transfer",
  "amount": 2500,
  "wallet_type": "eoa",
  "historical_error_rate": 0.18,
  "risk_score": 0.72,
  "decision": "REVIEW",
  "reasons": [
    "valor acima do padrão histórico",
    "destinatário nunca utilizado",
    "carteira possui alta taxa de falha"
  ]
}
```

### Seria integrado ao sistema da FGV?

Provavelmente não diretamente. A menos que os organizadores forneçam uma API, carteira, protocolo ou ambiente de teste, o projeto deveria ser apresentado como uma **camada independente de monitoramento e controle**.

Uma integração real poderia ocorrer entre:

```text
sistema financeiro/tesouraria
        ↓
agente de risco
        ↓
carteira ou serviço de assinatura
        ↓
RPC Ethereum
        ↓
blockchain
```

No escopo atual, o agente ainda não tem dados suficientes para analisar uma operação pendente em tempo real, porque faltam informações como contrato chamado, método, calldata, gas e valor em USD. O dataset atual permite principalmente uma análise histórica e um protótipo de decisão baseado no comportamento passado das carteiras.