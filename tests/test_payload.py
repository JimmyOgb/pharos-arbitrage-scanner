"""
Unit Tests for Calldata Payload Generation and Safe Simulation
"""

import pytest
from scanner.evaluator import evaluate_arbitrage
from scanner.payload import generate_atomic_payload, execute_simulated_trade


def test_generate_atomic_payload_eligible():
    eval_res = evaluate_arbitrage("PHRS/USDC", trade_volume_usd=2500.0, min_net_profit_usd=5.0)
    payload = generate_atomic_payload(eval_res)

    assert payload["type"] == "ATOMIC_ARBITRAGE_BUNDLE"
    assert payload["chain_id"] == 688689
    assert payload["is_simulated"] is True
    assert len(payload["legs"]) == 2
    assert payload["legs"][0]["step"] == 1
    assert payload["legs"][1]["step"] == 2
    assert payload["legs"][0]["encoded_calldata"].startswith("0x38ed1739")


def test_generate_atomic_payload_ineligible_raises_error():
    custom_equal = {
        "pharos_swap": {"reserve_base": 50000.0, "reserve_quote": 125000.0},
        "lighthouse_dex": {"reserve_base": 50000.0, "reserve_quote": 125000.0}
    }
    ineligible = evaluate_arbitrage("PHRS/USDC", custom_reserves=custom_equal)
    with pytest.raises(ValueError) as exc:
        generate_atomic_payload(ineligible)
    assert "Cannot generate execution payload" in str(exc.value)


def test_execute_simulated_trade():
    eval_res = evaluate_arbitrage("PHRS/USDC", trade_volume_usd=2500.0, min_net_profit_usd=5.0)
    payload = generate_atomic_payload(eval_res)
    receipt = execute_simulated_trade(payload)

    assert receipt["status"] == "CONFIRMED"
    assert receipt["receipt_type"] == "SIMULATED_TESTNET_RECEIPT"
    assert receipt["tx_hash"].startswith("0xsim_arb_")
    assert receipt["chain_id"] == 688689
    assert receipt["gas_used"] == 295000
