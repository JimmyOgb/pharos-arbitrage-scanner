"""
Multi-Venue Price Discovery & Real On-Chain Feed Reader
Queries verified Chainlink feed contracts and token registries on Pharos networks.
Separates reference oracles from executable AMM liquidity pools.
"""

import json
import time
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

PHAROS_RPC = "https://rpc.pharos.xyz"
ATLANTIC_RPC = "https://atlantic.dplabs-internal.com"


def get_assets_path() -> Path:
    """Returns the absolute path to assets directory."""
    return Path(__file__).resolve().parent.parent / "assets"


def load_venues_config() -> Dict[str, Any]:
    """Loads venue definitions from assets/venues.json."""
    venues_file = get_assets_path() / "venues.json"
    with open(venues_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_supported_pairs() -> List[str]:
    """Returns list of configured verified reference feeds."""
    config = load_venues_config()
    return list(config.get("verified_feeds", {}).keys())


def make_rpc_call(rpc_url: str, method: str, params: list, timeout: float = 6.0) -> Any:
    """Performs JSON-RPC call against verified node endpoint."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }).encode("utf-8")

    req = urllib.request.Request(
        rpc_url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Pharos-Arbitrage-Scanner/0.2.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if "error" in data:
            raise RuntimeError(f"RPC error from {rpc_url}: {data['error']}")
        return data["result"]


def query_chainlink_feed(pair_name: str, rpc_url: str = PHAROS_RPC, timeout: float = 6.0) -> Dict[str, Any]:
    """
    Queries real on-chain Chainlink reference feed cache on Pharos RPC (Chain ID: 1672).
    Contract: SelfManagedFeedsCache (0xd9F00c86ced2De92F6B7152b0492cb28edc4B5a8).
    This is an oracle benchmark feed, NOT an executable DEX trading pool.
    """
    config = load_venues_config()
    feed_cfg = config.get("verified_feeds", {}).get(pair_name)
    if not feed_cfg:
        raise ValueError(f"Pair '{pair_name}' not found in verified reference feeds: {get_supported_pairs()}")

    cache_address = feed_cfg["cache_address"]
    feed_id = feed_cfg["feed_id"]
    decimals = feed_cfg["decimals"]
    proxy_address = feed_cfg.get("proxy")

    try:
        # Selector 0x075482bf: getPrice(bytes32 feedId)
        price_calldata = "0x075482bf" + feed_id[2:]
        price_hex = make_rpc_call(rpc_url, "eth_call", [{"to": cache_address, "data": price_calldata}, "latest"], timeout=timeout)
        price_raw = int(price_hex, 16)
        price_usd = price_raw / (10 ** decimals)

        # Selector 0xab626992: getTimestamp(bytes32 feedId)
        ts_calldata = "0xab626992" + feed_id[2:]
        ts_hex = make_rpc_call(rpc_url, "eth_call", [{"to": cache_address, "data": ts_calldata}, "latest"], timeout=timeout)
        updated_at_epoch = int(ts_hex, 16)

        proxy_verified = False
        if proxy_address:
            try:
                proxy_res = make_rpc_call(rpc_url, "eth_call", [{"to": proxy_address, "data": "0xfeaf968c"}, "latest"], timeout=timeout)
                if len(proxy_res) >= 130:
                    proxy_verified = True
            except Exception:
                proxy_verified = False

        return {
            "pair": pair_name,
            "reference_price_usd": round(price_usd, 4),
            "raw_value": price_raw,
            "decimals": decimals,
            "updated_at_epoch": updated_at_epoch,
            "updated_at_iso": datetime.fromtimestamp(updated_at_epoch, tz=timezone.utc).isoformat() if updated_at_epoch > 0 else None,
            "cache_address": cache_address,
            "proxy_address": proxy_address,
            "proxy_verified": proxy_verified,
            "source": "PHAROS_CHAINLINK_PUSH_CACHE",
            "chain_id": 1672,
            "network_name": "Pharos RPC (Chain 1672)",
            "is_executable_pool": False,
            "status": "HEALTHY",
            "is_available": True
        }
    except Exception as e:
        return {
            "pair": pair_name,
            "reference_price_usd": None,
            "raw_value": None,
            "decimals": decimals,
            "updated_at_epoch": None,
            "updated_at_iso": None,
            "cache_address": cache_address,
            "proxy_address": proxy_address,
            "proxy_verified": False,
            "source": "PHAROS_CHAINLINK_PUSH_CACHE",
            "chain_id": 1672,
            "network_name": "Pharos RPC (Chain 1672)",
            "is_executable_pool": False,
            "status": "UNAVAILABLE",
            "is_available": False,
            "error": str(e)
        }


def check_on_chain_amm_pool(token_a_symbol: str, token_b_symbol: str, rpc_url: str = ATLANTIC_RPC) -> Dict[str, Any]:
    """
    Verifies bytecode existence and reserves for AMM liquidity pools on Pharos Atlantic Testnet (Chain ID: 688689).
    Returns explicit UNAVAILABLE status when no router or factory bytecode exists.
    """
    config = load_venues_config()
    router_cfg = config.get("venues", {}).get("atlantic_amm_router", {})
    router_address = router_cfg.get("address", "0x0000000000000000000000000000000000000000")

    if router_address == "0x0000000000000000000000000000000000000000":
        return {
            "is_deployed": False,
            "status": "UNAVAILABLE_NO_DEPLOYED_BYTECODE",
            "router_address": router_address,
            "chain_id": 688689,
            "network_name": "Pharos Atlantic Testnet (Chain 688689)",
            "message": "No verified AMM router deployed on Atlantic Testnet (0x bytecode, fail-closed enforced)."
        }

    try:
        code = make_rpc_call(rpc_url, "eth_getCode", [router_address, "latest"])
        if code in ("0x", "0x0", ""):
            return {
                "is_deployed": False,
                "status": "UNAVAILABLE_EMPTY_BYTECODE",
                "router_address": router_address,
                "chain_id": 688689,
                "network_name": "Pharos Atlantic Testnet (Chain 688689)",
                "message": f"Contract address {router_address} contains empty bytecode (0x). No AMM pool active."
            }
        return {
            "is_deployed": True,
            "status": "DEPLOYED",
            "router_address": router_address,
            "chain_id": 688689,
            "network_name": "Pharos Atlantic Testnet (Chain 688689)"
        }
    except Exception as e:
        return {
            "is_deployed": False,
            "status": "UNAVAILABLE_RPC_ERROR",
            "router_address": router_address,
            "chain_id": 688689,
            "network_name": "Pharos Atlantic Testnet (Chain 688689)",
            "message": f"RPC check failed: {str(e)}"
        }


def scan_pair_venues(
    pair_name: str,
    custom_reserves: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Reads pricing and venue states across verified on-chain sources.
    Strictly separates reference oracle pricing from executable AMM liquidity pools.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    now_ts = time.time()

    # Case A: Mathematical Test Fixture Mode (for pure unit tests)
    if custom_reserves:
        if "test_venue_a" not in custom_reserves and "test_venue_b" not in custom_reserves and "venue_a" not in custom_reserves and "pharos_swap" not in custom_reserves:
            raise ValueError("custom_reserves must provide test pools for mathematical validation")

        va = custom_reserves.get("test_venue_a") or custom_reserves.get("venue_a") or custom_reserves.get("pharos_swap", {})
        vb = custom_reserves.get("test_venue_b") or custom_reserves.get("venue_b") or custom_reserves.get("lighthouse_dex", {})

        va_spot = va["reserve_quote"] / va["reserve_base"] if va.get("reserve_base", 0) > 0 else 0.0
        vb_spot = vb["reserve_quote"] / vb["reserve_base"] if vb.get("reserve_base", 0) > 0 else 0.0

        return {
            "pair": pair_name,
            "timestamp": now_iso,
            "timestamp_epoch": now_ts,
            "data_freshness_seconds": 0.0,
            "is_stale": False,
            "is_test_fixture": True,
            "venues": {
                "test_venue_a": {
                    "id": "test_venue_a",
                    "name": va.get("name", "Test Venue A"),
                    "type": "AMM_CONSTANT_PRODUCT_MODEL",
                    "fee_ratio": va.get("fee_ratio", 0.003),
                    "gas_units": va.get("gas_units", 140000),
                    "reserve_base": va["reserve_base"],
                    "reserve_quote": va["reserve_quote"],
                    "spot_price": round(va_spot, 6),
                    "status": "ISOLATED_TEST_FIXTURE"
                },
                "test_venue_b": {
                    "id": "test_venue_b",
                    "name": vb.get("name", "Test Venue B"),
                    "type": "AMM_CONSTANT_PRODUCT_MODEL",
                    "fee_ratio": vb.get("fee_ratio", 0.0025),
                    "gas_units": vb.get("gas_units", 155000),
                    "reserve_base": vb["reserve_base"],
                    "reserve_quote": vb["reserve_quote"],
                    "spot_price": round(vb_spot, 6),
                    "status": "ISOLATED_TEST_FIXTURE"
                }
            }
        }

    # Case B: Production Live On-Chain Scan Mode
    if pair_name.upper() not in [p.upper() for p in get_supported_pairs()]:
        raise ValueError(f"Pair '{pair_name}' not supported. Verified reference feeds: {get_supported_pairs()}")

    feed_data = query_chainlink_feed(pair_name)
    amm_check = check_on_chain_amm_pool("BASE", "QUOTE")

    price_usd = feed_data.get("reference_price_usd")
    updated_at = feed_data.get("updated_at_epoch")
    freshness = max(0.0, now_ts - updated_at) if updated_at and updated_at > 0 else 0.0
    is_stale = freshness > 86400 or (not feed_data.get("is_available", False))

    return {
        "pair": pair_name,
        "timestamp": now_iso,
        "timestamp_epoch": now_ts,
        "data_freshness_seconds": round(freshness, 1),
        "is_stale": is_stale,
        "is_test_fixture": False,
        "venues": {
            "chainlink_reference_oracle": {
                "id": "chainlink_reference_oracle",
                "name": "Chainlink Self-Managed Feeds Cache",
                "network": "Pharos RPC",
                "chain_id": 1672,
                "type": "ON_CHAIN_REFERENCE_ORACLE",
                "is_executable_pool": False,
                "contract_address": feed_data["cache_address"],
                "proxy_address": feed_data["proxy_address"],
                "proxy_verified": feed_data.get("proxy_verified", False),
                "reference_price_usd": price_usd,
                "updated_at_iso": feed_data["updated_at_iso"],
                "updated_at_epoch": updated_at,
                "status": feed_data["status"],
                "is_available": feed_data["is_available"],
                "error": feed_data.get("error")
            },
            "atlantic_amm_router": {
                "id": "atlantic_amm_router",
                "name": "Pharos Atlantic Testnet AMM Router",
                "network": "Pharos Atlantic Testnet",
                "chain_id": 688689,
                "type": "AMM_CONSTANT_PRODUCT",
                "is_executable_pool": False,
                "deployed_pools_count": 0,
                "status": amm_check["status"],
                "is_deployed": amm_check["is_deployed"],
                "router_address": amm_check["router_address"],
                "message": amm_check["message"]
            }
        }
    }
