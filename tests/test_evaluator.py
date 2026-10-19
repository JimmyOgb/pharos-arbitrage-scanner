"""
Unit Tests for Arbitrage Evaluator, Live Fail-Closed Safety, and Mathematical Model
"""

import pytest
from scanner.evaluator import evaluate_arbitrage
from scanner.venues import get_supported_pairs


def test_live_evaluator_fails_closed():
    # Live scan of BTC/USD against verified on-chain push oracle
    res = evaluate_arbitrage("BTC/USD", trade_volume_usd=5000.0)
    assert res["data_mode"] == "PRODUCTION_LIVE_AUDIT"
    assert res["decision"]["is_eligible"] is False
    assert res["decision"]["status"] == "LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY"
    assert "no verified liquidity" in res["decision"]["reason"].lower()


def test_mathematical_model_profitable():
    custom = {
        "test_venue_a": {"name": "Test A", "reserve_base": 200000.0, "reserve_quote": 500000.0, "fee_ratio": 0.003, "gas_units": 140000},
        "test_venue_b": {"name": "Test B", "reserve_base": 200000.0, "reserve_quote": 512000.0, "fee_ratio": 0.0025, "gas_units": 155000}
    }
    res = evaluate_arbitrage(
        pair_name="TEST/USD",
        trade_volume_usd=2500.0,
        min_net_profit_usd=5.0,
        max_slippage_bps=150,
        custom_reserves=custom
    )
    assert res["data_mode"] == "ISOLATED_TEST_FIXTURE"
    assert res["decision"]["is_eligible"] is False  # Production execution is always disabled
    assert res["decision"]["fixture_threshold_passed"] is True
    assert res["decision"]["status"] == "TEST_FIXTURE_THRESHOLD_MET"
    assert res["waterfall"]["net_profit_usd"] > 5.0


def test_unprofitable_after_costs_status():
    custom = {
        "test_venue_a": {"name": "Test A", "reserve_base": 200000.0, "reserve_quote": 500000.0, "fee_ratio": 0.003, "gas_units": 140000},
        "test_venue_b": {"name": "Test B", "reserve_base": 200000.0, "reserve_quote": 501000.0, "fee_ratio": 0.0025, "gas_units": 155000}
    }
    res = evaluate_arbitrage(
        pair_name="TEST/USD",
        trade_volume_usd=2000.0,
        min_net_profit_usd=5.0,
        max_slippage_bps=150,
        custom_reserves=custom
    )
    assert res["decision"]["fixture_threshold_passed"] is False
    assert res["decision"]["status"] == "TEST_FIXTURE_UNPROFITABLE_AFTER_COSTS"
    assert res["waterfall"]["net_profit_usd"] < 0


def test_below_threshold_status():
    custom = {
        "test_venue_a": {"name": "Test A", "reserve_base": 200000.0, "reserve_quote": 500000.0, "fee_ratio": 0.003, "gas_units": 140000},
        "test_venue_b": {"name": "Test B", "reserve_base": 200000.0, "reserve_quote": 515000.0, "fee_ratio": 0.0025, "gas_units": 155000}
    }
    res = evaluate_arbitrage(
        pair_name="TEST/USD",
        trade_volume_usd=1000.0,
        min_net_profit_usd=25.0,
        max_slippage_bps=150,
        custom_reserves=custom
    )
    assert res["decision"]["fixture_threshold_passed"] is False
    assert res["decision"]["status"] == "TEST_FIXTURE_BELOW_MIN_PROFIT_THRESHOLD"


def test_excessive_slippage_status():
    custom = {
        "test_venue_a": {"name": "Test A", "reserve_base": 5000.0, "reserve_quote": 12500.0, "fee_ratio": 0.003, "gas_units": 140000},
        "test_venue_b": {"name": "Test B", "reserve_base": 5000.0, "reserve_quote": 13500.0, "fee_ratio": 0.0025, "gas_units": 155000}
    }
    res = evaluate_arbitrage(
        pair_name="TEST/USD",
        trade_volume_usd=4000.0,
        min_net_profit_usd=5.0,
        max_slippage_bps=50,
        custom_reserves=custom
    )
    assert res["decision"]["fixture_threshold_passed"] is False
    assert res["decision"]["status"] == "TEST_FIXTURE_EXCESSIVE_SLIPPAGE"


def test_negative_spread_status():
    custom_equal = {
        "test_venue_a": {"name": "Test A", "reserve_base": 50000.0, "reserve_quote": 125000.0, "fee_ratio": 0.003, "gas_units": 140000},
        "test_venue_b": {"name": "Test B", "reserve_base": 50000.0, "reserve_quote": 125000.0, "fee_ratio": 0.0025, "gas_units": 155000}
    }
    res = evaluate_arbitrage(
        pair_name="TEST/USD",
        trade_volume_usd=2500.0,
        custom_reserves=custom_equal
    )
    assert res["decision"]["is_eligible"] is False
    assert res["decision"]["status"] == "TEST_FIXTURE_NEGATIVE_SPREAD"


def test_invalid_thresholds_raise_error():
    with pytest.raises(ValueError):
        evaluate_arbitrage("BTC/USD", trade_volume_usd=-100)
    with pytest.raises(ValueError):
        evaluate_arbitrage("BTC/USD", min_net_profit_usd=-5.0)
    with pytest.raises(ValueError):
        evaluate_arbitrage("BTC/USD", max_slippage_bps=-10)


def test_high_gas_price_erodes_margin():
    gas_spike = {
        "source": "SIMULATED_SPIKE",
        "rpc_url": "test",
        "gas_price_wei": int(1000 * 1e9),
        "gas_price_gwei": 1000.0,
        "block_number": 31608000,
        "is_live": False
    }
    custom = {
        "test_venue_a": {"name": "Test A", "reserve_base": 200000.0, "reserve_quote": 500000.0, "fee_ratio": 0.003, "gas_units": 140000},
        "test_venue_b": {"name": "Test B", "reserve_base": 200000.0, "reserve_quote": 503500.0, "fee_ratio": 0.0025, "gas_units": 155000}
    }
    res = evaluate_arbitrage(
        pair_name="TEST/USD",
        trade_volume_usd=500.0,
        min_net_profit_usd=1.0,
        custom_reserves=custom,
        live_gas_info=gas_spike
    )
    assert res["waterfall"]["gas_cost_usd"] > 0.50
    assert res["decision"]["fixture_threshold_passed"] is False


def test_multi_pair_batch_evaluation():
    pairs = get_supported_pairs()
    for p in pairs:
        res = evaluate_arbitrage(p, trade_volume_usd=1000.0)
        assert res["pair"] == p
        assert res["data_mode"] == "PRODUCTION_LIVE_AUDIT"
        assert res["decision"]["status"] == "LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY"
