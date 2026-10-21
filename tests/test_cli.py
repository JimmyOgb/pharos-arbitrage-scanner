"""
Unit Tests for Command Line Interface (CLI) Execution
"""

import subprocess
import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_cli_live_gas():
    cmd = [sys.executable, str(ROOT_DIR / "scripts" / "scanner.py"), "live-gas", "--json"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert "status" in data
    if data.get("is_live"):
        assert data["gas_price_gwei"] > 0
    else:
        assert data["status"] == "UNAVAILABLE"


def test_cli_scan_json():
    cmd = [
        sys.executable, str(ROOT_DIR / "scripts" / "scanner.py"),
        "scan", "--pair", "BTC/USD", "--volume", "2000", "--json"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["pair"] == "BTC/USD"
    assert data[0]["data_mode"] == "PRODUCTION_LIVE_AUDIT"
    assert data[0]["decision"]["is_eligible"] is False
    assert data[0]["decision"]["status"] in ("CROSS_VENUE_COMPARISON_BLOCKED", "LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY")


def test_cli_demo_suite():
    cmd = [sys.executable, str(ROOT_DIR / "scripts" / "scanner.py"), "demo", "--json"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["production_status"] == "LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY"
    assert "verified_reference_oracle_feeds" in data
    assert "atlantic_gas" in data
    assert "amm_deployment_status" in data
    assert "isolated_unit_test_math_validation" in data

    # Verify feeds are populated
    feeds = data["verified_reference_oracle_feeds"]
    assert "BTC/USD" in feeds

    # Verify fail-closed AMM status
    assert data["amm_deployment_status"]["is_deployed"] is False
    assert data["amm_deployment_status"]["status"] in ("UNAVAILABLE_NO_DEPLOYED_BYTECODE", "UNAVAILABLE_RPC_ERROR")

    # Verify mathematical models tested
    models = data["isolated_unit_test_math_validation"]
    assert len(models) == 3
