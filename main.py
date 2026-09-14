"""
Root entrypoint for Railway, Render, Fly.io, and container deployments.
Launches the MoSPI National Airfare Price Index Server & REST API.
"""
import os
import sys

# Ensure repository root and live_fetcher directory are in sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FETCHER_DIR = os.path.join(ROOT_DIR, "airfare_index", "live_fetcher")

for p in (FETCHER_DIR, ROOT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from airfare_index.live_fetcher.server import run_server

if __name__ == "__main__":
    run_server()
