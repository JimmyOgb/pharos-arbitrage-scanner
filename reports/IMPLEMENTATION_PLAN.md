# Implementation Plan & Technical Audit: Pharos Arbitrage Scanner

**Project**: Pharos Arbitrage Scanner  
**Repository**: `https://github.com/JimmyOgb/pharos-arbitrage-scanner`  
**Official Task Track**: Pharos Agent Arena (Season of AI) — Task 7: Arbitrage Scanner (`arbitrage-scanner`)  
**Official URL**: [https://pharos-agent-arena.vercel.app/tasks/arbitrage-scanner](https://pharos-agent-arena.vercel.app/tasks/arbitrage-scanner)  
**Target Network**: Pharos Atlantic Testnet (`Chain ID: 688689`)  
**Budget Guarantee**: $0.00 (Zero paid APIs, zero cloud costs, free Vercel deployment, public testnet endpoints)  
**Status**: Approved for Implementation

---

## 1. Inspection & Ecosystem Findings

### 1.1 Official Task Scoring Criteria
From [https://pharos-agent-arena.vercel.app/tasks/arbitrage-scanner](https://pharos-agent-arena.vercel.app/tasks/arbitrage-scanner):
- **Tier**: Hard
- **Points**: 200 Base Points + 50 Video Bonus Points = **250 total points**
- **Five Mandatory Acceptance Criteria**:
  1. `Reads prices from at least 2 sources in the same scan.`
  2. `Calculates net profit after swap fees, slippage estimate, and gas.`
  3. `Acts (or prepares the transaction) only above a configurable profit threshold; otherwise logs why it skipped.`
  4. `Logs every scan with gross spread, costs, net result and decision.`
  5. `Works safely on testnet or with simulated execution; no requirement to risk real funds.`

### 1.2 On-Chain & Network Realities (Verified Live)
We directly probed the live Pharos Atlantic Testnet JSON-RPC (`https://atlantic.dplabs-internal.com`):
- `eth_chainId`: `688689` (`0xa8231`) — Verified.
- `eth_blockNumber`: `31,608,157+` — Live sub-second blocks confirmed.
- `eth_gasPrice`: `10,000,000,000` Wei (`10.0` Gwei) — Verified live.
- **Bytecode Inspection**:
  - `USDC_1` (`0xcfC8330f4BCAB529c625D12781b1C19466A9Fc8B`): Contract bytecode length = 3,598 bytes (Live).
  - `USDC_2` (`0xE0BE08c77f415F577A1B3A9aD7a1Df1479564ec8`): Contract bytecode length = 12,012 bytes (Live).
  - `WPHRS` (`0x838800b758277CC111B2d48Ab01e5E164f8E9471`): Contract bytecode length = 7,262 bytes (Live).
  - `UniswapV2Factory` (`0x5C69...`): Empty (`0x`) — No standard public Uniswap V2 factory on testnet.
  - `UniswapV2Router02` (`0x7a25...`): Empty (`0x`) — No standard public Uniswap V2 router on testnet.
  - `UniswapV3Factory` (`0x1F98...`): Empty (`0x`) — No standard public Uniswap V3 factory on testnet.

### 1.3 Architectural & Ethical Realism Strategy
Per project directives:
- **Zero Invention**: We do **not** claim or fabricate live DEX router contracts or fake pool transactions.
- **Hybrid Real-Time / Calibrated Simulation Architecture**:
  1. **Live Feed**: Network gas prices (`eth_gasPrice`) and block timestamps are polled directly from the live Pharos Atlantic Testnet RPC.
  2. **Calibrated Pool Models**: Dual-venue liquidity pool states (Venue A: *PharosSwap Constant-Product Pool*, Venue B: *Lighthouse Concentrated Pool*, Venue C: *Pyth Benchmark Oracle*) are modeled with realistic reserves, exact $x \cdot y = k$ math, and configurable depth scenarios.
  3. **Strict Labeling**: All simulated data and test fixtures are explicitly marked `[CALIBRATED SIMULATION]` or `[TEST FIXTURE]`. Real testnet network indicators are marked `[LIVE ATLANTIC RPC]`.
  4. **Fail-Closed Execution**: Transaction payloads are prepared with canonical multicall / router interfaces and simulated safely with receipt logging without risking real capital or private keys.

---

## 2. Mathematical Architecture

### 2.1 AMM Constant-Product Slippage
For a swap of $\Delta x$ on a pool with reserves $(R_x, R_y)$ and fee fraction $f = 0.003$:
$$\Delta x_{eff} = \Delta x \cdot (1 - f)$$
$$\Delta y = \frac{R_y \cdot \Delta x_{eff}}{R_x + \Delta x_{eff}}$$
$$\text{Effective Execution Price } P_{exec} = \frac{\Delta x}{\Delta y}$$
$$\text{Pre-trade Spot Price } P_{spot} = \frac{R_x}{R_y}$$
$$\text{Price Impact / Slippage } S = \frac{|P_{exec} - P_{spot}|}{P_{spot}}$$

### 2.2 Complete Waterfall Cost Deduction
1. **Gross Spread**: $(P_{sell} - P_{buy}) \times \text{Volume}$
2. **Venue A Swap Fee**: $\text{Volume} \times 0.003$
3. **Venue A Price Impact**: Non-linear constant-product slippage based on Venue A depth
4. **Venue B Swap Fee**: $\text{Leg 1 Output} \times 0.003$
5. **Venue B Price Impact**: Non-linear constant-product slippage based on Venue B depth
6. **Gas Cost**: $\text{Gas Units} \times \text{Gas Price (Live Gwei)} \times 10^{-9} \times P_{PHRS/USD}$
7. **Net Profit**: $\text{Gross Spread} - (\text{Fees} + \text{Slippage} + \text{Gas})$

### 2.3 Threshold Gating
- `MIN_NET_PROFIT_USD`: Minimum acceptable net profit (e.g. $5.00).
- `MAX_SLIPPAGE_BPS`: Maximum tolerable price impact per leg (e.g. 150 bps / 1.5%).
- **Decision Matrix**:
  - If $\text{Net Profit} \ge \text{Threshold}$ AND $\text{Slippage} \le \text{Max Slippage}$: `ELIGIBLE_FOR_EXECUTION`
  - If $\text{Gross Spread} \le 0$: `SKIPPED_NEGATIVE_SPREAD`
  - If $\text{Net Profit} < 0$: `SKIPPED_UNPROFITABLE_AFTER_COSTS`
  - If $0 \le \text{Net Profit} < \text{Threshold}$: `SKIPPED_BELOW_MIN_PROFIT_THRESHOLD`
  - If $\text{Slippage} > \text{Max Slippage}$: `SKIPPED_EXCESSIVE_SLIPPAGE`

---

## 3. Project Structure

```text
pharos-arbitrage-scanner/
├── .github/
│   └── workflows/ci.yml             # Automated multi-OS GitHub Actions workflow
├── assets/
│   ├── networks.json                # Verified Atlantic Testnet & Pacific Mainnet endpoints
│   ├── tokens.json                  # Verified ERC-20 token registry (USDC, WPHRS)
│   └── venues.json                  # Venue configurations, pool reserves, and fee schedules
├── references/
│   └── scanner.md                   # Machine-readable command templates & schemas
├── reports/
│   ├── IMPLEMENTATION_PLAN.md       # Pre-implementation audit & architecture specification
│   └── VERIFICATION_REPORT.md       # Comprehensive testing & evidence verification
├── scanner/                         # Python Core Engine (zero external runtime dependencies)
│   ├── __init__.py
│   ├── amm.py                       # Constant product math, price impact, output estimation
│   ├── costs.py                     # LP fees, live testnet gas conversion, friction waterfalls
│   ├── venues.py                    # Multi-venue pricing, reserve retrieval, data freshness
│   ├── evaluator.py                 # Threshold gating, decision logging, opportunity scoring
│   ├── payload.py                   # Atomic trade preparation, calldata formatting, safety checks
│   └── cli.py                       # Production CLI entrypoint with JSON & interactive outputs
├── scripts/
│   ├── scanner.py                   # SkillEngine CLI wrapper
│   └── server.py                    # Lightweight local HTTP/SSE server for web UI
├── tests/                           # Comprehensive automated test suite (unit + integration)
│   ├── test_amm.py                  # Math formulas, zero liquidity, edge cases
│   ├── test_costs.py                # Fee schedules, gas conversion, negative costs
│   ├── test_venues.py               # Price reading, stale data detection, venue comparison
│   ├── test_evaluator.py            # Decision logic, threshold gating, skip reasons
│   ├── test_payload.py              # Calldata generation, route safety, fail-closed barriers
│   ├── test_cli.py                  # Argument parsing, exit codes, JSON outputs
│   └── test_live_network.py         # Live Atlantic Testnet RPC integration tests
├── web/                             # Zero-dependency, modern reactive single-page dashboard
│   └── index.html                   # High-contrast Web3 developer UI (Tailwind CSS CDN, Lucide)
├── .gitignore
├── .vercelignore
├── LICENSE
├── pyproject.toml                   # Test & package configuration
├── README.md                        # 15-section complete developer & reviewer manual
├── SKILL.md                         # Official Pharos SkillEngine standard specification
└── vercel.json                      # Free-tier zero-build static deployment config
```

---

## 4. Work Plan & Delivery Sequence

1. **Reports & Audit**: Finalize `reports/IMPLEMENTATION_PLAN.md` (Completed).
2. **SkillEngine Assets & Manifest**:
   - `assets/networks.json`, `assets/tokens.json`, `assets/venues.json`
   - `SKILL.md` and `references/scanner.md`
3. **Core Engine Implementation (`scanner/`)**:
   - `amm.py`, `costs.py`, `venues.py`, `evaluator.py`, `payload.py`, `cli.py`
4. **Comprehensive Test Suite (`tests/`)**:
   - Author 35+ unit & integration tests covering all math, failure modes, and live RPC.
   - Run pytest and confirm 100% pass.
5. **Interactive Web Dashboard (`web/index.html`)**:
   - Live Atlantic Testnet connection badge (RPC polling).
   - Real-time scanner controls (pairs, volume slider, threshold inputs).
   - Waterfall cost visualizer (gross spread $\to$ fees $\to$ slippage $\to$ gas $\to$ net profit).
   - Opportunity table & audit log with detailed calculation proofs.
   - Atomic payload inspector with simulated execution sandbox.
6. **Verification & Evidence**:
   - Generate `reports/VERIFICATION_REPORT.md` documenting test results, live RPC responses, and mathematical verification.
7. **Documentation**:
   - Comprehensive `README.md` with setup, formulas, architecture, and verification instructions.
8. **User Review**:
   - Present final report and await explicit approval before pushing to GitHub or deploying to Vercel.
