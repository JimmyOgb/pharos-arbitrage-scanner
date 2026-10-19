"""
Arbitrage Opportunity Evaluator & Decision Gating Engine
Executes complete dual-leg analysis, applies slippage and fee netting,
and validates against user-configured risk thresholds.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from scanner.amm import calculate_price_impact, calculate_swap_output
from scanner.costs import fetch_live_gas_price, calculate_gas_cost_usd, compute_net_waterfall
from scanner.venues import scan_pair_venues


def evaluate_arbitrage(
    pair_name: str,
    trade_volume_usd: float = 5000.0,
    min_net_profit_usd: float = 5.0,
    max_slippage_bps: int = 150,
    custom_reserves: Optional[Dict[str, Any]] = None,
    live_gas_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates dual-venue arbitrage for a given pair and volume.
    
    Workflow:
    1. Reads prices from at least 2 sources simultaneously (Venue A, Venue B, Oracle).
    2. Identifies directional buy and sell venues (Buy Low, Sell High).
    3. Simulates Leg 1: Buying base token with quote volume on Venue A.
    4. Simulates Leg 2: Selling acquired base token for quote token on Venue B.
    5. Computes exact price impact and LP fee on both legs.
    6. Fetches/applies real live gas costs on Pharos Atlantic Testnet.
    7. Builds net profit waterfall.
    8. Applies decision gate (Threshold, Slippage, Positive spread).
    """
    if trade_volume_usd <= 0:
        raise ValueError(f"trade_volume_usd must be positive, got {trade_volume_usd}")
    if min_net_profit_usd < 0:
        raise ValueError(f"min_net_profit_usd cannot be negative, got {min_net_profit_usd}")
    if max_slippage_bps <= 0:
        raise ValueError(f"max_slippage_bps must be positive, got {max_slippage_bps}")

    # Step 1: Query prices from multiple sources simultaneously
    venues_snapshot = scan_pair_venues(pair_name, custom_reserves)
    ps = venues_snapshot["venues"]["pharos_swap"]
    lh = venues_snapshot["venues"]["lighthouse_dex"]
    oracle_price = venues_snapshot["venues"]["pyth_oracle"]["benchmark_price"]

    # Step 2: Determine directional flow (Buy at lower spot, Sell at higher spot)
    if ps["spot_price"] < lh["spot_price"]:
        buy_venue = ps
        sell_venue = lh
    else:
        buy_venue = lh
        sell_venue = ps

    buy_spot = buy_venue["spot_price"]
    sell_spot = sell_venue["spot_price"]
    gross_spread_per_unit = sell_spot - buy_spot
    gross_spread_pct = (gross_spread_per_unit / buy_spot) * 100.0 if buy_spot > 0 else 0.0

    # Step 3: Gas Pricing (live testnet query if not provided)
    if not live_gas_info:
        live_gas_info = fetch_live_gas_price()
    gas_units_total = buy_venue["gas_units"] + sell_venue["gas_units"]
    gas_cost_data = calculate_gas_cost_usd(gas_units_total, live_gas_info["gas_price_gwei"])

    # If gross spread is negative or zero, skip immediately
    if gross_spread_per_unit <= 0:
        gross_spread_usd = 0.0
        waterfall = compute_net_waterfall(
            trade_volume_usd=trade_volume_usd,
            gross_spread_usd=0.0,
            gross_spread_pct=gross_spread_pct,
            buy_fee_usd=0.0,
            sell_fee_usd=0.0,
            buy_slippage_usd=0.0,
            sell_slippage_usd=0.0,
            gas_cost_usd=gas_cost_data["gas_cost_usd"],
            gas_units_total=gas_units_total
        )
        return {
            "timestamp": venues_snapshot["timestamp"],
            "pair": pair_name,
            "trade_volume_usd": trade_volume_usd,
            "min_net_profit_usd": min_net_profit_usd,
            "max_slippage_bps": max_slippage_bps,
            "buy_venue": buy_venue["name"],
            "buy_spot_price": buy_spot,
            "sell_venue": sell_venue["name"],
            "sell_spot_price": sell_spot,
            "oracle_benchmark_price": oracle_price,
            "waterfall": waterfall,
            "gas_details": live_gas_info,
            "decision": {
                "status": "SKIPPED_NEGATIVE_SPREAD",
                "is_eligible": False,
                "reason": f"No positive spread: Buy {buy_venue['name']} (${buy_spot:.4f}) >= Sell {sell_venue['name']} (${sell_spot:.4f})."
            }
        }

    # Step 4: Leg 1 Execution (Swap Quote Token -> Base Token on Buy Venue)
    # Input is trade_volume_usd (quote), output is base token
    leg1_impact = calculate_price_impact(
        amount_in=trade_volume_usd,
        reserve_in=buy_venue["reserve_quote"],
        reserve_out=buy_venue["reserve_base"],
        fee_ratio=buy_venue["fee_ratio"]
    )
    tokens_acquired = leg1_impact["amount_out"]
    buy_fee_usd = trade_volume_usd * buy_venue["fee_ratio"]
    buy_slippage_usd = leg1_impact["slippage_loss_tokens"] * buy_spot

    # Step 5: Leg 2 Execution (Swap Base Token -> Quote Token on Sell Venue)
    # Input is tokens_acquired (base), output is quote token (USD)
    leg2_impact = calculate_price_impact(
        amount_in=tokens_acquired,
        reserve_in=sell_venue["reserve_base"],
        reserve_out=sell_venue["reserve_quote"],
        fee_ratio=sell_venue["fee_ratio"]
    )
    final_quote_received = leg2_impact["amount_out"]
    sell_fee_usd = final_quote_received * sell_venue["fee_ratio"]
    sell_slippage_usd = leg2_impact["slippage_loss_tokens"]

    # Step 6: Gross Spread and Net Waterfall
    gross_spread_usd = trade_volume_usd * (gross_spread_pct / 100.0)
    waterfall = compute_net_waterfall(
        trade_volume_usd=trade_volume_usd,
        gross_spread_usd=gross_spread_usd,
        gross_spread_pct=gross_spread_pct,
        buy_fee_usd=buy_fee_usd,
        sell_fee_usd=sell_fee_usd,
        buy_slippage_usd=buy_slippage_usd,
        sell_slippage_usd=sell_slippage_usd,
        gas_cost_usd=gas_cost_data["gas_cost_usd"],
        gas_units_total=gas_units_total
    )

    # Step 7: Decision Gating
    combined_slippage_bps = leg1_impact["price_impact_bps"] + leg2_impact["price_impact_bps"]
    net_profit = waterfall["net_profit_usd"]

    if combined_slippage_bps > max_slippage_bps:
        status = "SKIPPED_EXCESSIVE_SLIPPAGE"
        is_eligible = False
        reason = (
            f"Excessive price impact: Combined slippage {combined_slippage_bps:.1f} bps "
            f"exceeds maximum allowed {max_slippage_bps} bps (Market risk guardrail)."
        )
    elif net_profit <= 0:
        status = "SKIPPED_UNPROFITABLE_AFTER_COSTS"
        is_eligible = False
        reason = (
            f"Gross spread +${gross_spread_usd:.2f} ({gross_spread_pct:.2f}%) was completely eroded by "
            f"fees (${waterfall['total_fees_usd']:.2f}), slippage (${waterfall['total_slippage_usd']:.2f}), "
            f"and gas (${waterfall['gas_cost_usd']:.4f}). Net result: -${abs(net_profit):.2f}."
        )
    elif net_profit < min_net_profit_usd:
        status = "SKIPPED_BELOW_MIN_PROFIT_THRESHOLD"
        is_eligible = False
        reason = (
            f"Net profit +${net_profit:.2f} is positive but below configured minimum threshold "
            f"${min_net_profit_usd:.2f} (Shortfall: ${min_net_profit_usd - net_profit:.2f})."
        )
    else:
        status = "ELIGIBLE_FOR_EXECUTION"
        is_eligible = True
        reason = (
            f"Opportunity verified! Net profit +${net_profit:.2f} ({waterfall['net_profit_pct']:.2f}%) "
            f"exceeds threshold ${min_net_profit_usd:.2f} with acceptable price impact {combined_slippage_bps:.1f} bps."
        )
    return {
        "timestamp": venues_snapshot["timestamp"],
        "pair": pair_name,
        "trade_volume_usd": trade_volume_usd,
        "min_net_profit_usd": min_net_profit_usd,
        "max_slippage_bps": max_slippage_bps,
        "buy_venue": {
            "name": buy_venue["name"],
            "id": buy_venue["id"],
            "spot_price": buy_spot,
            "effective_price": leg1_impact["effective_price"],
            "price_impact_bps": leg1_impact["price_impact_bps"],
            "fee_usd": round(buy_fee_usd, 4)
        },
        "sell_venue": {
            "name": sell_venue["name"],
            "id": sell_venue["id"],
            "spot_price": sell_spot,
            "effective_price": leg2_impact["effective_price"],
            "price_impact_bps": leg2_impact["price_impact_bps"],
            "fee_usd": round(sell_fee_usd, 4)
        },
        "combined_slippage_bps": round(combined_slippage_bps, 2),
        "oracle_benchmark_price": oracle_price,
        "waterfall": waterfall,
        "gas_details": live_gas_info,
        "decision": {
            "status": status,
            "is_eligible": is_eligible,
            "reason": reason
        }
    }
