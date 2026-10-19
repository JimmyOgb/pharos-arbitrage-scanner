"""
Unit Tests for Calldata Payload Generation and Safety Guard Enforcement
"""

import pytest
from scanner.evaluator import evaluate_arbitrage
from scanner.payload import generate_arbitrage_calldata


def test_generate_arbitrage_calldata_eligible():
    custom = {
        "venue_a": {"name": "Test A", "reserve_base": 200000.0, "reserve_quote": 500000.0, "fee_ratio": 0.003, "gas_units": 140000},
        "venue_b": {"name": "Test B", "reserve_base": 200000.0, "reserve_quote": 512000.0, "fee_ratio": 0.0025, "gas_units": 155000}
    }
    eval_res = evaluate_arbitrage("BTC/USD", trade_volume_usd=2500.0, min_net_profit_usd=5.0, custom_reserves=custom)
    assert eval_res["decision"]["is_eligible"] is True

    payload = generate_arbitrage_calldata(eval_res)
    assert payload["type"] == "ATOMIC_ARBITRAGE_BUNDLE"
    assert payload["chain_id"] == 688689
    assert payload["execution_enabled"] is False
    assert payload["safety_guard"] == "FAIL_CLOSED_NO_DEPLOYED_ROUTER"
    assert len(payload["legs"]) == 2
    assert payload["legs"][0]["step"] == 1
    assert payload["legs"][1]["step"] == 2
    assert payload["legs"][0]["selector"] == "0x38ed1739"


def test_generate_arbitrage_calldata_ineligible_raises_error():
    custom_equal = {
        "venue_a": {"name": "Test A", "reserve_base": 50000.0, "reserve_quote": 125000.0, "fee_ratio": 0.003, "gas_units": 140000},
        "venue_b": {"name": "Test B", "reserve_base": 50000.0, "reserve_quote": 125000.0, "fee_ratio": 0.0025, "gas_units": 155000}
    }
    ineligible = evaluate_arbitrage("BTC/USD", custom_reserves=custom_equal)
    assert ineligible["decision"]["is_eligible"] is False
    with pytest.raises(ValueError) as exc:
        generate_arbitrage_calldata(ineligible)
    assert "Cannot generate execution payload" in str(exc.value)
