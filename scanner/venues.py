"""
Multi-Venue Price Discovery & Pool State Reader
Retrieves reserves, spot rates, and timestamps across multiple liquidity venues.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


def get_assets_path() -> Path:
    """Returns the absolute path to assets directory."""
    return Path(__file__).resolve().parent.parent / "assets"


def load_venues_config() -> Dict[str, Any]:
    """Loads venue definitions from assets/venues.json."""
    venues_file = get_assets_path() / "venues.json"
    with open(venues_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_supported_pairs() -> List[str]:
    """Returns list of configured trading pairs."""
    config = load_venues_config()
    return [p["pair"] for p in config.get("default_pairs", [])]


def scan_pair_venues(
    pair_name: str,
    custom_reserves: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Simultaneously reads pricing and reserve state across dual AMM venues
    and benchmark oracle for a specific trading pair.
    """
    config = load_venues_config()
    pair_data = None
    for p in config.get("default_pairs", []):
        if p["pair"].upper() == pair_name.upper():
            pair_data = p
            break

    if not pair_data:
        raise ValueError(f"Pair '{pair_name}' not found in registered venues. Supported: {get_supported_pairs()}")

    now_iso = datetime.now(timezone.utc).isoformat()
    now_ts = time.time()

    pharos_swap_cfg = config["venues"]["pharos_swap"]
    lighthouse_cfg = config["venues"]["lighthouse_dex"]
    pyth_cfg = config["venues"]["pyth_oracle"]

    ps_pool = pair_data["pharos_swap"]
    lh_pool = pair_data["lighthouse_dex"]

    if custom_reserves:
        if "pharos_swap" in custom_reserves:
            ps_pool = custom_reserves["pharos_swap"]
        if "lighthouse_dex" in custom_reserves:
            lh_pool = custom_reserves["lighthouse_dex"]

    ps_spot = ps_pool["reserve_quote"] / ps_pool["reserve_base"]
    lh_spot = lh_pool["reserve_quote"] / lh_pool["reserve_base"]
    oracle_price = pair_data.get("oracle_price", (ps_spot + lh_spot) / 2.0)

    return {
        "pair": pair_name,
        "base_token": pair_data["base_token"],
        "quote_token": pair_data["quote_token"],
        "timestamp": now_iso,
        "timestamp_epoch": now_ts,
        "data_freshness_seconds": 0.1,
        "is_stale": False,
        "venues": {
            "pharos_swap": {
                "id": "pharos_swap",
                "name": pharos_swap_cfg["name"],
                "type": pharos_swap_cfg["type"],
                "fee_bps": pharos_swap_cfg["fee_bps"],
                "fee_ratio": pharos_swap_cfg["fee_ratio"],
                "gas_units": pharos_swap_cfg["gas_units_estimate"],
                "reserve_base": ps_pool["reserve_base"],
                "reserve_quote": ps_pool["reserve_quote"],
                "spot_price": round(ps_spot, 6),
                "status": pharos_swap_cfg["status"]
            },
            "lighthouse_dex": {
                "id": "lighthouse_dex",
                "name": lighthouse_cfg["name"],
                "type": lighthouse_cfg["type"],
                "fee_bps": lighthouse_cfg["fee_bps"],
                "fee_ratio": lighthouse_cfg["fee_ratio"],
                "gas_units": lighthouse_cfg["gas_units_estimate"],
                "reserve_base": lh_pool["reserve_base"],
                "reserve_quote": lh_pool["reserve_quote"],
                "spot_price": round(lh_spot, 6),
                "status": lighthouse_cfg["status"]
            },
            "pyth_oracle": {
                "id": "pyth_oracle",
                "name": pyth_cfg["name"],
                "type": pyth_cfg["type"],
                "benchmark_price": round(oracle_price, 6),
                "status": pyth_cfg["status"]
            }
        }
    }
