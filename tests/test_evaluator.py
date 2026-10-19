"""
Unit Tests for Arbitrage Evaluator, Threshold Gating, and Decision Logging
"""

import pytest
from scanner.evaluator import evaluate_arbitrage


def test_profitable_opportunity_evaluation():
    # PHRS/USDC with default reserves has a 2.4% spread (2.50 vs 2.56)
    # Trade volume: $2,500. Gas: 10 Gwei.
    res = evaluate_arbitrage(
        pair_name="PHRS/USDC",
        trade_volume_usd=2500.0,
        min_net_profit_usd=5.0,
        max_slippage_bps=150
    )
    assert res["decision"]["is_eligible"] is True
    assert res["decision"]["status"] == "ELIGIBLE_FOR_EXECUTION"
    assert res["waterfall"]["net_profit_usd"] > 5.0
    assert "verified" in res["decision"]["reason"].lower()


def test_unprofitable_after_costs_status():
    # Thin spread scenario (0.2%) with deep reserves: fees exceed gross spread, but slippage is low
    custom = {
        "pharos_swap": {"reserve_base": 200000.0, "reserve_quote": 500000.0},     # 2.50
        "lighthouse_dex": {"reserve_base": 200000.0, "reserve_quote": 501000.0}   # 2.505 (0.2% spread)
    }
    res = evaluate_arbitrage(
        pair_name="PHRS/USDC",
        trade_volume_usd=2000.0,
        min_net_profit_usd=5.0,
        max_slippage_bps=150,
        custom_reserves=custom
    )
    assert res["decision"]["is_eligible"] is False
    assert res["decision"]["status"] == "SKIPPED_UNPROFITABLE_AFTER_COSTS"
    assert res["waterfall"]["net_profit_usd"] < 0
    assert "eroded" in res["decision"]["reason"].lower()


def test_below_threshold_status():
    # Spread produces ~+$17.00 net profit, but threshold is $25.00
    custom = {
        "pharos_swap": {"reserve_base": 200000.0, "reserve_quote": 500000.0},    # 2.50
        "lighthouse_dex": {"reserve_base": 200000.0, "reserve_quote": 515000.0}  # 2.575
    }
    res = evaluate_arbitrage(
        pair_name="PHRS/USDC",
        trade_volume_usd=1000.0,
        min_net_profit_usd=25.0,  # Threshold higher than net profit
        max_slippage_bps=150,
        custom_reserves=custom
    )
    assert res["decision"]["is_eligible"] is False
    assert res["decision"]["status"] == "SKIPPED_BELOW_MIN_PROFIT_THRESHOLD"
    assert "below configured minimum threshold" in res["decision"]["reason"]


def test_excessive_slippage_status():
    # Huge trade volume into shallow pool -> high slippage exceeds 50 bps limit
    custom = {
        "pharos_swap": {"reserve_base": 5000.0, "reserve_quote": 12500.0},     # 2.50
        "lighthouse_dex": {"reserve_base": 5000.0, "reserve_quote": 13500.0}   # 2.70
    }
    res = evaluate_arbitrage(
        pair_name="PHRS/USDC",
        trade_volume_usd=4000.0,  # Large trade relative to 12.5k reserve
        min_net_profit_usd=5.0,
        max_slippage_bps=50,  # Very strict 0.5% max slippage
        custom_reserves=custom
    )
    assert res["decision"]["is_eligible"] is False
    assert res["decision"]["status"] == "SKIPPED_EXCESSIVE_SLIPPAGE"
    assert "price impact" in res["decision"]["reason"]


def test_negative_spread_status():
    # Inverted market: Buy venue is more expensive than sell venue
    custom = {
        "pharos_swap": {"reserve_base": 50000.0, "reserve_quote": 130000.0},   # 2.60
        "lighthouse_dex": {"reserve_base": 50000.0, "reserve_quote": 125000.0} # 2.50
    }
    # Evaluator automatically checks both directions; if both have no profitable spread or equal
    custom_equal = {
        "pharos_swap": {"reserve_base": 50000.0, "reserve_quote": 125000.0},
        "lighthouse_dex": {"reserve_base": 50000.0, "reserve_quote": 125000.0}
    }
    res = evaluate_arbitrage(
        pair_name="PHRS/USDC",
        trade_volume_usd=2500.0,
        custom_reserves=custom_equal
    )
    assert res["decision"]["is_eligible"] is False
    assert res["decision"]["status"] == "SKIPPED_NEGATIVE_SPREAD"


def test_invalid_thresholds_raise_error():
    with pytest.raises(ValueError):
        evaluate_arbitrage("PHRS/USDC", trade_volume_usd=-100)
    with pytest.raises(ValueError):
        evaluate_arbitrage("PHRS/USDC", min_net_profit_usd=-5.0)
    with pytest.raises(ValueError):
        evaluate_arbitrage("PHRS/USDC", max_slippage_bps=-10)


def test_high_gas_price_erodes_margin():
    # If gas price spikes 100x (1,000 Gwei = $0.75 gas cost on 300k gas),
    # a micro profit of $0.50 gets completely wiped out
    gas_spike = {
        "source": "MOCK_SPIKE",
        "rpc_url": "mock",
        "gas_price_wei": int(1000 * 1e9),
        "gas_price_gwei": 1000.0,
        "block_number": 31608000,
        "is_live": False
    }
    custom = {
        "pharos_swap": {"reserve_base": 200000.0, "reserve_quote": 500000.0},
        "lighthouse_dex": {"reserve_base": 200000.0, "reserve_quote": 503500.0}
    }
    res = evaluate_arbitrage(
        pair_name="PHRS/USDC",
        trade_volume_usd=500.0,
        min_net_profit_usd=1.0,
        custom_reserves=custom,
        live_gas_info=gas_spike
    )
    assert res["waterfall"]["gas_cost_usd"] > 0.50
    assert res["decision"]["is_eligible"] is False


def test_multi_pair_batch_evaluation():
    from scanner.venues import get_supported_pairs
    pairs = get_supported_pairs()
    for p in pairs:
        res = evaluate_arbitrage(p, trade_volume_usd=1000.0)
        assert res["pair"] == p
        assert "waterfall" in res
        assert "decision" in res
