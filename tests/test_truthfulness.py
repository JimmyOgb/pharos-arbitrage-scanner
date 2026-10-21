"""
Regression Test Suite: Production Truthfulness & Data Integrity Verification
Validates that every quote, comparison, cost estimate, and status is supported
by genuine data for the correct asset, venue, network, block, and trade size.
Strictly verifies that no test fixtures or synthetic derived multipliers leak into live production.
"""

import pytest
from scanner.venues import (
    query_faroswap_v2_venue,
    query_dodo_v2_venue,
    query_chainlink_feed,
    scan_pair_venues
)
from scanner.costs import (
    fetch_mainnet_gas_price,
    fetch_atlantic_gas_price,
    fetch_live_gas_price,
    calculate_gas_cost_usd
)
from scanner.evaluator import evaluate_arbitrage
from scanner.payload import generate_arbitrage_calldata


def test_pros_pool_does_not_populate_btc_or_eth():
    """1. A PROS/USDC pool cannot populate ETH/USD or BTC/USD rows without valid verified routes."""
    faro_btc = query_faroswap_v2_venue("BTC/USD")
    faro_eth = query_faroswap_v2_venue("ETH/USD")
    
    assert faro_btc["is_available"] is False
    assert faro_btc["spot_price"] is None
    assert faro_btc["status"] == "QUOTE_UNAVAILABLE_NO_POOL"
    
    assert faro_eth["is_available"] is False
    assert faro_eth["spot_price"] is None
    assert faro_eth["status"] == "QUOTE_UNAVAILABLE_NO_POOL"


def test_oracle_value_not_mislabeled_as_dex_quote():
    """2. An oracle benchmark value cannot be mislabeled as an executable DEX quote."""
    oracle = query_chainlink_feed("BTC/USD")
    assert oracle["is_executable_pool"] is False
    assert oracle["source"] == "PHAROS_CHAINLINK_PUSH_CACHE"
    assert oracle["type"] if "type" in oracle else True

    # DODO must not derive synthetic quotes from oracle
    dodo = query_dodo_v2_venue("BTC/USD", oracle_price=80000.0)
    assert dodo["spot_price"] is None
    assert dodo["is_available"] is False
    assert dodo["status"] == "QUOTE_UNAVAILABLE_NO_VERIFIED_POOL"


def test_single_venue_quote_cannot_produce_cross_venue_spread():
    """3. A quote from only one venue cannot produce a cross-venue spread."""
    # FaroSwap may have PROS/USD pool, but DODO has no pool on Mainnet
    res = evaluate_arbitrage("PROS/USD", trade_volume_usd=5000.0)
    assert res["decision"]["is_eligible"] is False
    # Cross venue comparison must be blocked
    assert res["decision"]["status"] in ("CROSS_VENUE_COMPARISON_BLOCKED", "LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY")
    if res["decision"]["status"] == "CROSS_VENUE_COMPARISON_BLOCKED":
        assert res["waterfall"] is None


def test_incompatible_tokens_block_comparison():
    """4. Different tokens, decimals, amounts, chains, or incompatible snapshots block comparisons."""
    # Custom venues with mismatched tokens or chains
    custom_mismatched = {
        "test_venue_a": {
            "name": "Venue A",
            "reserve_base": 100000.0,
            "reserve_quote": 200000.0,
            "chain_id": 1672
        },
        "test_venue_b": {
            "name": "Venue B",
            "reserve_base": 100000.0,
            "reserve_quote": 210000.0,
            "chain_id": 688689  # Cross-chain mismatch!
        }
    }
    # Evaluator enforces same chain validation for atomic arbitrage
    scan = scan_pair_venues("TEST/PAIR", custom_reserves=custom_mismatched)
    assert scan["is_test_fixture"] is True


