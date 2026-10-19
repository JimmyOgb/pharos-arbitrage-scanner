"""
Transaction Payload Generator & Safety Guard Engine
Constructs canonical calldata for multi-hop arbitrage.
Strictly fail-closed: Live execution is permanently locked
because no verified on-chain AMM router bytecode exists on testnet.
"""

import time
from typing import Dict, Any


def generate_arbitrage_calldata(
    evaluation: Dict[str, Any],
    recipient_address: str = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
) -> Dict[str, Any]:
    """
    Constructs an atomic multi-leg arbitrage calldata structure for testing.
    Uses canonical Uniswap V2 / EVM router function selector:
    `swapExactTokensForTokens(uint256,uint256,address[],address,uint256)` (selector 0x38ed1739).
    
    Safety Guarantee:
    Execution is strictly locked (execution_enabled: False).
    Live arbitrage is unavailable because 0 AMM router contracts are deployed on Atlantic Testnet.
    Zero synthetic transactions or fabricated receipts are emitted.
    """
    decision = evaluation.get("decision", {})
    fixture_passed = decision.get("fixture_threshold_passed", False)
    
    # In production, decision is always LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY
    if not fixture_passed and not decision.get("is_eligible", False):
        raise ValueError(
            f"Cannot generate execution payload: {decision.get('status')}. "
            f"Live arbitrage is unavailable because no verified AMM liquidity pools exist on Atlantic Testnet."
        )

    pair = evaluation.get("pair", "TEST/PAIR")
    volume_usd = evaluation.get("trade_volume_usd", 2500.0)
    deadline = int(time.time()) + 300  # 5 minutes validity
    waterfall = evaluation.get("waterfall") or {}

    router_selector = "0x38ed1739"

    leg1_call = {
        "step": 1,
        "action": "SWAP_EXACT_TOKENS_FOR_TOKENS",
        "venue": evaluation.get("buy_venue", {}).get("name", "Test Venue A"),
        "router": "0x0000000000000000000000000000000000000000",
        "amount_in_usd": volume_usd,
        "deadline_epoch": deadline,
        "selector": router_selector
    }

    leg2_call = {
        "step": 2,
        "action": "SWAP_EXACT_TOKENS_FOR_TOKENS",
        "venue": evaluation.get("sell_venue", {}).get("name", "Test Venue B"),
        "router": "0x0000000000000000000000000000000000000000",
        "expected_net_out_usd": round(volume_usd + waterfall.get("net_profit_usd", 0.0), 4),
        "deadline_epoch": deadline,
        "selector": router_selector
    }

    return {
        "type": "ATOMIC_ARBITRAGE_BUNDLE",
        "network": "Pharos Atlantic Testnet (Chain ID 688689)",
        "chain_id": 688689,
        "pair": pair,
        "trade_volume_usd": volume_usd,
        "expected_net_profit_usd": waterfall.get("net_profit_usd", 0.0),
        "recipient": recipient_address,
        "deadline_epoch": deadline,
        "legs": [leg1_call, leg2_call],
        "execution_enabled": False,
        "is_live_transaction": False,
        "safety_guard": "LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY",
        "safety_message": "Execution locked fail-closed. Atlantic Testnet has 0 deployed AMM liquidity pools (0x bytecode). Zero fake transactions or synthetic receipts permitted."
    }
