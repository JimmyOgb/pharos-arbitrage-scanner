# Deployment Report: Pharos Arbitrage Scanner

**Project**: `pharos-arbitrage-scanner`  
**Date**: 2026-10-19  
**GitHub Repository**: [`https://github.com/JimmyOgb/pharos-arbitrage-scanner`](https://github.com/JimmyOgb/pharos-arbitrage-scanner)  
**Latest Published Commit**: `365f5dd` (`feat: integrate FaroSwap Mainnet discovery, dual-network audit, and enhanced truthfulness dashboard`)  
**Production Live URL**: [`https://pharos-arbitrage-scanner.vercel.app`](https://pharos-arbitrage-scanner.vercel.app)  
**Preview Deployment URL**: [`https://pharos-arbitrage-scanner-c1kap1jvc-jamism123.vercel.app`](https://pharos-arbitrage-scanner-c1kap1jvc-jamism123.vercel.app)  
**Vercel Project**: `jamism123/pharos-arbitrage-scanner` (Deployment ID: `dpl_APEgJvM2BC9SeniCoPHsinULcTT8`)  
**Hosting Model**: Zero-Build Static Dashboard with Client-Side Live JSON-RPC Multi-Network Queries.

---

## 1. Verified Multi-Network Data Integrations

| Dimension | On-Chain Source | Network / Chain ID | Deployed Verified State |
|---|---|---|---|
| **Push Price Oracles** | Chainlink Self-Managed Feeds Cache (`0xd9F00c86ced2De92F6B7152b0492cb28edc4B5a8`) | Pharos Mainnet (`1672`) | **LIVE**: BTC/USD ($82,792.12), ETH/USD ($2,427.43), PROS/USD ($0.63). Benchmark reference feeds. |
| **Aggregator Proxy** | EACAggregatorProxy (`0x8b5DB228Fbccf588f08B073C235254aCb6791D36`) | Pharos Mainnet (`1672`) | **LIVE**: Direct round data and updatedAt timestamps. |
| **FaroSwap DEX** | FaroSwap Router (`0xd285e37678f07631f33eb99927eb3ff0591a12d7`) & Factory (`0x18fab...`) | Pharos Mainnet (`1672`) | **DEPLOYED (35.7 KB)**: Factory has 111 pairs, but reserves are empty/dust (< $250 total liquidity). |
| **Secondary DEX on Mainnet** | Canonical EVM router contracts | Pharos Mainnet (`1672`) | **NOT DEPLOYED (0x Bytecode)**: 0 secondary DEXs exist on Chain 1672. Multi-venue arbitrage impossible. |
| **Testnet Network Gas** | JSON-RPC `https://atlantic.dplabs-internal.com` | Pharos Atlantic (`688689`) | **LIVE**: Real-time gas price (`10.0 Gwei`) and sub-second block progression (`#31,610,751+`). |
| **Testnet DEX Deployments** | Canonical EVM router contracts & FaroSwap on Atlantic | Pharos Atlantic (`688689`) | **NOT DEPLOYED (0x Bytecode)**: 0 AMM liquidity pools deployed on Atlantic Testnet. |

---

## 2. Production Status & Honest Failure Resolution

Because real arbitrage requires at least two independent executable venues with sufficient liquidity depth:
1. **Pharos Mainnet (Chain 1672)** has only 1 DEX (FaroSwap) with dust reserves and zero secondary DEXs.
2. **Pharos Atlantic Testnet (Chain 688689)** has 0 deployed AMM liquidity pools (`0x` bytecode).
3. **Chainlink Push Feeds** are non-executable benchmark oracles, not trading pools.

### Status Code Enforced
```json
{
  "status": "LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY",
  "is_eligible": false,
  "execution_enabled": false
}
```

The application strictly refuses to substitute calibrated mock reserves, synthetic execution receipts, or fake trading venues. Trade execution is locked fail-closed.

---

## 3. Automated Test Suite Results

- **Total Tests Collected**: 40
- **Total Tests Passing**: **37 Passed** (plus 3 live network tests safely skipped when public RPC endpoints encountered transient rate-limits)
- **Failures / Errors**: **0**
- **Test Categories**:
  - `tests/test_amm.py`: Pure constant-product formula validation ($x \cdot y = k$), reserve boundaries, non-linear price impact, micro-volume precision (12 tests).
  - `tests/test_costs.py`: LP fee deduction, live Atlantic testnet gas conversions, waterfall friction calculations (5 tests).
  - `tests/test_evaluator.py`: Fail-closed live evaluator, threshold gating, excessive slippage guardrail, batch evaluation (9 tests).
  - `tests/test_venues.py`: On-chain Chainlink push feeds, FaroSwap router and factory audit, Atlantic AMM bytecode audit, fixture isolation (7 tests).
  - `tests/test_payload.py`: Calldata execution lock, rejection of ineligible execution calls (2 tests).
  - `tests/test_cli.py`: CLI commands (`scan`, `live-gas`, `demo`) and JSON outputs (3 tests).
  - `tests/test_live_network.py`: Live RPC connectivity and Chain ID validation (2 tests).

---

## 4. GitHub & Vercel Verification Evidence

- **GitHub Remote**: `origin` -> `https://github.com/JimmyOgb/pharos-arbitrage-scanner.git`
- **Published Branch**: `main` (Head commit: `365f5dd`)
- **Vercel Production URL**: [`https://pharos-arbitrage-scanner.vercel.app`](https://pharos-arbitrage-scanner.vercel.app)
- **HTTP Response Verification**:
  - Status: `200 OK`
  - Served Content: Full glassmorphism single-page application with real-time JSON-RPC queries to Pharos Mainnet (Chain 1672) and Atlantic Testnet (Chain 688689).
  - Production Status Displayed: `Live arbitrage unavailable — no verified liquidity`.
  - Zero Simulated Trades Guarantee: Verified.
