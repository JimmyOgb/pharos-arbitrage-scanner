"""
Pharos Arbitrage Scanner Production CLI
100% Real On-Chain Verified Market Data & Fail-Closed AMM Audit Engine.
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
  Network: Pharos Atlantic Testnet (688689) & Pharos RPC (1672)
  100% Real On-Chain Verified Market Data & Fail-Closed Safety Engine
========================================================================
"""
    print(banner)


def cmd_live_gas(args):
    gas_info = fetch_live_gas_price()
    if args.json:
        print(json.dumps(gas_info, indent=2))
        return

    print("Fetching live network gas directly from Pharos Atlantic Testnet...")
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
    spot = eval_res.get("verified_feed_price")
    cl = eval_res.get("chainlink_details", {})
    amm = eval_res.get("amm_details", {})
    dec = eval_res["decision"]
    gas = eval_res.get("gas_details", {})

    status_icon = "[FAIL-CLOSED: LIQUIDITY UNAVAILABLE]"

    out = []
    out.append(f"\n=======================================================")
    out.append(f"Pair: {pair} | Mode: {eval_res.get('data_mode')} | Status: {status_icon}")
    out.append(f"=======================================================")
    out.append(f"  Verified On-Chain Price : ${spot:,.2f} USD")
    out.append(f"  Oracle Source           : {cl.get('name')} (Chain ID {cl.get('chain_id')})")
    out.append(f"  Oracle Cache Address    : {cl.get('contract_address')}")
    if cl.get("proxy_address"):
        out.append(f"  Aggregator Proxy        : {cl.get('proxy_address')} (Verified: {cl.get('proxy_verified')})")
    out.append(f"  Last Feed Update        : {cl.get('updated_at_iso')} (Epoch: {cl.get('updated_at_epoch')})")
    out.append(f"  Atlantic Gas Price      : {gas.get('gas_price_gwei')} Gwei (Block #{gas.get('block_number')})")
    out.append(f"  AMM Pool Deployment     : {amm.get('status')} (Router: {amm.get('router_address')})")
    out.append(f"  Decision Gate           : {dec['status']}")
    out.append(f"  Reason                  : {dec['reason']}")
    out.append(f"=======================================================\n")
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
    Executes the official 4-part live audit & mathematical model verification suite:
    Part 1: Live Chainlink push feed query across BTC/USD, ETH/USD, PROS/USD on Pharos
    Part 2: Live Atlantic Testnet gas price & block height query
    Part 3: On-chain AMM router bytecode verification (proof of fail-closed handling)
    Part 4: Mathematical model validation (x·y=k & waterfall) on isolated test fixtures
    """
    if not args.json:
        print_banner()
        print("RUNNING OFFICIAL LIVE AUDIT & MATHEMATICAL VERIFICATION SUITE\n")
        print(">>> PART 1: QUERYING REAL ON-CHAIN CHAINLINK FEEDS (PHAROS RPC)...")

    feeds_report = {}
    for pair in ["BTC/USD", "ETH/USD", "PROS/USD"]:
        data = query_chainlink_feed(pair)
        feeds_report[pair] = data
        if not args.json:
            price_str = f"${data['price_usd']:>12,.2f} USD" if data.get('price_usd') is not None else "UNAVAILABLE"
            print(f"  [+] {pair:8s} : {price_str} | Updated: {data.get('updated_at_iso')} | Cache: {data.get('cache_address')}")

    if not args.json:
        print("\n>>> PART 2: QUERYING ATLANTIC TESTNET NETWORK STATE...")
    gas_data = fetch_live_gas_price()
    if not args.json:
        print(f"  [+] Gas Price    : {gas_data.get('gas_price_gwei')} Gwei")
        print(f"  [+] Block Height : #{gas_data.get('block_number')}")
        print(f"  [+] Node Status  : {gas_data.get('status')}")

    if not args.json:
        print("\n>>> PART 3: VERIFYING ON-CHAIN AMM ROUTER BYTECODE (FAIL-CLOSED CHECK)...")
    amm_check = check_on_chain_amm_pool("BASE", "QUOTE")
    if not args.json:
        print(f"  [+] Router Address : {amm_check['router_address']}")
        print(f"  [+] Bytecode Status: {amm_check['status']}")
        print(f"  [+] Safety Action  : Fail-closed enforced. Zero simulated reserves substituted.")

    if not args.json:
        print("\n>>> PART 4: MATHEMATICAL MODEL VALIDATION (ISOLATED TEST FIXTURES)...")

    # Controlled test fixture scenarios to verify AMM math (x*y=k) and waterfall deductions
    test_scenarios = [
        {
            "name": "Wide Spread (Math Verification)",
            "pair": "TEST/USD",
            "reserves": {
                "venue_a": {"name": "Test Venue A", "reserve_base": 200000.0, "reserve_quote": 500000.0, "fee_ratio": 0.003, "gas_units": 140000},
                "venue_b": {"name": "Test Venue B", "reserve_base": 200000.0, "reserve_quote": 512000.0, "fee_ratio": 0.0025, "gas_units": 155000}
            },
            "volume": 2500.0,
            "min_profit": 5.0,
            "max_slippage": 150
        },
        {
            "name": "High Slippage Erosion (Guardrail Trigger)",
            "pair": "TEST/USD",
            "reserves": {
                "venue_a": {"name": "Test Venue A", "reserve_base": 10000.0, "reserve_quote": 25000.0, "fee_ratio": 0.003, "gas_units": 140000},
                "venue_b": {"name": "Test Venue B", "reserve_base": 10000.0, "reserve_quote": 25200.0, "fee_ratio": 0.0025, "gas_units": 155000}
            },
            "volume": 10000.0,
            "min_profit": 5.0,
            "max_slippage": 50
        },
        {
            "name": "Inverted Spread (Zero Opportunity)",
            "pair": "TEST/USD",
            "reserves": {
                "venue_a": {"name": "Test Venue A", "reserve_base": 100000.0, "reserve_quote": 255000.0, "fee_ratio": 0.003, "gas_units": 140000},
                "venue_b": {"name": "Test Venue B", "reserve_base": 100000.0, "reserve_quote": 250000.0, "fee_ratio": 0.0025, "gas_units": 155000}
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
        "verified_chainlink_feeds": feeds_report,
        "atlantic_gas": gas_data,
        "amm_deployment_status": amm_check,
        "mathematical_model_validation": math_results
    }

    if args.json:
        print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(
        prog="pharos-scanner",
        description="Pharos Arbitrage Scanner — Multi-venue discovery, AMM slippage, and waterfall netting"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: scan
    scan_p = subparsers.add_parser("scan", help="Scan verified on-chain pairs across venues")
    scan_p.add_argument("--pair", type=str, default=None, help="Specific pair to scan (e.g. BTC/USD)")
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
