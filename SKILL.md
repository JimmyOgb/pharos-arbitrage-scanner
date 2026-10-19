---
name: pharos-arbitrage-scanner
version: 0.2.0
description: Real on-chain price discovery engine, constant-product AMM slippage calculator, and fail-closed arbitrage audit planner on Pharos Network.
author: JimmyOgb
license: MIT
network: atlantic
chain_id: 688689
standard: Pharos SkillEngine v0.2.0
---

# Pharos Arbitrage Scanner (`pharos-arbitrage-scanner`)

A high-performance SkillEngine capability that queries real on-chain token prices directly from verified Chainlink push feeds on Pharos, validates non-linear constant-product slippage ($x \cdot y = k$), nets trading fees and live testnet gas costs, and enforces a strict fail-closed safety policy on Pharos Network.

## Prerequisites

1. **Python Runtime**: Python `>= 3.9` (Zero external third-party runtime package dependencies required for core math and CLI).
2. **Network Access**: HTTP connection to Pharos Atlantic Testnet JSON-RPC (`https://atlantic.dplabs-internal.com`) and Pharos RPC (`https://rpc.pharos.xyz`).
3. **Safety Guarantee**: Operates in fail-closed audit mode. Zero private keys requested, stored, or broadcast. Zero synthetic receipts.

---

## Network Configuration

| Parameter | Atlantic Testnet (Gas & Settlement) | Pharos RPC (Push Oracle Host) |
|---|---|---|
| **Chain ID** | `688689` (`0xa8231`) | `1672` |
| **JSON-RPC Endpoint** | `https://atlantic.dplabs-internal.com` | `https://rpc.pharos.xyz` |
| **Push Oracle Cache** | N/A | `0xd9F00c86ced2De92F6B7152b0492cb28edc4B5a8` |
| **Block Explorer** | `https://atlantic.pharosscan.xyz` | `https://pharosscan.xyz` |
| **Native Currency** | `PHRS` (18 decimals) | `PHRS` (18 decimals) |
| **Execution Permission** | Locked (Fail-Closed: 0x Bytecode) | Read-Only Feed Queries |

---

## Capability Index

| Capability | Command | Description |
|---|---|---|
| **Live Scan** | `python scripts/scanner.py scan --pair BTC/USD` | Scans verified on-chain push feeds against Atlantic AMM status. |
| **Live Audit Suite** | `python scripts/scanner.py demo` | Runs 4-part live audit: Chainlink Feeds -> Atlantic Gas -> AMM Bytecode -> Math Models. |
| **Live Gas Query** | `python scripts/scanner.py live-gas` | Queries current gas price and block height directly from Atlantic node. |
| **Interactive Dashboard** | `python scripts/server.py` | Launches local HTTP server and opens the web visualizer dashboard. |

---

## Safety Boundary & Fail-Closed Checks

Before any opportunity is marked as eligible:
1. **Network Guardrail**: Verifies network matches Atlantic Testnet (`688689`) or Pharos RPC (`1672`).
2. **Zero-Key Boundary**: Never requires or requests wallet private keys or mnemonics.
3. **Bytecode Verification**: Verifies on-chain AMM contract bytecode. Fails closed with `SKIPPED_UNAVAILABLE_LIQUIDITY` if bytecode is `0x`.
4. **Transparent Rejection Reasons**: Every scan logs exact mathematical shortfall (`SKIPPED_UNAVAILABLE_LIQUIDITY`, `SKIPPED_BELOW_MIN_PROFIT_THRESHOLD`, `SKIPPED_UNPROFITABLE_AFTER_COSTS`, `SKIPPED_EXCESSIVE_SLIPPAGE`, `SKIPPED_NEGATIVE_SPREAD`).

---

## Skill Files & Manifest

- `SKILL.md`: Main entrypoint and capability index.
- `assets/networks.json`: Verified network RPC, MCP, and explorer definitions.
- `assets/tokens.json`: Verified Atlantic testnet ERC-20 token registry (USDC, WPHRS).
- `assets/venues.json`: Verified on-chain contract addresses, feeds, and AMM router status.
- `references/scanner.md`: Command specifications, output schemas, and error codes.
- `scanner/`: Python core AMM math, waterfall cost netting, and fail-closed evaluator.
- `scripts/`: Production CLI and dashboard server wrappers.
- `tests/`: Automated unit and integration test suite (39 tests passing).
- `web/`: Zero-dependency, modern reactive single-page dashboard.
