Com base no EDA, o ideal é buscar dados que permitam relacionar **tempo, carteira, transação, protocolo, ativo, resultado e evidências de automação/governança**.

### 1. Transações on-chain

Pesquise por:

- `Ethereum transactions dataset CSV` -> Gus baixou: http://kaggle.com/datasets/chaitya0623/ethereum-transactions-for-fraud-detection
- `EVM transaction history dataset`.  -> Dados grandes:  https://huggingface.co/collections/BlockDB/blockdb-full-evm-research-datasets-10-years
- `Ethereum transaction traces dataset`
- `blockchain transactions with gas price and receipt status`
- `Ethereum wallet transaction dataset`
- `multi-chain on-chain transactions dataset`
- `Google BigQuery public crypto Ethereum transactions`
- `Dune Ethereum transactions dataset`
- `Flipside Crypto Ethereum transactions`

Campos importantes:

`timestamp`, `chain`, `block_number`, `tx_hash`, `from`, `to`, `gas_used`, `gas_price`, `transaction_fee`, `status`, `input_data`.

### 2. Eventos de contratos e protocolos DeFi

Esses dados ajudam a identificar `action_type`, `protocol`, `contract_address` e `method`.

- `DeFi protocol events dataset`
- `Ethereum smart contract event logs dataset`
- `Uniswap swaps dataset`
- `Aave lending transactions dataset`
- `Compound protocol events dataset`
- `MakerDAO transactions dataset`
- `Curve Finance swaps dataset`
- `DeFi transactions with decoded function calls`
- `Ethereum ERC-20 transfer events dataset`
- `Dune decoded DeFi events`

### 3. Stablecoins

São centrais para o tema do projeto.

- `stablecoin transactions dataset`
- `USDC on-chain transactions dataset`
- `USDT Ethereum transfer history dataset`
- `DAI transactions blockchain dataset`
- `stablecoin volume by blockchain`
- `stablecoin mint burn events dataset`
- `stablecoin depeg events dataset`
- `stablecoin supply and circulation historical data`
- `stablecoin liquidity pools dataset`
- `stablecoin transactions with USD value`

Stablecoins para incluir:

`USDT`, `USDC`, `DAI`, `FDUSD`, `USDe`, `PYUSD`, `TUSD`.

### 4. Governança e votação

Para testar concentração, coordenação e poder delegado:

- `DAO governance votes dataset`
- `on-chain governance proposals dataset`
- `Snapshot governance votes dataset`
- `Tally DAO votes API dataset`
- `Compound governance proposals and votes`
- `MakerDAO governance votes dataset`
- `Aave governance votes dataset`
- `Uniswap governance votes dataset`
- `DAO voting power delegation dataset`
- `governance proposal execution transactions`
- `delegated voting power blockchain dataset`

Campos desejáveis:

`proposal_id`, `voter`, `vote`, `voting_power`, `delegated_power`, `proposal_start`, `proposal_end`, `execution_tx`.

### 5. Bots, automação e agentes

Aqui provavelmente será mais difícil encontrar dados diretamente rotulados como “agente de IA”. Pesquise também por proxies de automação:

- `blockchain trading bots dataset`
- `DeFi arbitrage bots transactions dataset`
- `MEV bot transactions dataset`
- `MEV-Boost relay data`
- `flashbots Ethereum dataset`
- `Ethereum sandwich attacks dataset`
- `DEX arbitrage transactions dataset`
- `automated market maker bot addresses`
- `on-chain bot detection dataset`
- `crypto wallet behavior classification dataset`
- `smart contract automation transactions`
- `AI agents blockchain transactions`
- `autonomous agents on-chain dataset`
- `LLM agents blockchain transactions`
- `crypto trading agent transaction logs`

Possíveis evidências indiretas de automação:

- operações em alta frequência;
- padrões repetitivos;
- execução em horários contínuos;
- chamadas a contratos específicos;
- arbitragem;
- uso de Flashbots;
- transações agrupadas em blocos;
- carteiras identificadas como bots por estudos ou exploradores.

### 6. Falhas, reversões e risco operacional

- `Ethereum reverted transactions dataset`
- `smart contract failed transactions dataset`
- `blockchain transaction failure rate`
- `DeFi protocol exploit dataset`
- `smart contract incident database`
- `DeFi hacks dataset`
- `Ethereum transaction errors dataset`
- `reverted smart contract calls`
- `DeFi liquidation events dataset`
- `failed governance execution transactions`
- `blockchain operational risk dataset`

Fontes relacionadas a incidentes:

- `DeFiLlama hacks dataset`
- `Rekt database DeFi exploits`
- `Ethereum security incidents dataset`
- `smart contract vulnerabilities dataset`

### 7. Preços, volume e contexto de mercado

Esses dados não respondem sozinhos à pergunta sobre agentes, mas ajudam a contextualizar as operações:

- `historical cryptocurrency prices CSV`
- `stablecoin historical prices dataset`
- `stablecoin market capitalization historical data`
- `crypto market volume historical dataset`
- `CoinGecko historical market data API`
- `Kaiko crypto market data`
- `Coin Metrics stablecoin data`
- `stablecoin depeg historical events`
- `Ethereum gas prices historical dataset`

### 8. Identidade, rótulos e classificação de carteiras

Para relacionar carteiras a exchanges, protocolos, bots ou operadores:

- `labeled Ethereum addresses dataset`
- `Ethereum wallet labels dataset`
- `blockchain address classification dataset`
- `crypto wallet entity labels`
- `Etherscan labeled addresses dataset`
- `exchange wallet addresses dataset`
- `DeFi protocol contract addresses list`
- `MEV bot address labels`
- `Ethereum smart money wallet dataset`

### 9. Dados de auditoria e responsabilização

Para os campos de `model_version`, `policy_id`, `human_review` e `operator_id`, procure por dados de sistemas de agentes, não apenas blockchain:

- `AI trading agent transaction logs`
- `autonomous trading system audit logs`
- `algorithmic trading audit trail dataset`
- `AI agent decision logs dataset`
- `human in the loop trading dataset`
- `automated trading risk control dataset`
- `model governance audit trail`
- `AI model versioning decision logs`
- `algorithmic trading approval logs`
- `policy enforcement logs autonomous agents`

Esse tipo de dado provavelmente terá de ser criado pelo próprio grupo ou obtido em estudos de caso, porque raramente aparece publicamente junto com a transação on-chain.

### Ordem de busca recomendada

Eu começaria por:

1. **Transações Ethereum ou Base**
2. **Eventos ERC-20 e operações de stablecoins**
3. **Governança de uma DAO específica**
4. **Dados de bots/MEV como proxy de automação**
5. **Falhas, gas e reversões**
6. **Dados de preços e depeg**
7. **Rótulos de carteiras**
8. **Logs de agentes e auditoria**

Uma combinação viável seria: **transações + eventos de stablecoins + governança + rótulos de carteiras + dados de falha/gas**. Se não encontrarem evidência confiável de IA, o projeto pode tratar “agentes automatizados” como uma categoria observável e deixar “agentes de IA” como limitação ou extensão futura. 