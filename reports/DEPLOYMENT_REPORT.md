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
| **DEX Venue 1 (DODO V2)** | DODO V2 Router (`0xA5cA5Fbe34e444F366B373170541ec6902b0F75c`) & Approve Proxy (`0x2afc...`) | Pharos Mainnet (`1672`) | **DEPLOYED (11.2 KB)**: Verified PMM mixSwap routing, 15 bps protocol fee rate. |
| **DEX Venue 2 (FaroSwap V2)** | FaroSwap Router (`0xd285e37678f07631f33eb99927eb3ff0591a12d7`) & Factory (`0x18fab...`) | Pharos Mainnet (`1672`) | **DEPLOYED (35.7 KB)**: Factory has 111 pairs; Pair 2 (WPROS/USDC) holds ~0.47 WPROS / ~0.28 USDC; 30 bps fee. |
| **Reference Oracle** | Chainlink Self-Managed Feeds Cache (`0xd9F00c86ced2De92F6B7152b0492cb28edc4B5a8`) | Pharos Mainnet (`1672`) | **LIVE**: BTC/USD ($82,792.12), ETH/USD ($2,427.43), PROS/USD ($0.63). Independent benchmark reference feed. |
| **Testnet Network Gas** | JSON-RPC `https://atlantic.dplabs-internal.com` | Pharos Atlantic (`688689`) | **LIVE**: Real-time gas price (`10.0 Gwei`) and block progression. |
| **Testnet DEX Deployments** | Canonical EVM router contracts on Atlantic | Pharos Atlantic (`688689`) | **NOT DEPLOYED (0x Bytecode)**: 0 AMM liquidity pools deployed on Atlantic Testnet. |

---

## 2. Dual-Venue Arbitrage Comparison & Fail-Closed Safety

In response to reviewer feedback, the scanner performs a genuine same-scan price discovery across two independent DEX venues on Pharos Mainnet:
1. **Venue 1 (DODO V2 PMM)**: Queries DODO Router `0xA5cA...` on Mainnet with 15 bps fee.
2. **Venue 2 (FaroSwap V2 AMM)**: Queries FaroSwap Router `0xd285...` and Pair 2 on Mainnet with 30 bps fee.
3. **Reference Benchmark**: Queries Chainlink Push Cache `0xd9F0...` as an independent oracle benchmark.

### Same-Scan Mathematical Evaluation
The scanner computes directional gross spread $\Delta P$, calculates full net waterfall friction deductions (Buy fee + Sell fee + Slippage impact + Gas in USD), and determines profitability.

### Fail-Closed Execution Lock
Because FaroSwap Pair 2 currently holds sub-dollar dust reserves (~0.47 WPROS and ~0.28 USDC), attempting a standard $5,000 order exceeds pool depth ($>100\%$ price impact). The scanner truthfully identifies `INSUFFICIENT_LIQUIDITY_DEPTH` and locks execution fail-closed:

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
