# Pharos Arbitrage Scanner Command Reference & Schema Specification

This document details the command interfaces, parameters, output schemas, and status codes for `pharos-arbitrage-scanner`.

---

## 1. CLI Commands

### 1.1 `scan`
Scans verified on-chain push feeds from Chainlink Self-Managed Feeds Cache on Pharos RPC (Chain ID 1672), audits AMM liquidity deployment on Pharos Atlantic Testnet (Chain ID 688689), and queries live Atlantic network gas.

```bash
python scripts/scanner.py scan [--pair PAIR] [--volume USD] [--min-profit USD] [--max-slippage-bps BPS] [--json]
```

**Parameters**:
- `--pair` (string, optional): Specific pair to audit (e.g., `BTC/USD`, `ETH/USD`, `PROS/USD`). If omitted, scans all verified feeds.
- `--volume` (float, default: `5000.0`): Trade size in quote currency (USD).
- `--min-profit` (float, default: `5.0`): Minimum net profit in USD threshold.
- `--max-slippage-bps` (int, default: `150`): Maximum allowable price impact in basis points (150 bps = 1.5%).
- `--json` (flag): Emit machine-readable JSON output to stdout.

### 1.2 `demo`
Executes the official 4-part live truthfulness audit & mathematical verification suite:
1. **Part 1**: Queries real live push feeds from Chainlink Self-Managed Feeds Cache (`0xd9F00...`) on Pharos RPC (Chain ID 1672).
2. **Part 2**: Queries live block height and gas price from Pharos Atlantic Testnet (Chain ID 688689).
3. **Part 3**: Audits on-chain AMM contract bytecode on Atlantic Testnet (`0x` empty bytecode verified).
4. **Part 4**: Runs mathematical constant-product ($x \cdot y = k$) unit test harness using clearly labeled test fixtures (`TEST_FIXTURE_THRESHOLD_MET`).

```bash
python scripts/scanner.py demo [--json]
```

### 1.3 `live-gas`
Queries the live Pharos Atlantic Testnet RPC (`https://atlantic.dplabs-internal.com`) for current block number and `eth_gasPrice`.

```bash
python scripts/scanner.py live-gas [--json]
```

---

## 2. Production Output Data Schema (Live Scan)

### 2.1 Live Scan Result Schema (`python scripts/scanner.py scan --pair BTC/USD --json`)
```json
[
  {
    "timestamp": "2026-10-19T08:39:01.439142+00:00",
    "pair": "BTC/USD",
    "data_mode": "PRODUCTION_LIVE_AUDIT",
    "trade_volume_usd": 5000.0,
    "min_net_profit_usd": 5.0,
    "max_slippage_bps": 150,
    "reference_oracle_price": 82792.1189,
    "oracle_venue": {
      "id": "chainlink_reference_oracle",
      "name": "Chainlink Self-Managed Feeds Cache",
      "network": "Pharos RPC",
      "chain_id": 1672,
      "type": "ON_CHAIN_REFERENCE_ORACLE",
      "is_executable_pool": false,
      "contract_address": "0xd9F00c86ced2De92F6B7152b0492cb28edc4B5a8",
      "proxy_address": "0x8b5DB228Fbccf588f08B073C235254aCb6791D36",
      "proxy_verified": true,
      "reference_price_usd": 82792.1189,
      "updated_at_iso": "2026-10-19T07:45:11+00:00",
      "updated_at_epoch": 1792395911,
      "status": "HEALTHY",
      "is_available": true,
      "error": null
    },
    "amm_venue": {
      "id": "atlantic_amm_router",
      "name": "Pharos Atlantic Testnet AMM Router",
      "network": "Pharos Atlantic Testnet",
      "chain_id": 688689,
      "type": "AMM_CONSTANT_PRODUCT",
      "is_executable_pool": false,
      "deployed_pools_count": 0,
      "status": "UNAVAILABLE_NO_DEPLOYED_BYTECODE",
      "is_deployed": false,
      "router_address": "0x0000000000000000000000000000000000000000",
      "message": "No verified AMM router deployed on Atlantic Testnet (0x bytecode, fail-closed enforced)."
    },
    "gas_details": {
      "source": "LIVE_ATLANTIC_RPC",
      "rpc_url": "https://atlantic.dplabs-internal.com",
      "gas_price_wei": 10000000000,
      "gas_price_gwei": 10.0,
      "block_number": 31610751,
      "is_live": true,
      "status": "HEALTHY"
    },
    "waterfall": null,
    "decision": {
      "status": "LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY",
      "is_eligible": false,
      "reason": "Live arbitrage unavailable -- no verified liquidity. Verified Chainlink reference price is $82,792.12 on Pharos RPC (Chain ID 1672). However, reference oracles are non-executable benchmark feeds, and Pharos Atlantic Testnet (Chain ID 688689) currently has 0 deployed AMM liquidity pools or router contracts (0x bytecode). Two independent executable venue quotes are required for real arbitrage."
    }
  }
]
```

---

## 3. Decision Status Codes

| Status Code | Context | Meaning | Action Taken |
|---|---|---|---|
| `LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY` | Production Live Scan | Live oracle price verified, but Atlantic Testnet has 0 active AMM liquidity pools (`0x` bytecode). | Permanently fail-closed. Execution locked (`execution_enabled: false`). |
| `TEST_FIXTURE_THRESHOLD_MET` | Unit Test Fixture Sandbox | Synthetic math test fixture exceeds user profit threshold and satisfies slippage limits. | Test passed for math evaluation only. `is_eligible: false`. Not marked as live execution. |
| `TEST_FIXTURE_EXCESSIVE_SLIPPAGE` | Unit Test Fixture Sandbox | High-volume test fixture encounters price impact exceeding maximum allowable basis points. | Test fixture rejected for market risk protection. |
| `TEST_FIXTURE_UNPROFITABLE` | Unit Test Fixture Sandbox | Net spread after LP fees and gas is less than or equal to zero. | Test fixture discarded, friction logged. |
| `TEST_FIXTURE_BELOW_THRESHOLD` | Unit Test Fixture Sandbox | Net profit is positive but below configured threshold. | Test fixture discarded, shortfall logged. |
