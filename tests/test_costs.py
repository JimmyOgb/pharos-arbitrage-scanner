"""
Unit Tests for Cost Estimation and Profit Waterfall Deductions
"""

import pytest
from scanner.costs import (
    calculate_gas_cost_usd,
    compute_net_waterfall,
    fetch_live_gas_price
)


def test_gas_cost_calculation_usd():
    # 300,000 gas units, 10.0 Gwei, $2.50 per PHRS
    # 300,000 * 10 * 1e-9 = 0.003 PHRS
    # 0.003 * 2.50 = 0.0075 USD
    res = calculate_gas_cost_usd(300000, 10.0, 2.50)
    assert res["gas_cost_phrs"] == 0.003
    assert res["gas_cost_usd"] == 0.0075


def test_waterfall_net_profit_deduction():
    # Volume $5,000, Gross Spread $120 (2.4%)
    # Buy Fee $15, Sell Fee $12.50 -> Fees = $27.50
    # Buy Slippage $25, Sell Slippage $25 -> Slippage = $50.00
    # Gas = $0.01
    # Total friction = $77.51
    # Net profit = 120 - 77.51 = 42.49
    wf = compute_net_waterfall(
        trade_volume_usd=5000.0,
        gross_spread_usd=120.0,
        gross_spread_pct=2.40,
        buy_fee_usd=15.0,
        sell_fee_usd=12.50,
        buy_slippage_usd=25.0,
        sell_slippage_usd=25.0,
        gas_cost_usd=0.01,
        gas_units_total=300000
    )
    assert wf["is_profitable"] is True
    assert round(wf["total_fees_usd"], 2) == 27.50
    assert round(wf["total_slippage_usd"], 2) == 50.00
    assert round(wf["total_friction_usd"], 2) == 77.51
    assert round(wf["net_profit_usd"], 2) == 42.49


def test_waterfall_unprofitable_opportunity():
    # Small gross spread $20 wiped out by $50 friction
    wf = compute_net_waterfall(
        trade_volume_usd=5000.0,
        gross_spread_usd=20.0,
        gross_spread_pct=0.40,
        buy_fee_usd=15.0,
        sell_fee_usd=15.0,
        buy_slippage_usd=15.0,
        sell_slippage_usd=15.0,
        gas_cost_usd=0.01,
        gas_units_total=300000
    )
    assert wf["is_profitable"] is False
    assert wf["net_profit_usd"] < 0


def test_negative_costs_raise_error():
    with pytest.raises(ValueError):
        calculate_gas_cost_usd(-100, 10.0)
    with pytest.raises(ValueError):
        calculate_gas_cost_usd(100, -5.0)
    with pytest.raises(ValueError):
        compute_net_waterfall(
            trade_volume_usd=-5000.0,
            gross_spread_usd=100.0,
            gross_spread_pct=2.0,
            buy_fee_usd=10.0,
            sell_fee_usd=10.0,
            buy_slippage_usd=10.0,
            sell_slippage_usd=10.0,
            gas_cost_usd=0.01,
            gas_units_total=100000
        )


def test_fallback_gas_price():
    # When pointed at unreachable RPC, fallback safely returns testnet standard 10 Gwei
    res = fetch_live_gas_price(rpc_url="http://127.0.0.1:9999/unreachable", timeout=0.1)
    assert res["is_live"] is False
    assert res["gas_price_gwei"] == 10.0
    assert "fallback_notice" in res
