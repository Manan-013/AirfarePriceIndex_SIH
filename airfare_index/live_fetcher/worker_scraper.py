"""
worker_scraper.py - Decoupled Headless Background Ingestion Worker
Integrated for SIH 2026 (Problem Statement SIH26056).

Features:
1. Decoupled Architecture: Runs independently of FastAPI/server.py web processes,
   preventing long-running Playwright browser tasks from starving HTTP handlers.
2. Low-Memory Footprint (<120MB RAM):
   - Launches Chromium with low-memory sandbox flags
   - Intercepts and drops images, video, fonts, and heavy tracking scripts
   - Explicit garbage collection and browser context recycling
3. Ethical Compliance: Checks robots.txt via RobotGuard and enforces domain rate limits.
4. Multi-Source Ingestion: Pulls live quotes from EaseMyTrip and Google Flights.
5. SQLite Storage: Writes fresh quotes directly into airfare_index.db for instant dashboard consumption.
"""

import os
import sys
import time
import argparse
import gc
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Ensure cloud runner / standalone worker enables Playwright
os.environ["ENABLE_CLOUD_PLAYWRIGHT"] = "1"

# Ensure parent directory is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from scraper import RealtimeFlightScraper, AIRPORT_NAMES
from robot_guard import robot_guard
from database import db

DEFAULT_TOP_ROUTES = [
    "DEL-BOM",  # 1. Delhi - Mumbai (Largest trunk corridor)
    "DEL-BLR",  # 2. Delhi - Bengaluru (Major tech trunk)
    "BOM-BLR",  # 3. Mumbai - Bengaluru
    "DEL-CCU",  # 4. Delhi - Kolkata
    "DEL-HYD",  # 5. Delhi - Hyderabad
]

def run_worker_cycle(routes, days_ahead=7, verbose=True):
    """Executes a single extraction pass across specified routes."""
    scraper = RealtimeFlightScraper()
    target_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    cycle_stats = {
        "cycle_timestamp": datetime.now().isoformat(),
        "routes_attempted": len(routes),
        "total_quotes_logged": 0,
        "results": []
    }

    print(f"\n================================================================================")
    print(f" AeroDex Scraper Ingestion Worker Pass | Target: T+{days_ahead} ({target_date})")
    print(f"================================================================================")

    for route_idx, route in enumerate(routes, 1):
        if "-" not in route:
            print(f"Skipping invalid route format: {route}")
            continue
        origin, destination = route.split("-", 1)
        origin = origin.strip().upper()
        destination = destination.strip().upper()

        print(f"\n[{route_idx}/{len(routes)}] Ingesting corridor: {origin} -> {destination} on {target_date}...")
        t0 = time.time()

        try:
            res = scraper.search_live(origin, destination, target_date, force_live=True)
            flights = res.get("flights", [])
            data_auth = res.get("data_authenticity", "Unknown")
            is_live = res.get("is_live", False)
            sources = res.get("sources_used", ["Unknown"])

            # Log to SQLite
            logged_count = db.log_flight_quotes(
                flights=flights,
                origin=origin,
                destination=destination,
                departure_date=target_date,
                window=f"T+{days_ahead}",
                source_portal=data_auth
            )
            elapsed = time.time() - t0
            cycle_stats["total_quotes_logged"] += logged_count
            cycle_stats["results"].append({
                "route": route,
                "flights_count": len(flights),
                "is_live": is_live,
                "data_authenticity": data_auth,
                "sources_used": sources,
                "elapsed_seconds": round(elapsed, 2)
            })

            badge = "[LIVE]" if is_live else "[BENCHMARK]"
            print(f"   [OK] {badge} | {data_auth} | {len(flights)} quotes ({logged_count} logged) in {elapsed:.1f}s")
            if flights:
                cheapest = min(flights, key=lambda x: x["total_fare"])
                print(f"     Cheapest: {cheapest['carrier_name']} ({cheapest['flight_number']}) at Rs.{cheapest['total_fare']:,}")

        except Exception as e:
            print(f"   [ERROR] Error extracting {route}: {e}")

        # Polite inter-route pause and memory cleanup
        gc.collect()
        time.sleep(2.0)

    # Compliance telemetry summary
    compliance = robot_guard.get_compliance_status()
    print(f"\n--------------------------------------------------------------------------------")
    print(f" Cycle Summary:")
    print(f" Total Quotes Logged : {cycle_stats['total_quotes_logged']}")
    print(f" Cached Robot Domains: {compliance.get('cached_domains', [])}")
    print(f" Total Robot Checks  : {compliance.get('total_checks', 0)}")
    print(f" Database Status     : {db.get_db_stats().get('total_scraped_quotes_logged', 0)} total historical records")
    print(f"================================================================================\n")
    return cycle_stats

def main():
    parser = argparse.ArgumentParser(description="AeroDex Standalone Background Ingestion Worker")
    parser.add_argument("--routes", type=str, default=",".join(DEFAULT_TOP_ROUTES),
                        help="Comma-separated list of airport code pairs (e.g. DEL-BOM,DEL-BLR)")
    parser.add_argument("--window", type=int, default=7,
                        help="Days ahead for travel departure (e.g. 7 for T+7)")
    parser.add_argument("--interval", type=int, default=300,
                        help="Interval between cycles in seconds (default: 300)")
    parser.add_argument("--once", action="store_true",
                        help="Run a single pass and terminate (ideal for cron)")
    args = parser.parse_args()

    routes = [r.strip() for r in args.routes.split(",") if r.strip()]

    if args.once:
        run_worker_cycle(routes, days_ahead=args.window)
        return

    print(f"[AeroDex Worker] Starting continuous background ingestion (interval: {args.interval}s)...")
    try:
        while True:
            run_worker_cycle(routes, days_ahead=args.window)
            print(f"[AeroDex Worker] Sleeping for {args.interval}s before next cycle. Press Ctrl+C to stop.")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[AeroDex Worker] Clean shutdown requested by user.")

if __name__ == "__main__":
    main()
