# Final Implementation Plan: Pharos Arbitrage Scanner

**Project**: `pharos-arbitrage-scanner`  
**Workspace**: `C:\Users\NO GO NO\PharosBuild\skills\pharos-arbitrage-scanner`  
**GitHub Repository**: `https://github.com/JimmyOgb/pharos-arbitrage-scanner`  
**Official Task**: [Pharos Agent Arena — Task 7: Arbitrage Scanner](https://pharos-agent-arena.vercel.app/tasks/arbitrage-scanner)  
**Standard**: Pharos SkillEngine v0.2.0  
**Operating Budget**: $0.00 (Pure on-chain RPC reads, zero external paid dependencies, zero build static Vercel deployment)  
**Security & Truthfulness Policy**: Strict Fail-Closed Zero-Simulation Mandate.

---

## 1. Verified Task Requirements & Acceptance Mapping

| # | Official Acceptance Criterion | Verified Technical Implementation | Automated Test & Evidence |
|---|---|---|---|
| **01** | **Reads prices from verified sources** | Queries real on-chain Chainlink Feeds Cache (`0xd9F00...`) & Proxy (`0x8b5DB...`) on Pharos Mainnet (`1672`); audits FaroSwap Factory (`0x18fa...`) on Chain 1672; audits Atlantic Testnet (`688689`) bytecode. | `test_query_chainlink_feed_live`<br>`test_amm_pool_bytecode_fail_closed` |
| **02** | **Calculates net profit after swap fees, slippage estimate, and gas** | Non-linear constant-product curve equations ($x \cdot y = k$), exact LP fee deduction, price impact vs slippage distinction, and live Atlantic Testnet gas at current Gwei converted to USD. | `test_waterfall_net_profit_deduction`<br>`test_price_impact_increases_with_volume` |
| **03** | **Acts (or prepares transaction) only above threshold; otherwise logs why it skipped** | Configurable `min_net_profit_usd` and `max_slippage_bps`. Rejects execution with `LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY` when multi-venue executable liquidity is unavailable; unit test fixtures validated with `TEST_FIXTURE_THRESHOLD_MET`. | `test_mathematical_model_profitable`<br>`test_below_threshold_status` |
| **04** | **Logs every scan with gross spread, costs, net result and decision** | Immutable structured JSON and tabular trace output detailing timestamp, network, spread, LP fees, slippage, gas friction, net profit, and fail-closed decision. | `test_cli_scan_json`<br>`test_multi_pair_batch_evaluation` |
| **05** | **Works safely on testnet; no requirement to risk real funds** | Fail-closed execution lock: locks trade execution (`execution_enabled: false`) when no two independent executable DEX venues with sufficient liquidity exist on testnet or mainnet. Zero private keys requested or exposed. Zero synthetic receipts. | `test_generate_arbitrage_calldata_eligible`<br>`test_live_atlantic_rpc_connectivity` |

---

## 2. On-Chain Network Audit Findings (Chain 1672 vs Chain 688689)

### A. Pharos Mainnet (Chain ID `1672`, RPC: `https://rpc.pharos.xyz`)
1. **Chainlink Self-Managed Feeds Cache** (`0xd9F00c86ced2De92F6B7152b0492cb28edc4B5a8`):
   - Bytecode: 3,875 bytes (Verified).
   - Feeds: BTC/USD ($82,792.12), ETH/USD ($2,427.43), PROS/USD ($0.63).
   - Role: Non-executable benchmark reference oracle.
2. **FaroSwap Uniswap-V2 Router** (`0xd285e37678f07631f33eb99927eb3ff0591a12d7`):
   - Bytecode: 35,708 bytes (Verified).
   - Factory: `0x18fab7d7027e9fb33fa90ca607439449209f7b09` (Verified).
   - Total Pairs: 111 pairs deployed.
   - Liquidity Depth: Empty / dust reserves (< $250 total liquidity across all pools).
3. **Secondary DEX**:
   - Standard Uniswap, SushiSwap, PancakeSwap, and Curve contracts checked: `0x` bytecode.
   - Result: **0 secondary executable DEXs deployed on Pharos Mainnet**. Multi-venue cross-DEX arbitrage is impossible.

### B. Pharos Atlantic Testnet (Chain ID `688689`, RPC: `https://atlantic.dplabs-internal.com`)
1. **Node State**:
   - Gas Price: **10.0 Gwei** (Polled via `eth_gasPrice`).
   - Block Height: **#31,610,751+** (Real-time progression).
2. **DEX Deployments**:
   - FaroSwap Router & Uniswap V2/V3 Routers checked: `0x` bytecode (empty).
   - Result: **0 AMM liquidity pools deployed on Atlantic Testnet**.

---

## 3. Truthful Architecture & Fail-Closed Resolution

Under the Zero Simulation Mandate:
- We refuse to fabricate synthetic quotes, calibrate fake pool reserves, or invent fake secondary DEX venues.
- The scanner reports status `LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY` with `is_eligible: false`.
- Calldata execution is permanently locked (`execution_enabled: false`) to safeguard user capital.
- The mathematical constant-product engine and net profit waterfall are verified using isolated unit tests labeled `TEST_FIXTURE_THRESHOLD_MET`.

---

## 4. Execution Phases

1. **Phase 1**: Audit and document requirements in `reports/FINAL_IMPLEMENTATION_PLAN.md` (Complete).
2. **Phase 2**: Discover and verify on-chain contracts across Chain 1672 and Chain 688689 (Complete).
3. **Phase 3**: Update venue registry and scanner logic with FaroSwap on Chain 1672 and Atlantic fail-closed check.
4. **Phase 4**: Enhance the web dashboard with dual-network monitoring, live gas polling, FaroSwap status, and client-side fail-closed transparency.
5. **Phase 5**: Run full test suite (39/39 passing) and update verification reports.
6. **Phase 6**: Publish to GitHub repository `JimmyOgb/pharos-arbitrage-scanner`.
7. **Phase 7**: Deploy to Vercel and verify live production URL.
