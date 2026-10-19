"""
Unit Tests for Multi-Venue Discovery & Pool Reading
"""

import pytest
from scanner.venues import (
    load_venues_config,
    get_supported_pairs,
    scan_pair_venues
)


def test_load_venues_config():
    config = load_venues_config()
    assert "venues" in config
    assert "pharos_swap" in config["venues"]
    assert "lighthouse_dex" in config["venues"]
    assert "pyth_oracle" in config["venues"]


def test_get_supported_pairs():
    pairs = get_supported_pairs()
    assert "PHRS/USDC" in pairs
    assert "WPHRS/USDT" in pairs
    assert "USDC/USDT" in pairs


def test_scan_pair_venues_multi_source():
    # Criterion 01: Reads prices from at least 2 sources in the same scan
    res = scan_pair_venues("PHRS/USDC")
    assert res["pair"] == "PHRS/USDC"
    assert "pharos_swap" in res["venues"]
    assert "lighthouse_dex" in res["venues"]
    assert "pyth_oracle" in res["venues"]

    ps_spot = res["venues"]["pharos_swap"]["spot_price"]
    lh_spot = res["venues"]["lighthouse_dex"]["spot_price"]
    pyth_price = res["venues"]["pyth_oracle"]["benchmark_price"]

    assert ps_spot > 0
    assert lh_spot > 0
    assert pyth_price > 0
    assert res["is_stale"] is False


def test_unsupported_pair_raises_error():
    with pytest.raises(ValueError):
        scan_pair_venues("UNKNOWN/TOKEN")


def test_custom_reserves_override():
    custom = {
        "pharos_swap": {"reserve_base": 50000.0, "reserve_quote": 100000.0},
        "lighthouse_dex": {"reserve_base": 50000.0, "reserve_quote": 110000.0}
    }
    res = scan_pair_venues("PHRS/USDC", custom_reserves=custom)
    assert res["venues"]["pharos_swap"]["spot_price"] == 2.0
    assert res["venues"]["lighthouse_dex"]["spot_price"] == 2.2
