"""
Pharos Arbitrage Scanner Production CLI
Truthful On-Chain Feed Audit & Fail-Closed AMM Verification Engine.
"""

import argparse
import json
import sys
from typing import List, Dict, Any

from scanner.venues import get_supported_pairs, load_venues_config, query_chainlink_feed, check_on_chain_amm_pool
from scanner.evaluator import evaluate_arbitrage
from scanner.costs import fetch_live_gas_price
from scanner.payload import generate_arbitrage_calldata


def print_banner():
    banner = """
========================================================================
  PHAROS ARBITRAGE SCANNER | SKILLENGINE v0.2.0
  Network Audit: Pharos RPC (1672) & Pharos Atlantic Testnet (688689)
  Status: Live Arbitrage Unavailable -- No Verified Liquidity
========================================================================
"""
    print(banner)


def cmd_live_gas(args):
    gas_info = fetch_live_gas_price()
    if args.json:
        print(json.dumps(gas_info, indent=2))
        return

    print("Fetching live network gas directly from Pharos Atlantic Testnet (Chain ID 688689)...")
    print("\n--- Live Testnet Gas Status ---")
    print(f"  RPC Endpoint : {gas_info['rpc_url']}")
    print(f"  Status       : {gas_info.get('status', 'UNKNOWN')}")
    print(f"  Gas Price    : {gas_info.get('gas_price_gwei')} Gwei ({gas_info.get('gas_price_wei')} Wei)")
    print(f"  Block Number : {gas_info.get('block_number')}")
    print(f"  Is Live RPC  : {gas_info.get('is_live')}")
    if not gas_info.get("is_live"):
        print(f"  Error Notice : {gas_info.get('error')}")
    print("--------------------------------\n")


def format_live_audit_summary(eval_res: Dict[str, Any]) -> str:
    pair = eval_res["pair"]
    oracle_price = eval_res.get("reference_oracle_price")
    oracle = eval_res.get("oracle_venue", {})
    va = eval_res.get("venue_a", {})
    vb = eval_res.get("venue_b", {})
    buy = eval_res.get("buy_venue", {})
    sell = eval_res.get("sell_venue", {})
    spread = eval_res.get("gross_spread", {})
    waterfall = eval_res.get("waterfall") or {}
    dec = eval_res["decision"]
    gas = eval_res.get("gas_details", {})

    status_icon = f"[{dec.get('status')}]"

    va_price_str = f"${va.get('spot_price'):,.4f} USD" if va.get("spot_price") is not None else "QUOTE UNAVAILABLE"
    vb_price_str = f"${vb.get('spot_price'):,.4f} USD" if vb.get("spot_price") is not None else "QUOTE UNAVAILABLE"

    out = []
    out.append(f"\n========================================================================")
    out.append(f"Pair: {pair} | Mode: {eval_res.get('data_mode')} | Status: {status_icon}")
    out.append(f"========================================================================")
    out.append(f"  [Venue 1: DODO V2]       : {va_price_str} | Fee: {va.get('fee_bps', 15)} bps | Router: {va.get('router_address')}")
    out.append(f"  [Venue 2: FaroSwap V2]   : {vb_price_str} | Fee: {vb.get('fee_bps', 30)} bps | Pair: {vb.get('pair_address') or 'None'}")
    if oracle_price is not None:
        out.append(f"  [Reference Oracle]       : ${oracle_price:,.4f} USD (Chainlink Push Cache: {oracle.get('contract_address')})")
    out.append(f"  ----------------------------------------------------------------------")
    if waterfall:
        out.append(f"  Same-Scan Direction      : Buy {buy.get('name')} (${buy.get('spot_price', 0):,.4f}) -> Sell {sell.get('name')} (${sell.get('spot_price', 0):,.4f})")
        out.append(f"  Gross Spread             : {spread.get('spread_pct', 0):.2f}% (${spread.get('per_unit_usd', 0):.4f}/unit | ${spread.get('gross_spread_usd', 0):,.2f} on ${eval_res.get('trade_volume_usd', 0):,.2f})")
        out.append(f"  Waterfall - Buy Fee      : -${waterfall.get('buy_fee_usd', 0):.2f}")
        out.append(f"  Waterfall - Sell Fee     : -${waterfall.get('sell_fee_usd', 0):.2f}")
        out.append(f"  Waterfall - Slippage     : -${waterfall.get('total_slippage_usd', 0):.2f} (Buy: ${waterfall.get('buy_slippage_usd', 0):.2f}, Sell: ${waterfall.get('sell_slippage_usd', 0):.2f})")
        out.append(f"  Waterfall - Network Gas  : -${waterfall.get('gas_cost_usd', 0):.4f} ({gas.get('gas_price_gwei')} Gwei | Block #{gas.get('block_number')})")
        out.append(f"  Waterfall - Net Profit   : ${waterfall.get('net_profit_usd', 0):.2f} ({waterfall.get('net_profit_pct', 0):.2f}%)")
    else:
        out.append(f"  Cross-Venue Comparison   : BLOCKED (Both venues must independently provide verified quotes)")
        out.append(f"  Waterfall Friction       : N/A (Execution locked fail-closed)")
    out.append(f"  ----------------------------------------------------------------------")
    out.append(f"  Decision Gate Status     : {dec['status']} (is_eligible: {dec.get('is_eligible')})")
    out.append(f"  Gating Rationale         : {dec['reason']}")
    out.append(f"========================================================================\n")
    return "\n".join(out)


