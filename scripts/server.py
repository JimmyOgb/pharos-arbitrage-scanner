#!/usr/bin/env python3
"""
Lightweight Local REST Server & Static Asset Server for Web Visualizer
Provides JSON endpoints for live Atlantic gas, verified Chainlink feeds, and AMM mathematics.
Zero simulated execution receipts. Strictly real data and transparent mathematical models.
"""

import http.server
import json
import socketserver
import sys
import urllib.parse
from pathlib import Path
from typing import Any

# Add root directory to path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from scanner.evaluator import evaluate_arbitrage
from scanner.venues import get_supported_pairs, query_chainlink_feed, check_on_chain_amm_pool, check_faroswap_mainnet_dex
from scanner.costs import fetch_live_gas_price
from scanner.payload import generate_arbitrage_calldata

PORT = 8088
WEB_DIR = root_dir / "web"


class ScannerHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # API: /api/live-gas
        if path == "/api/live-gas":
            gas_info = fetch_live_gas_price()
            self._send_json(gas_info)
            return

        # API: /api/feeds
        if path == "/api/feeds":
            feeds = {}
            for pair in get_supported_pairs():
                try:
                    feeds[pair] = query_chainlink_feed(pair)
                except Exception as e:
                    feeds[pair] = {"error": str(e)}
            self._send_json({"feeds": feeds})
            return

        # API: /api/amm-status
        if path == "/api/amm-status":
            status = check_on_chain_amm_pool("BASE", "QUOTE")
            self._send_json(status)
            return

        # API: /api/faroswap-status
        if path == "/api/faroswap-status":
            status = check_faroswap_mainnet_dex()
            self._send_json(status)
            return

        # API: /api/pairs
        if path == "/api/pairs":
            pairs = get_supported_pairs()
            self._send_json({"pairs": pairs})
            return

        # API: /api/scan
        if path == "/api/scan":
            volume = float(query.get("volume", [5000.0])[0])
            min_profit = float(query.get("min_profit", [5.0])[0])
            max_slippage = int(query.get("max_slippage", [150])[0])
            pair = query.get("pair", [None])[0]

            pairs_to_scan = [pair] if pair else get_supported_pairs()
            gas_info = fetch_live_gas_price()

            results = []
            for p in pairs_to_scan:
                try:
                    res = evaluate_arbitrage(
                        pair_name=p,
                        trade_volume_usd=volume,
                        min_net_profit_usd=min_profit,
                        max_slippage_bps=max_slippage,
                        live_gas_info=gas_info
                    )
                    results.append(res)
                except Exception as e:
                    results.append({"pair": p, "error": str(e)})

            self._send_json({"results": results, "gas_info": gas_info})
            return

        # Fallback to static files in web/
        super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)

        # Mathematical Model Evaluation Sandbox
        if parsed_url.path == "/api/math-evaluate":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                body = json.loads(post_data.decode("utf-8"))
                res = evaluate_arbitrage(
                    pair_name=body.get("pair", "MATH/TEST"),
                    trade_volume_usd=float(body.get("volume", 2500.0)),
                    min_net_profit_usd=float(body.get("min_profit", 5.0)),
                    max_slippage_bps=int(body.get("max_slippage", 150)),
                    custom_reserves=body.get("custom_reserves")
                )
                calldata = None
                if res["decision"]["is_eligible"]:
                    calldata = generate_arbitrage_calldata(res)
                self._send_json({"evaluation": res, "prepared_calldata": calldata})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        self.send_error(404, "Endpoint not found")

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)


def run_server(port: int = PORT):
    handler = ScannerHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"\n=======================================================")
        print(f"  Pharos Arbitrage Scanner Server Active (Zero Simulation)")
        print(f"  URL: http://localhost:{port}")
        print(f"  API: http://localhost:{port}/api/scan")
        print(f"  Live Feeds: http://localhost:{port}/api/feeds")
        print(f"  Serving Static Assets from: {WEB_DIR}")
        print(f"=======================================================\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port)