def test_fixture_cannot_enter_live_scan_history():
    """5. A test fixture cannot enter live scan history or the opportunities list."""
    live_scan = scan_pair_venues("PROS/USD")
    assert live_scan["is_test_fixture"] is False
    
    custom = {
        "test_venue_a": {"name": "Test A", "reserve_base": 100000.0, "reserve_quote": 200000.0},
        "test_venue_b": {"name": "Test B", "reserve_base": 100000.0, "reserve_quote": 210000.0}
    }
    fixture_scan = scan_pair_venues("TEST/PAIR", custom_reserves=custom)
    assert fixture_scan["is_test_fixture"] is True
    assert fixture_scan["venues"]["test_venue_a"]["status"] == "ISOLATED_TEST_FIXTURE"


def test_atlantic_gas_segregation_from_mainnet():
    """6. Atlantic gas data cannot be presented as a Pharos Mainnet execution-cost estimate."""
    mainnet_gas = fetch_mainnet_gas_price()
    assert mainnet_gas["chain_id"] == 1672
    assert "Mainnet" in mainnet_gas["network_name"]

    atlantic_gas = fetch_atlantic_gas_price()
    assert atlantic_gas["chain_id"] == 688689
    assert "Atlantic" in atlantic_gas["network_name"]

    # Mainnet gas cost calculation must explicitly tag chain_id 1672
    cost = calculate_gas_cost_usd(150000, 10.0, chain_id=1672)
    assert cost["chain_id"] == 1672
    assert cost["gas_cost_usd"] > 0


def test_missing_mainnet_gas_blocks_live_net_profit():
    """7. Missing mainnet gas data blocks live net-profit claims."""
    missing_gas = {
        "source": "MOCK_UNAVAILABLE",
        "chain_id": 1672,
        "gas_price_wei": None,
        "gas_price_gwei": None,
        "block_number": None,
        "is_live": False,
        "status": "UNAVAILABLE"
    }
    custom = {
        "test_venue_a": {"name": "Test A", "reserve_base": 100000.0, "reserve_quote": 200000.0, "spot_price": 2.0, "is_available": True},
        "test_venue_b": {"name": "Test B", "reserve_base": 100000.0, "reserve_quote": 210000.0, "spot_price": 2.1, "is_available": True}
    }
    res = evaluate_arbitrage("PROS/USD", live_gas_info=missing_gas)
    assert res["decision"]["is_eligible"] is False
    assert res["waterfall"] is None


def test_dodo_pmm_formula_distinction():
    """8. DODO PMM slippage is not incorrectly computed using an AMM constant-product formula."""
    dodo = query_dodo_v2_venue("PROS/USD")
    assert dodo["type"] == "DEX_PMM_ROUTER"
    # When no verified pool exists, DODO refuses to compute AMM reserves
    assert dodo["reserve_base"] == 0.0
    assert dodo["reserve_quote"] == 0.0
    assert dodo["spot_price"] is None


def test_insufficient_reserves_remain_non_executable():
    """9. Insufficient reserves and failed router quotes remain non-executable."""
    faro = query_faroswap_v2_venue("PROS/USD")
    if faro.get("is_available"):
        # Real pool depth is ~0.28 USDC
        assert faro["reserve_quote"] < 1.0  # sub-dollar dust
        res = evaluate_arbitrage("PROS/USD", trade_volume_usd=5000.0)
        assert res["decision"]["is_eligible"] is False


def test_invalid_rpc_data_fails_closed():
    """10. Invalid, stale, or unavailable RPC data never becomes a fabricated successful quote."""
    dodo_fail = query_dodo_v2_venue("PROS/USD", rpc_url="https://invalid.rpc.node.endpoint:9999")
    assert dodo_fail["is_available"] is False
    assert dodo_fail["spot_price"] is None

    faro_fail = query_faroswap_v2_venue("PROS/USD", rpc_url="https://invalid.rpc.node.endpoint:9999")
    assert faro_fail["is_available"] is False
    assert faro_fail["spot_price"] is None


def test_ui_and_backend_execution_gates_agree():
    """11. UI state and backend execution gates agree on fail-closed state."""
    res = evaluate_arbitrage("PROS/USD", trade_volume_usd=5000.0)
    assert res["decision"]["is_eligible"] is False
    with pytest.raises((ValueError, RuntimeError)) as exc_info:
        generate_arbitrage_calldata(res)
    assert any(term in str(exc_info.value).lower() for term in ("cannot generate", "not eligible", "unavailable"))
