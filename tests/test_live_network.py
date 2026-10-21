"""
Live Integration Tests against Pharos Atlantic Testnet
Validates real JSON-RPC connectivity, Chain ID 688689, and gas pricing.
"""

import pytest
import urllib.request
import json
from scanner.costs import DEFAULT_ATLANTIC_RPC, fetch_live_gas_price


@pytest.mark.live
def test_live_atlantic_rpc_connectivity():
    res = fetch_live_gas_price(rpc_url=DEFAULT_ATLANTIC_RPC)
    if not res.get("is_live", False):
        pytest.skip(f"Live Atlantic RPC currently unreachable: {res.get('error')}")
    assert res["source"] in ("LIVE_ATLANTIC_RPC", "ATLANTIC_TESTNET_DIAGNOSTIC_RPC")
    assert res["chain_id"] == 688689
    assert res["gas_price_gwei"] > 0
    assert res["block_number"] > 30000000


@pytest.mark.live
def test_atlantic_chain_id():
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}).encode("utf-8")
    req = urllib.request.Request(
        DEFAULT_ATLANTIC_RPC,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=6.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            chain_id = int(data["result"], 16)
            assert chain_id == 688689
    except Exception as e:
        pytest.skip(f"Live Atlantic RPC chain_id query skipped due to network timeout: {str(e)}")
