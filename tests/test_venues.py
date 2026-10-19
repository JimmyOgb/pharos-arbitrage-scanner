"""
Unit Tests for Multi-Venue Discovery, On-Chain Feeds, and Bytecode Verification
"""

import pytest
from scanner.venues import (
    load_venues_config,
    get_supported_pairs,
    scan_pair_venues,
    query_chainlink_feed,
    check_on_chain_amm_pool
)


def test_load_venues_config():
    config = load_venues_config()
    assert "venues" in config
    assert "chainlink_feeds_cache" in config["venues"]
    assert "chainlink_btc_proxy" in config["venues"]
    assert "verified_feeds" in config
    assert "verified_tokens" in config


def test_get_supported_pairs():
    pairs = get_supported_pairs()
    assert "BTC/USD" in pairs
    assert "ETH/USD" in pairs
    assert "PROS/USD" in pairs


def test_query_chainlink_feed_live():
    data = query_chainlink_feed("BTC/USD")
    if not data.get("is_available", False):
        pytest.skip(f"Pharos RPC feed temporarily unreachable: {data.get('error')}")
    assert data["pair"] == "BTC/USD"
    assert data["reference_price_usd"] > 10000.0
    assert data["chain_id"] == 1672
    assert data["cache_address"] == "0xd9F00c86ced2De92F6B7152b0492cb28edc4B5a8"
    assert data["updated_at_epoch"] > 0
    assert data["is_executable_pool"] is False


def test_amm_pool_bytecode_fail_closed():
    status = check_on_chain_amm_pool("BASE", "QUOTE")
    assert status["is_deployed"] is False
    assert status["status"] in ("UNAVAILABLE_NO_DEPLOYED_BYTECODE", "UNAVAILABLE_EMPTY_BYTECODE", "UNAVAILABLE_RPC_ERROR")
    assert status["chain_id"] == 688689


def test_unsupported_pair_raises_error():
    with pytest.raises(ValueError):
        scan_pair_venues("UNKNOWN/PAIR")


def test_custom_reserves_isolation():
    custom = {
        "test_venue_a": {"name": "Test A", "reserve_base": 50000.0, "reserve_quote": 100000.0},
        "test_venue_b": {"name": "Test B", "reserve_base": 50000.0, "reserve_quote": 110000.0}
    }
    res = scan_pair_venues("BTC/USD", custom_reserves=custom)
    assert res["is_test_fixture"] is True
    assert res["venues"]["test_venue_a"]["spot_price"] == 2.0
    assert res["venues"]["test_venue_b"]["spot_price"] == 2.2
