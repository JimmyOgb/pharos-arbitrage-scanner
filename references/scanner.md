# Pharos Arbitrage Scanner Command Reference & Schema Specification

This document details the machine-readable command interfaces, parameters, output schemas, and error codes for `pharos-arbitrage-scanner`.

---

## 1. CLI Commands

### 1.1 `scan`
Scans all registered trading pairs across configured venues (PharosSwap V2, Lighthouse DEX, Pyth Oracle), netting fees, slippage, and live network gas.

```bash
python scripts/scanner.py scan [--volume USD] [--min-profit USD] [--max-slippage-bps BPS] [--json]
```

**Parameters**:
- `--volume` (float, default: `5000.0`): Trade size in quote currency (USD).
- `--min-profit` (float, default: `5.0`): Minimum net profit in USD required to trigger `ELIGIBLE_FOR_EXECUTION`.
- `--max-slippage-bps` (int, default: `150`): Maximum allowable price impact in basis points (150 bps = 1.5%).
- `--json` (flag): Emit machine-readable JSON output to stdout.

### 1.2 `demo`
Runs a side-by-side benchmark test across four canonical market conditions:
1. `profitable_arb`: Wide spread (2.40%) sufficient to absorb fees, slippage, and gas $\to$ **Eligible**.
2. `slippage_eroded`: Thin spread (0.80%) eaten by AMM price impact $\to$ **Skipped (Unprofitable)**.
3. `gas_eroded`: Micro-spread (0.15%) wiped out by network gas $\to$ **Skipped (Below Threshold)**.
4. `inverted_spread`: Efficient/inverted market (-1.96%) $\to$ **Skipped (Negative Spread)**.

```bash
python scripts/scanner.py demo [--json]
```

### 1.3 `live-gas`
Queries the live Pharos Atlantic Testnet RPC (`https://atlantic.dplabs-internal.com`) for current block number and `eth_gasPrice`.

```bash
python scripts/scanner.py live-gas
```

---

## 2. Output Data Schemas

### 2.1 Scan Result Schema
```json
{
  "timestamp": "2026-10-19T08:30:00Z",
  "block_number": 31608157,
  "gas_price_gwei": 10.0,
  "pair": "PHRS/USDC",
  "volume_usd": 5000.0,
  "buy_venue": {
    "id": "pharos_swap",
    "name": "PharosSwap V2",
    "spot_price": 2.50,
    "effective_price": 2.5126,
    "fee_usd": 15.0,
    "price_impact_bps": 50.4
  },
  "sell_venue": {
    "id": "lighthouse_dex",
    "name": "Lighthouse DEX",
    "spot_price": 2.56,
    "effective_price": 2.5448,
    "fee_usd": 12.66,
    "price_impact_bps": 59.4
  },
  "oracle_benchmark_price": 2.52,
  "waterfall": {
    "gross_spread_usd": 120.0,
    "gross_spread_pct": 2.40,
    "buy_fee_usd": 15.0,
    "sell_fee_usd": 12.66,
    "total_fees_usd": 27.66,
    "buy_slippage_usd": 25.07,
    "sell_slippage_usd": 29.83,
    "total_slippage_usd": 54.90,
    "gas_units_total": 295000,
    "gas_cost_phrs": 0.00295,
    "gas_cost_usd": 0.007375,
    "total_friction_usd": 82.567375,
    "net_profit_usd": 37.432625,
    "net_profit_pct": 0.7487
  },
  "decision": {
    "status": "ELIGIBLE_FOR_EXECUTION",
    "reason": "Net profit $37.43 exceeds threshold $5.00 and max slippage 109.8 bps < 150 bps.",
    "is_executable": true
  }
}
```

---

## 3. Decision Status Codes

| Status Code | Meaning | Action Taken |
|---|---|---|
| `ELIGIBLE_FOR_EXECUTION` | Net profit $\ge$ threshold AND slippage $\le$ limit | Opportunity surfaced as actionable, calldata prepared |
| `SKIPPED_NEGATIVE_SPREAD` | Sell price $\le$ Buy price | Discarded immediately, zero costs evaluated |
| `SKIPPED_UNPROFITABLE_AFTER_COSTS` | Gross spread positive, but net profit $< 0$ | Discarded, cost breakdown logged |
| `SKIPPED_BELOW_MIN_PROFIT_THRESHOLD` | Net profit $> 0$, but below user's threshold | Discarded, shortfall logged |
| `SKIPPED_EXCESSIVE_SLIPPAGE` | Net profit meets threshold, but price impact exceeds limit | Discarded for market risk protection |
