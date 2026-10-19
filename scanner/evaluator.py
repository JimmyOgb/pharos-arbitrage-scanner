"""
Arbitrage Opportunity Evaluator & Decision Gating Engine
Executes dual-venue analysis, constant-product slippage calculation,
and waterfall cost netting. Enforces strict fail-closed safety.
Live Status: 'Live arbitrage unavailable — no verified liquidity'
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
    Evaluates multi-venue arbitrage for a given pair and trade volume.
    
    Truthfulness Enforcement:
    1. Production Live Audit: Chainlink push feeds on Pharos RPC (Chain 1672) provide
       reference benchmark prices, NOT executable AMM pool quotes.
       Atlantic Testnet (Chain 688689) currently has 0 verified AMM pool bytecodes.
       Therefore, live production status is strictly:
       "Live arbitrage unavailable — no verified liquidity" (is_eligible: False).
    2. Unit Test Math Harness: Evaluates constant-product formulas (x·y=k), fees,
       and waterfall netting strictly in unit tests with 'TEST_FIXTURE' status tags.
       Never emits 'ELIGIBLE_FOR_EXECUTION'.
    """
    if trade_volume_usd <= 0:
        raise ValueError(f"trade_volume_usd must be positive, got {trade_volume_usd}")
    if min_net_profit_usd < 0:
        raise ValueError(f"min_net_profit_usd cannot be negative, got {min_net_profit_usd}")
    if max_slippage_bps <= 0:
        raise ValueError(f"max_slippage_bps must be positive, got {max_slippage_bps}")

    # Fetch gas details if not supplied
    if not live_gas_info:
        live_gas_info = fetch_live_gas_price()

    venues_snapshot = scan_pair_venues(pair_name, custom_reserves)

    # Mode 1: Production Live Evaluation
    if not venues_snapshot.get("is_test_fixture", False):
        chainlink_venue = venues_snapshot["venues"]["chainlink_reference_oracle"]
        amm_venue = venues_snapshot["venues"]["atlantic_amm_router"]
        spot_price = chainlink_venue.get("reference_price_usd")

        # Check oracle availability
        if not chainlink_venue.get("is_available", False) or spot_price is None:
            return {
                "timestamp": venues_snapshot["timestamp"],
                "pair": pair_name,
                "data_mode": "PRODUCTION_LIVE_AUDIT",
                "trade_volume_usd": trade_volume_usd,
                "min_net_profit_usd": min_net_profit_usd,
                "max_slippage_bps": max_slippage_bps,
                "reference_oracle_price": None,
                "oracle_venue": chainlink_venue,
                "amm_venue": amm_venue,
                "gas_details": live_gas_info,
                "waterfall": None,
                "decision": {
                    "status": "LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY",
                    "is_eligible": False,
                    "reason": f"Live arbitrage unavailable — no verified liquidity. Reference oracle from Pharos RPC (Chain 1672) is unreachable ({chainlink_venue.get('error')}) and Atlantic Testnet (Chain 688689) has no deployed AMM liquidity pools."
                }
            }

        return {
            "timestamp": venues_snapshot["timestamp"],
            "pair": pair_name,
            "data_mode": "PRODUCTION_LIVE_AUDIT",
            "trade_volume_usd": trade_volume_usd,
            "min_net_profit_usd": min_net_profit_usd,
            "max_slippage_bps": max_slippage_bps,
            "reference_oracle_price": spot_price,
            "oracle_venue": chainlink_venue,
            "amm_venue": amm_venue,
            "gas_details": live_gas_info,
            "waterfall": None,
            "decision": {
                "status": "LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY",
                "is_eligible": False,
                "reason": (
                    f"Live arbitrage unavailable — no verified liquidity. "
                    f"Verified Chainlink reference price is ${spot_price:,.2f} on Pharos RPC (Chain ID 1672). "
                    f"However, reference oracles are non-executable benchmark feeds, and Pharos Atlantic Testnet (Chain ID 688689) "
                    f"currently has 0 deployed AMM liquidity pools or router contracts (0x bytecode). "
                    f"Two independent executable venue quotes are required for real arbitrage."
                )
            }
        }

    # Mode 2: Isolated Mathematical Unit Test Harness
    venues = venues_snapshot["venues"]
    va = venues["test_venue_a"]
    vb = venues["test_venue_b"]

    # Directional Flow for Test Math
    if va["spot_price"] < vb["spot_price"]:
        buy_venue = va
        sell_venue = vb
    else:
        buy_venue = vb
        sell_venue = va

    buy_spot = buy_venue["spot_price"]
    sell_spot = sell_venue["spot_price"]
    gross_spread_per_unit = sell_spot - buy_spot
    gross_spread_pct = (gross_spread_per_unit / buy_spot) * 100.0 if buy_spot > 0 else 0.0

    gas_units_total = buy_venue["gas_units"] + sell_venue["gas_units"]
    gas_gwei = live_gas_info.get("gas_price_gwei") if live_gas_info.get("gas_price_gwei") is not None else 10.0
    gas_cost_data = calculate_gas_cost_usd(gas_units_total, gas_gwei)

    # Inverted / Negative Spread Gate in Math Test
    if gross_spread_per_unit <= 0:
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
            "data_mode": "ISOLATED_TEST_FIXTURE",
            "trade_volume_usd": trade_volume_usd,
            "min_net_profit_usd": min_net_profit_usd,
            "max_slippage_bps": max_slippage_bps,
            "buy_venue": {"name": buy_venue["name"], "spot_price": buy_spot},
            "sell_venue": {"name": sell_venue["name"], "spot_price": sell_spot},
            "waterfall": waterfall,
            "gas_details": live_gas_info,
            "decision": {
                "status": "TEST_FIXTURE_NEGATIVE_SPREAD",
                "is_eligible": False,
                "fixture_threshold_passed": False,
                "reason": f"[TEST FIXTURE] Negative or zero spread: Buy {buy_venue['name']} (${buy_spot:.4f}) >= Sell {sell_venue['name']} (${sell_spot:.4f})."
            }
        }

    # Leg 1: Swap Quote -> Base on Buy Venue
    leg1_impact = calculate_price_impact(
        amount_in=trade_volume_usd,
        reserve_in=buy_venue["reserve_quote"],
        reserve_out=buy_venue["reserve_base"],
        fee_ratio=buy_venue["fee_ratio"]
    )
    tokens_acquired = leg1_impact["amount_out"]
    buy_fee_usd = trade_volume_usd * buy_venue["fee_ratio"]
    buy_slippage_usd = leg1_impact["slippage_loss_tokens"] * buy_spot

    # Leg 2: Swap Base -> Quote on Sell Venue
    leg2_impact = calculate_price_impact(
        amount_in=tokens_acquired,
        reserve_in=sell_venue["reserve_base"],
        reserve_out=sell_venue["reserve_quote"],
        fee_ratio=sell_venue["fee_ratio"]
    )
    final_quote_received = leg2_impact["amount_out"]
    sell_fee_usd = final_quote_received * sell_venue["fee_ratio"]
    sell_slippage_usd = leg2_impact["slippage_loss_tokens"]

    # Waterfall Friction Deductions
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

    combined_slippage_bps = leg1_impact["price_impact_bps"] + leg2_impact["price_impact_bps"]
    net_profit = waterfall["net_profit_usd"]

    if combined_slippage_bps > max_slippage_bps:
        status = "TEST_FIXTURE_EXCESSIVE_SLIPPAGE"
        fixture_passed = False
        reason = (
            f"[TEST FIXTURE] Excessive price impact: Combined slippage {combined_slippage_bps:.1f} bps "
            f"exceeds maximum allowed {max_slippage_bps} bps."
        )
    elif net_profit <= 0:
        status = "TEST_FIXTURE_UNPROFITABLE_AFTER_COSTS"
        fixture_passed = False
        reason = (
            f"[TEST FIXTURE] Gross spread +${gross_spread_usd:.2f} was eroded by "
            f"fees (${waterfall['total_fees_usd']:.2f}), slippage (${waterfall['total_slippage_usd']:.2f}), "
            f"and gas (${waterfall['gas_cost_usd']:.4f}). Net: -${abs(net_profit):.2f}."
        )
    elif net_profit < min_net_profit_usd:
        status = "TEST_FIXTURE_BELOW_MIN_PROFIT_THRESHOLD"
        fixture_passed = False
        reason = (
            f"[TEST FIXTURE] Net profit +${net_profit:.2f} is positive but below threshold "
            f"${min_net_profit_usd:.2f} (Shortfall: ${min_net_profit_usd - net_profit:.2f})."
        )
    else:
        status = "TEST_FIXTURE_THRESHOLD_MET"
        fixture_passed = True
        reason = (
            f"[TEST FIXTURE] Mathematical model validated. Synthetic profit +${net_profit:.2f} ({waterfall['net_profit_pct']:.2f}%) "
            f"exceeds threshold ${min_net_profit_usd:.2f} with slippage {combined_slippage_bps:.1f} bps."
        )

    return {
        "timestamp": venues_snapshot["timestamp"],
        "pair": pair_name,
        "data_mode": "ISOLATED_TEST_FIXTURE",
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
        "waterfall": waterfall,
        "gas_details": live_gas_info,
        "decision": {
            "status": status,
            "is_eligible": False,  # Execution is strictly disabled in production
            "fixture_threshold_passed": fixture_passed,
            "reason": reason
        }
    }