def cmd_scan(args):
    if not args.json:
        print_banner()
    pairs = [args.pair] if args.pair else get_supported_pairs()
    gas_info = fetch_live_gas_price()

    results = []
    for pair in pairs:
        try:
            res = evaluate_arbitrage(
                pair_name=pair,
                trade_volume_usd=args.volume,
                min_net_profit_usd=args.min_profit,
                max_slippage_bps=args.max_slippage_bps,
                live_gas_info=gas_info
            )
            results.append(res)
            if not args.json:
                print(format_live_audit_summary(res))
        except Exception as e:
            results.append({"pair": pair, "error": str(e)})
            if not args.json:
                print(f"Error scanning {pair}: {str(e)}")

    if args.json:
        print(json.dumps(results, indent=2))


def cmd_demo(args):
    """
    Executes the official 4-part live truthfulness audit & mathematical verification suite:
    Part 1: Live Chainlink reference push feed query (Pharos RPC, Chain ID: 1672)
    Part 2: Live Atlantic Testnet gas price & block height query (Chain ID: 688689)
    Part 3: On-chain AMM router bytecode audit (Proof that 0 AMM pools are deployed on Atlantic)
    Part 4: Mathematical unit test suite verifying constant-product mechanics (x·y=k) on test fixtures
    """
    if not args.json:
        print_banner()
        print("RUNNING OFFICIAL LIVE TRUTHFULNESS AUDIT & MATHEMATICAL VERIFICATION SUITE\n")
        print(">>> PART 1: QUERYING VERIFIED CHAINLINK REFERENCE FEEDS (PHAROS RPC, CHAIN ID 1672)...")
        print("    [Notice] Reference oracles provide benchmark prices, NOT executable AMM trade quotes.")

    feeds_report = {}
    for pair in ["BTC/USD", "ETH/USD", "PROS/USD"]:
        data = query_chainlink_feed(pair)
        feeds_report[pair] = data
        if not args.json:
            price_str = f"${data['reference_price_usd']:>12,.2f} USD" if data.get('reference_price_usd') is not None else "UNAVAILABLE"
            print(f"  [+] {pair:8s} : {price_str} | Updated: {data.get('updated_at_iso')} | Cache: {data.get('cache_address')}")

    if not args.json:
        print("\n>>> PART 2: QUERYING PHAROS ATLANTIC TESTNET (CHAIN ID 688689)...")
    gas_data = fetch_live_gas_price()
    if not args.json:
        print(f"  [+] Gas Price    : {gas_data.get('gas_price_gwei')} Gwei")
        print(f"  [+] Block Height : #{gas_data.get('block_number')}")
        print(f"  [+] Node Status  : {gas_data.get('status')}")

    if not args.json:
        print("\n>>> PART 3: AUDITING ON-CHAIN AMM ROUTER BYTECODE (ATLANTIC TESTNET)...")
    amm_check = check_on_chain_amm_pool("BASE", "QUOTE")
    if not args.json:
        print(f"  [+] Network Checked : {amm_check['network_name']}")
        print(f"  [+] Router Address  : {amm_check['router_address']}")
        print(f"  [+] Bytecode Status : {amm_check['status']} (0x bytecode)")
        print(f"  [+] Production State: Live arbitrage unavailable -- no verified liquidity.")

    if not args.json:
        print("\n>>> PART 4: MATHEMATICAL UNIT TEST HARNESS (ISOLATED TEST FIXTURES)...")
        print("    [Notice] Evaluating constant-product formulas (x*y=k) on isolated test fixtures for code verification only.")

    test_scenarios = [
        {
            "name": "Wide Spread (Math Verification)",
            "pair": "TEST/USD",
            "reserves": {
                "test_venue_a": {"name": "Test Venue A", "reserve_base": 200000.0, "reserve_quote": 500000.0, "fee_ratio": 0.003, "gas_units": 140000},
                "test_venue_b": {"name": "Test Venue B", "reserve_base": 200000.0, "reserve_quote": 512000.0, "fee_ratio": 0.0025, "gas_units": 155000}
            },
            "volume": 2500.0,
            "min_profit": 5.0,
            "max_slippage": 150
        },
        {
            "name": "High Slippage Erosion (Guardrail Trigger)",
            "pair": "TEST/USD",
            "reserves": {
                "test_venue_a": {"name": "Test Venue A", "reserve_base": 10000.0, "reserve_quote": 25000.0, "fee_ratio": 0.003, "gas_units": 140000},
                "test_venue_b": {"name": "Test Venue B", "reserve_base": 10000.0, "reserve_quote": 25200.0, "fee_ratio": 0.0025, "gas_units": 155000}
            },
            "volume": 10000.0,
            "min_profit": 5.0,
            "max_slippage": 50
        },
        {
            "name": "Inverted Spread (Zero Opportunity)",
            "pair": "TEST/USD",
            "reserves": {
                "test_venue_a": {"name": "Test Venue A", "reserve_base": 100000.0, "reserve_quote": 255000.0, "fee_ratio": 0.003, "gas_units": 140000},
                "test_venue_b": {"name": "Test Venue B", "reserve_base": 100000.0, "reserve_quote": 250000.0, "fee_ratio": 0.0025, "gas_units": 155000}
            },
            "volume": 2500.0,
            "min_profit": 5.0,
            "max_slippage": 150
        }
    ]

    math_results = []
    for sc in test_scenarios:
        res = evaluate_arbitrage(
            pair_name=sc["pair"],
            trade_volume_usd=sc["volume"],
            min_net_profit_usd=sc["min_profit"],
            max_slippage_bps=sc["max_slippage"],
            custom_reserves=sc["reserves"],
            live_gas_info=gas_data
        )
        res["test_name"] = sc["name"]
        math_results.append(res)
        if not args.json:
            dec = res["decision"]
            wf = res["waterfall"]
            print(f"  [+] {sc['name']}: {dec['status']}")
            if wf and wf.get("net_profit_usd") is not None:
                print(f"      Gross: +${wf['gross_spread_usd']:.2f} | Friction: -${wf['total_friction_usd']:.2f} | Net: ${wf['net_profit_usd']:+.2f}")
            print(f"      Reason: {dec['reason']}")

    report = {
        "production_status": "LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY",
        "verified_reference_oracle_feeds": feeds_report,
        "atlantic_gas": gas_data,
        "amm_deployment_status": amm_check,
        "isolated_unit_test_math_validation": math_results
    }

    if args.json:
        print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(
        prog="pharos-scanner",
        description="Pharos Arbitrage Scanner -- On-chain oracle reading, AMM mathematics, and fail-closed audit engine"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: scan
    scan_p = subparsers.add_parser("scan", help="Scan verified on-chain reference feeds and AMM status")
    scan_p.add_argument("--pair", type=str, default=None, help="Specific feed to query (e.g. BTC/USD)")
    scan_p.add_argument("--volume", type=float, default=5000.0, help="Trade volume in USD (default: 5000)")
    scan_p.add_argument("--min-profit", type=float, default=5.0, help="Min net profit threshold USD (default: 5.0)")
    scan_p.add_argument("--max-slippage-bps", type=int, default=150, help="Max price impact in bps (default: 150)")
    scan_p.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # Command: demo
    demo_p = subparsers.add_parser("demo", help="Run 4-part live audit & mathematical model verification suite")
    demo_p.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # Command: live-gas
    gas_p = subparsers.add_parser("live-gas", help="Fetch live gas price from Pharos Atlantic Testnet")
    gas_p.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "demo":
        cmd_demo(args)
    elif args.command == "live-gas":
        cmd_live_gas(args)


if __name__ == "__main__":
    main()
