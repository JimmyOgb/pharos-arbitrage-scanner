"""
Unit Tests for Multi-Venue Discovery, On-Chain Feeds, and Bytecode Verification
"""

import pytest
from scanner.venues import (
    load_venues_config,
    get_supported_pairs,
    scan_pair_venues,
    query_chainlink_feed,
    check_on_chain_amm_pool,
    check_faroswap_mainnet_dex
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


def test_check_faroswap_mainnet_dex():
    data = check_faroswap_mainnet_dex()
    if data["status"] == "UNAVAILABLE_RPC_ERROR":
        pytest.skip(f"Pharos Mainnet RPC temporarily unreachable: {data.get('message')}")
    assert data["chain_id"] == 1672
    assert data["is_deployed"] is True
    assert data["status"] in ("DEPLOYED", "DEPLOYED_ZERO_LIQUIDITY")
    assert data["router_address"] == "0xd285e37678f07631f33eb99927eb3ff0591a12d7"
    assert data["factory_address"] == "0x18fab7d7027e9fb33fa90ca607439449209f7b09"
    assert data["deployed_pairs_count"] >= 100


def test_dodo_v2_venue_definition():
    config = load_venues_config()
    assert "dodo_v2_router" in config["venues"]
    dodo = config["venues"]["dodo_v2_router"]
    assert dodo["address"] == "0xA5cA5Fbe34e444F366B373170541ec6902b0F75c"
    assert dodo["approve_proxy"] == "0x2afc65f51b8afd1db9618643f89f0b135eaaeeaa"
    assert dodo["fee_rate_bps"] == 15
    assert dodo["type"] == "DEX_PMM_ROUTER"


def test_same_scan_dual_venues_present():
    custom = {
        "test_venue_a": {"name": "DODO V2 Model", "reserve_base": 100000.0, "reserve_quote": 250000.0, "fee_ratio": 0.0015},
        "test_venue_b": {"name": "FaroSwap V2 Model", "reserve_base": 100000.0, "reserve_quote": 252000.0, "fee_ratio": 0.003}
    }
    scan = scan_pair_venues("PROS/USD", custom_reserves=custom)
    assert scan["is_test_fixture"] is True
    assert "test_venue_a" in scan["venues"]
    assert "test_venue_b" in scan["venues"]
    assert scan["venues"]["test_venue_a"]["spot_price"] > 0
    assert scan["venues"]["test_venue_b"]["spot_price"] > 0


