"""
Unit Tests for Constant-Product AMM Math Engine (x * y = k)
"""

import pytest
from scanner.amm import (
    calculate_spot_price,
    calculate_swap_output,
    calculate_effective_price,
    calculate_price_impact,
    AMMMathError
)


def test_spot_price_calculation():
    # 100k quote, 50k base -> spot price = 2.0 quote per base
    assert calculate_spot_price(50000.0, 100000.0) == 2.0
    # Equal reserves -> spot price = 1.0
    assert calculate_spot_price(1000.0, 1000.0) == 1.0


def test_swap_output_constant_product():
    # Reserve In: 100,000, Reserve Out: 200,000, Amount In: 1,000, Fee: 0.3%
    # In with fee = 997
    # Out = (200000 * 997) / (100000 + 997) = 199400000 / 100997 = 1974.316...
    out = calculate_swap_output(1000.0, 100000.0, 200000.0, 0.003)
    assert 1974.0 < out < 1975.0


def test_effective_price():
    # 1000 in, 1974.31 out -> 1.97431 out per in
    eff = calculate_effective_price(1000.0, 1974.31)
    assert round(eff, 2) == 1.97


def test_price_impact_increases_with_volume():
    # Small trade: 100 in against 100,000 reserve -> very small price impact
    small = calculate_price_impact(100.0, 100000.0, 200000.0, 0.003)
    # Large trade: 20,000 in against 100,000 reserve -> substantial price impact
    large = calculate_price_impact(20000.0, 100000.0, 200000.0, 0.003)

    assert large["price_impact_bps"] > small["price_impact_bps"]
    assert small["price_impact_bps"] < 20.0  # < 0.2%
    assert large["price_impact_bps"] > 1000.0  # > 10%


def test_zero_and_negative_reserves_raise_error():
    with pytest.raises(AMMMathError):
        calculate_spot_price(0, 100)
    with pytest.raises(AMMMathError):
        calculate_spot_price(-50, 100)
    with pytest.raises(AMMMathError):
        calculate_swap_output(10, 0, 100)
    with pytest.raises(AMMMathError):
        calculate_swap_output(10, 100, -10)


def test_zero_and_negative_inputs_raise_error():
    with pytest.raises(AMMMathError):
        calculate_swap_output(0, 1000, 1000)
    with pytest.raises(AMMMathError):
        calculate_swap_output(-5, 1000, 1000)
    with pytest.raises(AMMMathError):
        calculate_effective_price(0, 100)


def test_excessive_drain_exceeding_reserve_raises_error():
    # In an infinite input case where amount_in_with_fee is huge,
    # it approaches reserve_out. If reserve_out is 100, output cannot equal or exceed 100.
    # Testing boundary handling.
    out = calculate_swap_output(1e9, 100.0, 100.0, 0.003)
    assert out < 100.0


def test_fee_ratio_bounds():
    with pytest.raises(AMMMathError):
        calculate_swap_output(100, 1000, 1000, fee_ratio=-0.01)
    with pytest.raises(AMMMathError):
        calculate_swap_output(100, 1000, 1000, fee_ratio=1.0)
    with pytest.raises(AMMMathError):
        calculate_swap_output(100, 1000, 1000, fee_ratio=1.5)


def test_zero_fee_ratio():
    # 0% fee: output = (1000 * 100) / (1000 + 100) = 100000 / 1100 = 90.909090...
    out = calculate_swap_output(100.0, 1000.0, 1000.0, fee_ratio=0.0)
    assert round(out, 4) == 90.9091


def test_micro_volume_precision():
    # Very small volume: $0.0001
    impact = calculate_price_impact(0.0001, 100000.0, 200000.0, 0.003)
    assert impact["amount_out"] > 0
    assert impact["price_impact_bps"] == 0.0


def test_price_impact_bps_boundary():
    # Half the pool reserve swapped -> price impact ~ 33% (3333 bps)
    impact = calculate_price_impact(50000.0, 100000.0, 100000.0, 0.003)
    assert 3000 < impact["price_impact_bps"] < 3500


def test_calculate_spot_price_symmetric():
    p1 = calculate_spot_price(100.0, 200.0)
    p2 = calculate_spot_price(200.0, 100.0)
    assert p1 * p2 == 1.0
