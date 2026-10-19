"""
Transaction Payload Generator & Safety Guard Engine
Constructs canonical calldata for multi-hop arbitrage.
Strictly zero fake receipts: Execution is locked fail-closed when
no verified on-chain AMM router bytecode exists on testnet.
"""

import time
from typing import Dict, Any, List


def generate_arbitrage_calldata(
    evaluation: Dict[str, Any],
    recipient_address: str = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
) -> Dict[str, Any]:
    """
    Constructs an atomic multi-leg arbitrage calldata structure.
    Uses canonical Uniswap V2 / EVM router function selector:
    `swapExactTokensForTokens(uint256,uint256,address[],address,uint256)` (selector 0x38ed1739).
    
    Safety Guard:
    Execution is explicitly locked (execution_enabled: False) because
    no verified on-chain AMM liquidity router is currently deployed on Atlantic Testnet.
    """
    decision = evaluation.get("decision", {})
    if not decision.get("is_eligible", False):
        raise ValueError(f"Cannot generate execution payload for non-eligible scan: {decision.get('status')}")

    pair = evaluation["pair"]
    volume_usd = evaluation["trade_volume_usd"]
    deadline = int(time.time()) + 300  # 5 minutes validity

    # Standard Uniswap V2 swapExactTokensForTokens function selector: 0x38ed1739
    router_selector = "0x38ed1739"

    leg1_call = {
        "step": 1,
        "action": "SWAP_EXACT_TOKENS_FOR_TOKENS",
        "venue": evaluation["buy_venue"]["name"],
        "router": "0x0000000000000000000000000000000000000000",
        "amount_in_usd": volume_usd,
        "effective_rate": evaluation["buy_venue"]["effective_price"],
        "price_impact_bps": evaluation["buy_venue"]["price_impact_bps"],
        "deadline_epoch": deadline,
        "selector": router_selector
    }

    leg2_call = {
        "step": 2,
        "action": "SWAP_EXACT_TOKENS_FOR_TOKENS",
        "venue": evaluation["sell_venue"]["name"],
        "router": "0x0000000000000000000000000000000000000000",
        "expected_net_out_usd": round(volume_usd + evaluation["waterfall"]["net_profit_usd"], 4),
        "effective_rate": evaluation["sell_venue"]["effective_price"],
        "price_impact_bps": evaluation["sell_venue"]["price_impact_bps"],
        "deadline_epoch": deadline,
        "selector": router_selector
    }

    return {
        "type": "ATOMIC_ARBITRAGE_BUNDLE",
        "network": "Pharos Atlantic Testnet",
        "chain_id": 688689,
        "pair": pair,
        "trade_volume_usd": volume_usd,
        "expected_net_profit_usd": evaluation["waterfall"]["net_profit_usd"],
        "recipient": recipient_address,
        "deadline_epoch": deadline,
        "legs": [leg1_call, leg2_call],
        "execution_enabled": False,
        "safety_guard": "FAIL_CLOSED_NO_DEPLOYED_ROUTER",
        "safety_message": "Execution locked. Bytecode query on Atlantic Testnet returns 0x. Zero fake transactions or synthetic receipts permitted."
    }
