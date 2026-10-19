---
name: pharos-arbitrage-scanner
version: 0.1.0
description: Multi-venue price discovery engine, constant-product AMM slippage calculator, and threshold-gated arbitrage execution planner on Pharos Network.
author: JimmyOgb
license: MIT
network: atlantic
chain_id: 688689
standard: Pharos SkillEngine v0.1.0
---

# Pharos Arbitrage Scanner (`pharos-arbitrage-scanner`)

A high-performance SkillEngine capability that queries token prices across multiple trading venues simultaneously, computes non-linear constant-product slippage ($x \cdot y = k$), nets trading fees and live testnet gas costs, and evaluates opportunities against configurable risk and profit thresholds on Pharos Network.

## Prerequisites

1. **Python Runtime**: Python `>= 3.9` (Zero external third-party package dependencies required for core math and CLI).
2. **Network Access**: HTTP connection to Pharos Atlantic Testnet JSON-RPC (`https://atlantic.dplabs-internal.com`) for live gas price and block time polling.
3. **Safety Guarantee**: Operates in zero-risk simulation and preparation mode. Zero private keys requested, stored, or broadcast.

---

## Network Configuration

| Parameter | Atlantic Testnet (Primary) | Pacific Mainnet (Restricted) |
|---|---|---|
| **Chain ID** | `688689` (`0xa8231`) | `688688` (`0xa8230`) |
| **JSON-RPC Endpoint** | `https://atlantic.dplabs-internal.com` | `https://pacific.dplabs-internal.com` |
| **Hosted Chain MCP** | `https://mcp.pharos.xyz/mcp` | N/A |
| **Block Explorer** | `https://atlantic.pharosscan.xyz` | `https://pharosscan.xyz` |
| **Native Currency** | `PHRS` (18 decimals) | `PHRS` (18 decimals) |
| **Execution Permission** | Allowed (Simulation & Calibrated Read) | Blocked (Fail-Closed) |

---

## Capability Index

| Capability | Command | Description |
|---|---|---|
| **Full Scan** | `python scripts/scanner.py scan` | Scans all configured pairs across dual venues and benchmark oracle. |
| **Scenario Suite** | `python scripts/scanner.py demo` | Runs side-by-side scenarios: Profitable Arbitrage, Slippage-Eroded, Gas-Eroded, and Negative Spread. |
| **Live Gas Query** | `python scripts/scanner.py live-gas` | Queries current gas price directly from Pharos Atlantic Testnet node. |
| **Custom Evaluation** | `python scripts/scanner.py evaluate --pair PHRS/USDC --volume 2500 --min-profit 5.0` | Evaluates a custom pair and volume with waterfall profit deduction. |
| **Interactive Dashboard** | `python scripts/server.py` | Launches local HTTP/SSE server and opens the web visualizer dashboard. |

---

## Safety Boundary & Write Pre-checks

Before any opportunity is marked as eligible:
1. **Network Guardrail**: Verifies network matches Atlantic Testnet (`688689`). Fails closed on unexpected chain IDs.
2. **Zero-Key Boundary**: Never requires or requests wallet private keys or mnemonics.
3. **Non-Linear Slippage**: Enforces constant-product reserve depth calculations rather than flat percentages.
4. **Transparent Rejection Reasons**: Every non-executable scan logs exact mathematical shortfall (`SKIPPED_BELOW_MIN_PROFIT_THRESHOLD`, `SKIPPED_UNPROFITABLE_AFTER_COSTS`, `SKIPPED_EXCESSIVE_SLIPPAGE`, `SKIPPED_NEGATIVE_SPREAD`).

---

## Skill Files & Manifest

- `SKILL.md`: Main entrypoint and capability index.
- `assets/networks.json`: Verified network RPC, MCP, and explorer definitions.
- `assets/tokens.json`: Verified Atlantic testnet ERC-20 token registry (USDC, WPHRS).
- `assets/venues.json`: DEX pool parameters, fee schedules, and market scenarios.
- `references/scanner.md`: Command specifications, output schemas, and error codes.
- `scanner/`: Python core AMM math, waterfall cost netting, and threshold evaluator.
- `scripts/`: Production CLI and dashboard server wrappers.
- `tests/`: Automated unit and integration test suite.
- `web/`: Zero-dependency, modern reactive single-page dashboard.
