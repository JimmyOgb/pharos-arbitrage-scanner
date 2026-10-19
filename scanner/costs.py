"""
Cost Estimation & Profit Waterfall Engine
Calculates LP swap fees, queries live network gas from Pharos Atlantic Testnet,
and evaluates transparent waterfall friction deductions.
"""

import urllib.request
import json
from typing import Dict, Any, Optional

DEFAULT_ATLANTIC_RPC = "https://atlantic.dplabs-internal.com"
FALLBACK_GAS_PRICE_GWEI = 10.0
DEFAULT_PHRS_PRICE_USD = 2.50


def fetch_live_gas_price(
    rpc_url: str = DEFAULT_ATLANTIC_RPC,
    timeout: float = 3.0
) -> Dict[str, Any]:
    """
    Fetches real live gas price and latest block height directly from Pharos Atlantic Testnet.
    Falls back gracefully to calibrated testnet constants if offline.
    """
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_gasPrice",
        "params": []
    }).encode("utf-8")

    block_payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "eth_blockNumber",
        "params": []
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            rpc_url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "Pharos-Arbitrage-Scanner/0.1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            gas_wei = int(data["result"], 16)
            gas_gwei = gas_wei / 1e9

        block_req = urllib.request.Request(
            rpc_url,
            data=block_payload,
            headers={"Content-Type": "application/json", "User-Agent": "Pharos-Arbitrage-Scanner/0.1.0"}
        )
        with urllib.request.urlopen(block_req, timeout=timeout) as resp:
            block_data = json.loads(resp.read().decode("utf-8"))
            block_number = int(block_data["result"], 16)

        return {
            "source": "LIVE_ATLANTIC_RPC",
            "rpc_url": rpc_url,
            "gas_price_wei": gas_wei,
            "gas_price_gwei": round(gas_gwei, 4),
            "block_number": block_number,
            "is_live": True
        }
    except Exception as e:
        return {
            "source": "CALIBRATED_FALLBACK",
            "rpc_url": rpc_url,
            "gas_price_wei": int(FALLBACK_GAS_PRICE_GWEI * 1e9),
            "gas_price_gwei": FALLBACK_GAS_PRICE_GWEI,
            "block_number": 31608000,
            "is_live": False,
            "fallback_notice": f"RPC unreachable ({str(e)}), used verified testnet 10.0 Gwei constant"
        }


def calculate_gas_cost_usd(
    gas_units: int,
    gas_price_gwei: float,
    phrs_price_usd: float = DEFAULT_PHRS_PRICE_USD
) -> Dict[str, Any]:
    """
    Computes total gas cost in native PHRS and USD.
    Formula:
        Gas Cost (PHRS) = gas_units * (gas_price_gwei * 1e-9)
        Gas Cost (USD)  = Gas Cost (PHRS) * phrs_price_usd
    """
    if gas_units < 0:
        raise ValueError(f"gas_units cannot be negative: {gas_units}")
    if gas_price_gwei < 0:
        raise ValueError(f"gas_price_gwei cannot be negative: {gas_price_gwei}")

    gas_cost_phrs = gas_units * (gas_price_gwei * 1e-9)
    gas_cost_usd = gas_cost_phrs * phrs_price_usd

    return {
        "gas_units": gas_units,
        "gas_price_gwei": gas_price_gwei,
        "phrs_price_usd": phrs_price_usd,
        "gas_cost_phrs": round(gas_cost_phrs, 8),
        "gas_cost_usd": round(gas_cost_usd, 6)
    }


def compute_net_waterfall(
    trade_volume_usd: float,
    gross_spread_usd: float,
    gross_spread_pct: float,
    buy_fee_usd: float,
    sell_fee_usd: float,
    buy_slippage_usd: float,
    sell_slippage_usd: float,
    gas_cost_usd: float,
    gas_units_total: int
) -> Dict[str, Any]:
    """
    Builds the transparent waterfall deduction:
    Gross Spread
      - Buy Fee
      - Sell Fee
      - Buy Slippage Impact
      - Sell Slippage Impact
      - Network Gas
    = Net Profit
    """
    if trade_volume_usd <= 0:
        raise ValueError(f"trade_volume_usd must be positive, got {trade_volume_usd}")

    total_fees = buy_fee_usd + sell_fee_usd
    total_slippage = buy_slippage_usd + sell_slippage_usd
    total_friction = total_fees + total_slippage + gas_cost_usd
    net_profit_usd = gross_spread_usd - total_friction
    net_profit_pct = (net_profit_usd / trade_volume_usd) * 100.0

    return {
        "trade_volume_usd": round(trade_volume_usd, 2),
        "gross_spread_usd": round(gross_spread_usd, 4),
        "gross_spread_pct": round(gross_spread_pct, 4),
        "buy_fee_usd": round(buy_fee_usd, 4),
        "sell_fee_usd": round(sell_fee_usd, 4),
        "total_fees_usd": round(total_fees, 4),
        "buy_slippage_usd": round(buy_slippage_usd, 4),
        "sell_slippage_usd": round(sell_slippage_usd, 4),
        "total_slippage_usd": round(total_slippage, 4),
        "gas_units_total": gas_units_total,
        "gas_cost_usd": round(gas_cost_usd, 6),
        "total_friction_usd": round(total_friction, 4),
        "net_profit_usd": round(net_profit_usd, 4),
        "net_profit_pct": round(net_profit_pct, 4),
        "is_profitable": net_profit_usd > 0
    }
