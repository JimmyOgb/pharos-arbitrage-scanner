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
    assert "gas_price_gwei" in data
    assert data["gas_price_gwei"] > 0


def test_cli_scan_json():
    cmd = [
        sys.executable, str(ROOT_DIR / "scripts" / "scanner.py"),
        "scan", "--pair", "PHRS/USDC", "--volume", "2000", "--json"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["pair"] == "PHRS/USDC"
    assert "waterfall" in data[0]
    assert "decision" in data[0]


def test_cli_demo_suite():
    cmd = [sys.executable, str(ROOT_DIR / "scripts" / "scanner.py"), "demo", "--json"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert isinstance(data, list)
    assert len(data) == 4
    # All 4 scenarios present
    sc_ids = [d["scenario_id"] for d in data]
    assert "profitable_arb" in sc_ids
    assert "slippage_eroded" in sc_ids
    assert "gas_eroded" in sc_ids
    assert "inverted_spread" in sc_ids
