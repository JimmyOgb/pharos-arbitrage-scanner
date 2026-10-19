"""
Pharos Arbitrage Scanner Production CLI
Interactive terminal interface, benchmark demo suite, and machine-readable JSON logging.
"""

import argparse
import json
import sys
from typing import List, Dict, Any

from scanner.venues import get_supported_pairs, load_venues_config
from scanner.evaluator import evaluate_arbitrage
from scanner.costs import fetch_live_gas_price
from scanner.payload import generate_atomic_payload, execute_simulated_trade


def print_banner():
    banner = """
========================================================================
  PHAROS ARBITRAGE SCANNER | SKILLENGINE v0.1.0
  Network: Pharos Atlantic Testnet (Chain ID: 688689)
  Zero-Risk Simulation & Calibrated Price Discovery Engine
========================================================================
"""
    print(banner)


def cmd_live_gas(args):
    gas_info = fetch_live_gas_price()
    if args.json:
        print(json.dumps(gas_info, indent=2))
        return

    print("Fetching live gas price from Pharos Atlantic Testnet...")
    print("\n--- Live Testnet Gas Status ---")
    print(f"  RPC Endpoint : {gas_info['rpc_url']}")
    print(f"  Source       : {gas_info['source']}")
    print(f"  Gas Price    : {gas_info['gas_price_gwei']} Gwei ({gas_info['gas_price_wei']} Wei)")
    print(f"  Block Number : {gas_info['block_number']}")
    print(f"  Is Live RPC  : {gas_info['is_live']}")
    if "fallback_notice" in gas_info:
        print(f"  Notice       : {gas_info['fallback_notice']}")
    print("--------------------------------\n")


def format_evaluation_summary(eval_res: Dict[str, Any]) -> str:
    pair = eval_res["pair"]
    wf = eval_res["waterfall"]
    dec = eval_res["decision"]
    buy = eval_res["buy_venue"]
    sell = eval_res["sell_venue"]
    
    status_icon = "🟢 [ELIGIBLE]" if dec["is_eligible"] else "🔴 [SKIPPED]"
    
    out = []
    out.append(f"\n=======================================================")
    out.append(f"Pair: {pair} | Volume: ${eval_res['trade_volume_usd']:,.2f} | Status: {status_icon}")
    out.append(f"=======================================================")
    out.append(f"  Direction   : Buy on {buy['name']} (${buy['spot_price']:.4f}) -> Sell on {sell['name']} (${sell['spot_price']:.4f})")
    out.append(f"  Gross Spread: +${wf['gross_spread_usd']:,.2f} (+{wf['gross_spread_pct']:.2f}%)")
    out.append(f"  --- Waterfall Cost Deductions ---")
    out.append(f"  - LP Fees   : -${wf['total_fees_usd']:,.2f} (Buy: ${wf['buy_fee_usd']:.2f}, Sell: ${wf['sell_fee_usd']:.2f})")
    out.append(f"  - Slippage  : -${wf['total_slippage_usd']:,.2f} ({eval_res['combined_slippage_bps']:.1f} bps impact)")
    out.append(f"  - Gas Cost  : -${wf['gas_cost_usd']:,.4f} ({wf['gas_units_total']:,} units @ {eval_res['gas_details']['gas_price_gwei']} Gwei)")
    out.append(f"  Total Costs : -${wf['total_friction_usd']:,.2f}")
    out.append(f"  ---------------------------------")
    out.append(f"  NET PROFIT  : {'+$' if wf['net_profit_usd'] >= 0 else '-$'}{abs(wf['net_profit_usd']):,.2f} ({wf['net_profit_pct']:+.2f}%)")
    out.append(f"  Decision    : {dec['status']}")
    out.append(f"  Reason      : {dec['reason']}")
    out.append(f"=======================================================\n")
    return "\n".join(out)


def cmd_scan(args):
    if not args.json:
        print_banner()
    pairs = [args.pair] if args.pair else get_supported_pairs()
    gas_info = fetch_live_gas_price()
    
    results = []
    for pair in pairs:
        res = evaluate_arbitrage(
            pair_name=pair,
            trade_volume_usd=args.volume,
            min_net_profit_usd=args.min_profit,
            max_slippage_bps=args.max_slippage_bps,
            live_gas_info=gas_info
        )
        results.append(res)
        if not args.json:
            print(format_evaluation_summary(res))

    if args.json:
        print(json.dumps(results, indent=2))


def cmd_demo(args):
    """
    Executes a side-by-side run of the four canonical market scenarios:
    1. Profitable Arbitrage
    2. Slippage-Eroded Spread
    3. Gas-Eroded Micro-Spread
    4. Inverted Spread (Zero Opportunity)
    """
    if not args.json:
        print_banner()
        print("RUNNING OFFICIAL BENCHMARK SCENARIOS (4 CANONICAL TEST CASES)...\n")

    config = load_venues_config()
    scenarios = config.get("market_scenarios", {})
    gas_info = fetch_live_gas_price()
    
    demo_results = []
    for sc_id, sc in scenarios.items():
        custom_reserves = None
        if sc_id == "slippage_eroded":
            # Thin spread with shallow depth
            custom_reserves = {
                "pharos_swap": {"reserve_base": 10000.0, "reserve_quote": 25000.0},
                "lighthouse_dex": {"reserve_base": 10000.0, "reserve_quote": 25200.0}
            }
        elif sc_id == "inverted_spread":
            # Inverted market
            custom_reserves = {
                "pharos_swap": {"reserve_base": 100000.0, "reserve_quote": 255000.0},
                "lighthouse_dex": {"reserve_base": 100000.0, "reserve_quote": 250000.0}
            }

        res = evaluate_arbitrage(
            pair_name=sc["pair"],
            trade_volume_usd=5000.0,
            min_net_profit_usd=5.0,
            max_slippage_bps=150,
            custom_reserves=custom_reserves,
            live_gas_info=gas_info
        )
        res["scenario_id"] = sc_id
        res["scenario_name"] = sc["name"]
        demo_results.append(res)

        if not args.json:
            print(f">>> SCENARIO: {sc['name']} ({sc_id})")
            print(format_evaluation_summary(res))
            if res["decision"]["is_eligible"]:
                payload = generate_atomic_payload(res)
                receipt = execute_simulated_trade(payload)
                print(f"  [EXECUTION SIMULATION CONFIRMED]")
                print(f"  Tx Hash      : {receipt['tx_hash']}")
                print(f"  Block Height : {receipt['block_number']}")
                print(f"  Profit Net   : +${receipt['profit_realized_usd']:.2f}")
                print(f"  Gas Used     : {receipt['gas_used']:,} units\n")

    if args.json:
        print(json.dumps(demo_results, indent=2))


def main():
    parser = argparse.ArgumentParser(
        prog="pharos-scanner",
        description="Pharos Arbitrage Scanner — Multi-venue discovery, AMM slippage, and waterfall netting"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: scan
    scan_p = subparsers.add_parser("scan", help="Scan trading pairs across venues")
    scan_p.add_argument("--pair", type=str, default=None, help="Specific pair to scan (e.g. PHRS/USDC)")
    scan_p.add_argument("--volume", type=float, default=5000.0, help="Trade volume in USD (default: 5000)")
    scan_p.add_argument("--min-profit", type=float, default=5.0, help="Min net profit threshold USD (default: 5.0)")
    scan_p.add_argument("--max-slippage-bps", type=int, default=150, help="Max price impact in bps (default: 150)")
    scan_p.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # Command: demo
    demo_p = subparsers.add_parser("demo", help="Run 4-scenario benchmark demo suite")
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
