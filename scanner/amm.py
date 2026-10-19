"""
Constant-Product AMM Mathematical Engine (x * y = k)
Implements exact reserve-based output estimation, spot pricing, and price impact calculation.
"""

from typing import Dict, Any, Tuple


class AMMMathError(ValueError):
    """Raised when AMM calculations encounter invalid reserves, zero liquidity, or invalid inputs."""
    pass


def calculate_spot_price(reserve_in: float, reserve_out: float) -> float:
    """
    Calculates the unperturbed spot price of token_in priced in token_out.
    Spot Price = reserve_out / reserve_in
    """
    if reserve_in <= 0 or reserve_out <= 0:
        raise AMMMathError(f"Reserves must be strictly positive: in={reserve_in}, out={reserve_out}")
    return reserve_out / reserve_in


def calculate_swap_output(
    amount_in: float,
    reserve_in: float,
    reserve_out: float,
    fee_ratio: float = 0.003
) -> float:
    """
    Calculates exact token output for a constant-product AMM swap with LP fee deduction.
    Formula:
        amount_in_with_fee = amount_in * (1 - fee_ratio)
        amount_out = (reserve_out * amount_in_with_fee) / (reserve_in + amount_in_with_fee)
    """
    if amount_in <= 0:
        raise AMMMathError(f"amount_in must be positive, got {amount_in}")
    if reserve_in <= 0 or reserve_out <= 0:
        raise AMMMathError(f"Pool reserves must be positive: in={reserve_in}, out={reserve_out}")
    if fee_ratio < 0 or fee_ratio >= 1.0:
        raise AMMMathError(f"fee_ratio must be in [0, 1), got {fee_ratio}")

    amount_in_with_fee = amount_in * (1.0 - fee_ratio)
    numerator = reserve_out * amount_in_with_fee
    denominator = reserve_in + amount_in_with_fee

    if denominator <= 0:
        raise AMMMathError("Denominator non-positive during swap output calculation")

    amount_out = numerator / denominator

    # Safety check: Cannot extract more than available reserve_out
    if amount_out >= reserve_out:
        raise AMMMathError(f"Requested output {amount_out} exceeds total pool reserve {reserve_out}")

    return amount_out


def calculate_effective_price(amount_in: float, amount_out: float) -> float:
    """
    Calculates the actual average execution price:
    Effective Price = amount_out / amount_in
    """
    if amount_in <= 0 or amount_out <= 0:
        raise AMMMathError(f"Amounts must be positive: in={amount_in}, out={amount_out}")
    return amount_out / amount_in


def calculate_price_impact(
    amount_in: float,
    reserve_in: float,
    reserve_out: float,
    fee_ratio: float = 0.003
) -> Dict[str, Any]:
    """
    Distinguishes Price Impact (inherent AMM curve slippage) from user-configured slippage tolerance.
    
    Returns:
        - spot_price: Unperturbed marginal rate before trade
        - amount_out: Actual token received
        - effective_price: Realized average execution rate
        - price_impact_ratio: Fractional deviation from spot price
        - price_impact_bps: Price impact in basis points (1% = 100 bps)
        - slippage_cost_usd: Estimated value loss due strictly to liquidity curve curvature
    """
    spot_price = calculate_spot_price(reserve_in, reserve_out)
    amount_out = calculate_swap_output(amount_in, reserve_in, reserve_out, fee_ratio)
    effective_price = calculate_effective_price(amount_in, amount_out)

    # Output if there were zero liquidity friction (infinite depth at spot price minus fee)
    ideal_output_with_fee = amount_in * spot_price * (1.0 - fee_ratio)
    
    # Deviation between ideal output and actual AMM curve output
    slippage_loss_tokens = max(0.0, ideal_output_with_fee - amount_out)
    
    price_impact_ratio = max(0.0, (ideal_output_with_fee - amount_out) / ideal_output_with_fee) if ideal_output_with_fee > 0 else 0.0
    price_impact_bps = round(price_impact_ratio * 10000.0, 2)

    return {
        "spot_price": round(spot_price, 6),
        "amount_in": amount_in,
        "amount_out": round(amount_out, 6),
        "effective_price": round(effective_price, 6),
        "price_impact_ratio": round(price_impact_ratio, 6),
        "price_impact_bps": price_impact_bps,
        "slippage_loss_tokens": round(slippage_loss_tokens, 6)
    }
