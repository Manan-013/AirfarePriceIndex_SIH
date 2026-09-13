"""
Live Flight Price Search Server with Automated Real-Time Background Scraper
Serves the web dashboard and handles REST API queries at /api/v1/search and /api/v1/live/pulse.
Uses standard Python libraries with zero external dependencies required.
"""

import http.server
import socketserver
import json
import urllib.parse
import os
import sys
import threading
import time
import random
from datetime import datetime, timedelta

# Ensure current module directory is in sys.path for cloud runners (Render/Railway/Docker)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Import our live scraper, statistical index engine, SQLite database, and AI Situation Engine
from scraper import RealtimeFlightScraper, AIRPORT_NAMES
from index_engine import AirfareIndexEngine
from database import db
from ai_engine import AirfareAIEngine
from forecasting_engine import forecast_engine
from live_calamity_tracker import live_calamity_tracker

PORT = int(os.environ.get("PORT", 8000))
STATIC_DIR = os.path.join(CURRENT_DIR, "static")
scraper = RealtimeFlightScraper()
index_engine = AirfareIndexEngine()
ai_engine = AirfareAIEngine(db, index_engine)

MONITORED_ROUTES = [
    # Metros & High-Volume Trunks (Cat-I)
    ("DEL", "BOM"),
    ("BLR", "DEL"),
    ("BLR", "BOM"),
    ("DEL", "CCU"),
    ("DEL", "HYD"),
    ("DEL", "PNQ"),
    ("BOM", "GOI"),
    ("BOM", "MAA"),
    ("AMD", "DEL"),
    ("BLR", "HYD"),
    # Strategic & Remote Regions (Cat-II / IIA)
    ("DEL", "SXR"),  # Srinagar (J&K)
    ("DEL", "GAU"),  # Guwahati (Northeast Gateway)
    ("CCU", "GAU"),  # Northeast Corridor
    ("DEL", "IXZ"),  # Port Blair (Andaman Islands)
    ("DEL", "IXL"),  # Leh (Ladakh)
    # Tier-2 Commercial & Regional Hubs (Cat-III)
    ("DEL", "COK"),  # Kochi (South)
    ("DEL", "PAT"),  # Patna (East)
    ("DEL", "LKO"),  # Lucknow (North)
    ("BOM", "JAI"),  # Jaipur (West)
    ("BOM", "AMD"),  # Western Business
    ("MAA", "BLR"),  # Southern Interstate
    ("DEL", "BBI"),  # Bhubaneswar (East)
    ("DEL", "ATQ"),  # Amritsar (North)
    ("DEL", "IDR"),  # Indore (Central)
    ("BOM", "COK"),  # West-South Corridor
]

class AutoUpdateManager:
    def __init__(self):
        self.is_running = True
        self.interval_seconds = 12  # 12-second live refresh cycle matching frontend cadence
        self.pause_until = 0
        self.current_route_idx = 0
        self.latest_fares = {
            "DEL-BOM": 6314.0, "BLR-DEL": 6860.0, "BLR-BOM": 5210.0,
            "DEL-CCU": 6070.0, "DEL-HYD": 5850.0, "DEL-PNQ": 6470.0,
            "BOM-GOI": 3950.0, "BOM-MAA": 5540.0, "AMD-DEL": 4490.0,
            "BLR-HYD": 3850.0, "DEL-SXR": 5340.0, "DEL-GAU": 6120.0,
            "CCU-GAU": 3450.0, "DEL-IXZ": 8450.0, "DEL-IXL": 6250.0,
            "DEL-COK": 7150.0, "DEL-PAT": 4650.0, "DEL-LKO": 3850.0,
            "BOM-JAI": 4750.0, "BOM-AMD": 3250.0, "MAA-BLR": 2950.0,
            "DEL-BBI": 5350.0, "DEL-ATQ": 3450.0, "DEL-IDR": 3950.0,
            "BOM-COK": 5650.0
        }
        self.composite_fares = {
            "DEL-BOM": 6195.0, "BLR-DEL": 6640.0, "BLR-BOM": 5050.0,
            "DEL-CCU": 6070.0, "DEL-HYD": 5880.0, "DEL-PNQ": 6250.0,
            "BOM-GOI": 3950.0, "BOM-MAA": 5360.0, "AMD-DEL": 4340.0,
            "BLR-HYD": 3750.0, "DEL-SXR": 5240.0, "DEL-GAU": 6020.0,
            "CCU-GAU": 3350.0, "DEL-IXZ": 8150.0, "DEL-IXL": 6050.0,
            "DEL-COK": 6950.0, "DEL-PAT": 4550.0, "DEL-LKO": 3750.0,
            "BOM-JAI": 4650.0, "BOM-AMD": 3150.0, "MAA-BLR": 2850.0,
            "DEL-BBI": 5250.0, "DEL-ATQ": 3350.0, "DEL-IDR": 3850.0,
            "BOM-COK": 5450.0
        }
        self.window_multipliers = {
            "T+1": 1.52,
            "T+7": 1.32,
            "T+15": 1.16,
            "T+30": 1.05,
            "T+45": 0.98
        }
        self.last_scrape_event = {
            "route": "DEL → BOM",
            "route_code": "DEL-BOM",
            "time": datetime.now().strftime("%H:%M:%S"),
            "flights_count": 54,
            "lowest_fare": 6314,
            "weighted_fare": 6675,
            "window": "T+1",
            "source": "Live Google Flights Feed",
            "status": "INITIALIZED"
        }
        self.lock = threading.Lock()
        self.is_scraping = False
        self.active_scraping_route = None
        self.next_scrape_timestamp = time.time() + self.interval_seconds
        self.worker_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.worker_thread.start()

    def _run_loop(self):
        time.sleep(2)
        while True:
            if not self.is_running or time.time() < self.pause_until:
                time.sleep(1)
                continue

            try:
                origin, dest = MONITORED_ROUTES[self.current_route_idx % len(MONITORED_ROUTES)]
                self.current_route_idx += 1
                
                days_offset = random.choice([1, 7, 15])
                travel_date = (datetime.now() + timedelta(days=days_offset)).strftime("%Y-%m-%d")
                route_code = f"{origin}-{dest}"
                window_key = f"T+{days_offset}"

                self.is_scraping = True
                self.active_scraping_route = f"{origin} → {dest} ({window_key})"
                print(f"[AUTO-SCRAPER] Live automated extraction for {route_code} ({window_key})...")
                res = scraper.search_live(origin, dest, travel_date)

                if res and res.get("flights"):
                    flights = res["flights"]
                    fares = [f["total_fare"] for f in flights]
                    cw_fare = index_engine.compute_carrier_weighted_fare(flights)
                    sector_idx = index_engine.calculate_route_index(route_code, cw_fare)

                    # Persist to SQLite
                    db.log_flight_quotes(flights, origin, dest, travel_date, window=window_key, source_portal=res.get("data_authenticity", "Automated Live Scraper"))
                    db.log_index_calculation(
                        {
                            "min_fare": min(fares),
                            "max_fare": max(fares),
                            "avg_fare": round(sum(fares)/len(fares)),
                            "carrier_weighted_fare": cw_fare,
                            **sector_idx
                        },
                        {},
                        origin,
                        dest,
                        travel_date,
                        window=window_key
                    )

                    # Compute de-surged constant quality tariff for National Basket Index
                    mult = self.window_multipliers.get(window_key, 1.30)
                    composite_tariff = round(cw_fare / mult, 2)

                    with self.lock:
                        self.latest_fares[route_code] = cw_fare
                        self.composite_fares[route_code] = composite_tariff
                        self.last_scrape_event = {
                            "route": f"{origin} → {dest}",
                            "route_code": route_code,
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "flights_count": len(flights),
                            "lowest_fare": min(fares),
                            "weighted_fare": round(cw_fare),
                            "window": window_key,
                            "source": res.get("data_authenticity", "Live Google Flights / OTA"),
                            "status": "UPDATED"
                        }
                    print(f"  [AUTO-SCRAPER] Logged {len(flights)} quotes for {route_code}. SQLite updated!")
                    try:
                        current_pulse = self.get_live_pulse()
                        # Instant synchronous update for 0ms cache freshness
                        ai_engine.refresh_situation_summary(force_local=True, live_pulse=current_pulse)
                        # Rate-limited background AI upgrade (at most once every 15 minutes to conserve quota)
                        now_ts = time.time()
                        if ai_engine.gemini_client and (now_ts - getattr(ai_engine, "_last_gemini_call", 0) > 900):
                            ai_engine._last_gemini_call = now_ts
                            threading.Thread(target=ai_engine.refresh_situation_summary, kwargs={"force_local": False, "live_pulse": current_pulse}, daemon=True).start()
                    except Exception as ai_e:
                        print(f"  [AI Engine Error] {ai_e}")

            except Exception as e:
                print(f"  [AUTO-SCRAPER ERROR] {e}")
            finally:
                self.is_scraping = False
                self.active_scraping_route = None
                self.next_scrape_timestamp = time.time() + self.interval_seconds

            time.sleep(self.interval_seconds)

    def get_live_pulse(self):
        with self.lock:
            sampled_routes = [{"route_code": r, "fare": f} for r, f in self.composite_fares.items()]
            national_context = index_engine.compute_national_index(sampled_routes)
            db_stats = db.get_db_stats()
            sector_matrix = index_engine.get_sector_heatmap_matrix()

            seconds_remaining = max(0, int(round(self.next_scrape_timestamp - time.time())))
            return {
                "status": "LIVE_FEED_ONLINE",
                "is_running": self.is_running,
                "interval_seconds": self.interval_seconds,
                "is_scraping": self.is_scraping,
                "active_scraping_route": self.active_scraping_route,
                "seconds_until_next_scrape": seconds_remaining,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "total_quotes_logged": db_stats.get("total_scraped_quotes_logged", 1000),
                "last_scrape": self.last_scrape_event,
                "national_index": national_context["national_airfare_index"],
                "national_change_pct": national_context["airfare_inflation_vs_base_pct"],
                "cpi_impact_bps": national_context["headline_cpi_impact_basis_points"],
                "cpi_contribution_pct": national_context["headline_cpi_contribution_pct"],
                "latest_fares": self.latest_fares,
                "sector_matrix": sector_matrix
            }

    def pause_briefly(self, seconds=25):
        self.pause_until = time.time() + seconds

auto_manager = AutoUpdateManager()

class FlightAPIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # Favicon handler
        if parsed.path == "/favicon.ico":
            fav_path = os.path.join(STATIC_DIR, "favicon.ico")
            if os.path.exists(fav_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/x-icon")
                self.end_headers()
                with open(fav_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            self.send_response(204)
            self.end_headers()
            return

        # PWA Web App Manifest
        if parsed.path == "/manifest.json":
            manifest_path = os.path.join(STATIC_DIR, "manifest.json")
            if os.path.exists(manifest_path):
                self.send_response(200)
                self.send_header("Content-Type", "application/manifest+json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(manifest_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        # PWA Service Worker script
        if parsed.path == "/sw.js":
            sw_path = os.path.join(STATIC_DIR, "sw.js")
            if os.path.exists(sw_path):
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
                self.send_header("Service-Worker-Allowed", "/")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                with open(sw_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        # API: Real-Time Live Stream Pulse (High-Frequency Feed)
        if parsed.path == "/api/v1/live/pulse":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = auto_manager.get_live_pulse()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # API: Toggle Auto Scraper Pause / Resume
        if parsed.path == "/api/v1/live/toggle":
            auto_manager.is_running = not auto_manager.is_running
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"is_running": auto_manager.is_running}).encode("utf-8"))
            return

        # API: Supported airports
        if parsed.path == "/api/v1/airports":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = [{"code": code, "name": name} for code, name in AIRPORT_NAMES.items()]
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # API: National Airfare Price Index (APIx) & MoSPI CPI Contribution
        if parsed.path == "/api/v1/index/national":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = index_engine.compute_national_index([])
            self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))
            return

        # API: Macroeconomic Comparison Timeline (MoSPI 07.3.3 vs ATF Fuel vs Scraper)
        if parsed.path == "/api/v1/macro/timeline":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = index_engine.get_macro_comparison_timeline()
            self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))
            return

        # API: Top DGCA Route Volume Weights (786 Routes Basket)
        if parsed.path == "/api/v1/routes/weights":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = index_engine.get_top_routes_weights(limit=25)
            self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))
            return

        # API: Carrier Market Shares (IndiGo, Air India, Akasa, SpiceJet)
        if parsed.path == "/api/v1/carriers":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(index_engine.carriers_list, indent=2).encode("utf-8"))
            return

        # API: Sector Dynamic Pricing Heatmap (T+1 to T+45)
        if parsed.path == "/api/v1/heatmap/sectors":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = index_engine.get_sector_heatmap_matrix()
            self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))
            return

        # API: State Airfare Inflation Heatmap (MoSPI 34 States)
        if parsed.path == "/api/v1/heatmap/states":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = index_engine.get_state_inflation_heatmap()
            self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))
            return

        # API: SQLite Database Statistics & System Health
        if parsed.path == "/api/v1/db/stats":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = db.get_db_stats()
            self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))
            return

        # API: Recent Live Scraped Quotes from SQLite Audit Log
        if parsed.path == "/api/v1/db/quotes":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = db.get_recent_quotes(limit=30)
            self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))
            return

        
        # API: Export MoSPI Daily Sector Airfare Bulletin (CSV)
        if parsed.path == "/api/v1/export/daily":
            csv_content = index_engine.generate_daily_bulletin_csv(auto_manager.get_live_pulse())
            filename = f"MoSPI_Daily_Airfare_Index_Bulletin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(csv_content.encode("utf-8"))
            return

        # API: Export MoSPI 20-Month Historical Timeline Series (CSV)
        if parsed.path == "/api/v1/export/monthly":
            csv_content = index_engine.generate_monthly_timeline_csv()
            filename = f"MoSPI_Monthly_Airfare_Series_2025_2026.csv"
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(csv_content.encode("utf-8"))
            return

        # API: Export Scraped Flight Quotes Microdata Audit Log (CSV)
        if parsed.path == "/api/v1/export/quotes":
            csv_content = db.export_quotes_csv(limit=10000)
            filename = f"Scraped_Flight_Quotes_Microdata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(csv_content.encode("utf-8"))
            return

        # API: AI Airfare Situation Room Executive Summary (Instant Pre-Computed <5ms)
        if parsed.path == "/api/v1/ai/summary":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = ai_engine.get_latest_summary()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            return

        # API: AI Configuration Status (Has key, active model, masked key)
        if parsed.path == "/api/v1/ai/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = ai_engine.get_config_status()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        # API: Predictive Calendar Annotated Events
        if parsed.path == "/api/v1/forecast/calendar":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            qs = urllib.parse.parse_qs(parsed.query)
            month = qs.get("month", [None])[0]
            category = qs.get("category", [None])[0]
            cal = forecast_engine.get_annotated_calendar(month=month, category=category)
            self.wfile.write(json.dumps(cal, ensure_ascii=False).encode("utf-8"))
            return

        # API: Real-Time Live Calamity & Aviation METAR Radar
        if parsed.path == "/api/v1/forecast/live_calamities":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = live_calamity_tracker.fetch_all(force_refresh=False)
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            return

        # Debug endpoint to diagnose scraper on Render
        if parsed.path == "/api/v1/debug/scraper":
            import traceback, sys
            debug_info = {
                "playwright_available": scraper.PLAYWRIGHT_AVAILABLE,
                "python_version": sys.version,
                "platform": sys.platform,
            }
            try:
                import asyncio
                flights = asyncio.run(scraper._scrape_google_flights_async("DEL", "BOM", "2026-09-14"))
                debug_info["status"] = "success"
                debug_info["flights_found"] = len(flights)
                debug_info["sample"] = flights[:2] if flights else []
            except Exception as e:
                debug_info["status"] = "error"
                debug_info["error_type"] = type(e).__name__
                debug_info["error_msg"] = str(e)
                debug_info["traceback"] = traceback.format_exc()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(debug_info, indent=2).encode("utf-8"))
            return

        # Default: Serve static files (index.html, styles, scripts)
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        # API: Live Flight Search & Sector Index Calculation
        if parsed.path == "/api/v1/search":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            
            try:
                params = json.loads(post_data)
            except Exception:
                params = urllib.parse.parse_qs(post_data)
                params = {k: v[0] for k, v in params.items()}

            origin = params.get("origin", "DEL")
            destination = params.get("destination", "BOM")
            travel_date = params.get("date", datetime.now().strftime("%Y-%m-%d"))
            route_code = f"{origin}-{destination}"

            print(f"[LIVE SEARCH] {origin} -> {destination} on {travel_date}")
            auto_manager.pause_briefly(25)
            results = scraper.search_live(origin, destination, travel_date)

            if results["flights"]:
                fares = [f["total_fare"] for f in results["flights"]]
                carrier_weighted_fare = index_engine.compute_carrier_weighted_fare(results["flights"])
                sector_index_data = index_engine.calculate_route_index(route_code, carrier_weighted_fare)
                
                results["summary"] = {
                    "min_fare": min(fares),
                    "max_fare": max(fares),
                    "avg_fare": round(sum(fares) / len(fares)),
                    "carrier_weighted_fare": carrier_weighted_fare,
                    "carrier_count": len(set(f["carrier_code"] for f in results["flights"])),
                    "direct_flights": len(results["flights"]),
                    **sector_index_data
                }
            else:
                results["summary"] = {"min_fare": 0, "max_fare": 0, "avg_fare": 0, "carrier_count": 0, "direct_flights": 0}

            pulse = auto_manager.get_live_pulse()
            results["macro_context"] = {
                "national_airfare_index": pulse["national_index"],
                "headline_cpi_impact_basis_points": pulse["cpi_impact_bps"],
                "headline_cpi_contribution_pct": pulse["cpi_contribution_pct"],
                "airfare_inflation_vs_base_pct": pulse["national_change_pct"],
                "routes_evaluated": 25
            }

            # Persist to SQLite
            try:
                if results.get("flights"):
                    db.log_flight_quotes(
                        results["flights"],
                        origin,
                        destination,
                        travel_date,
                        window=results.get("window", "T+1"),
                        source_portal=results.get("data_authenticity", "Live OTA / Google Flights")
                    )
                    db.log_index_calculation(
                        results["summary"],
                        results.get("macro_context", {}),
                        origin,
                        destination,
                        travel_date,
                        results.get("window", "T+1")
                    )
            except Exception as dbe:
                print(f"  [DB Warning] Failed to log quotes to SQLite: {dbe}")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(results, indent=2).encode("utf-8"))
            return

        # API: Conversational Grounded AI Query ("Ask AI")
        if parsed.path == "/api/v1/ai/query":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
                try:
                    params = json.loads(post_data)
                except Exception:
                    params = urllib.parse.parse_qs(post_data)
                    params = {k: v[0] for k, v in params.items()}

                question = params.get("question", "")
                lang = params.get("lang", "auto")
                response_data = ai_engine.handle_conversational_query(question, lang)
            except Exception as ex:
                print(f"[AI Query Error] {ex}")
                response_data = {
                    "answer": f"AeroDex real-time data engine is active. Please ask about any specific route (e.g. DEL-BOM), cheapest fares, or CPI basis points impact.",
                    "language": "en",
                    "source": "AeroDex Grounded Engine"
                }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
            except Exception as write_err:
                print(f"[AI Query Write Error] {write_err}")
            return

        # API: Set / Update Gemini API Key and Model dynamically
        if parsed.path == "/api/v1/ai/config":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            try:
                params = json.loads(post_data)
            except Exception:
                params = urllib.parse.parse_qs(post_data)
                params = {k: v[0] for k, v in params.items()}

            api_key = params.get("api_key", "")
            model = params.get("model", "gemini-3.7-flash")
            success, message = ai_engine.configure_gemini(api_key, model)
            status_data = ai_engine.get_config_status()
            self.send_response(200 if success else 400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": success, "message": message, "config": status_data}).encode("utf-8"))
            return

        # API: Refresh Live Calamity & Aviation METAR Sensors
        if parsed.path == "/api/v1/forecast/refresh_sensors":
            data = live_calamity_tracker.fetch_all(force_refresh=True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            return

        # API: Simulate Forecast for Target Date & Scenario
        if parsed.path == "/api/v1/forecast/simulate":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            try:
                params = json.loads(post_data)
            except Exception:
                params = urllib.parse.parse_qs(post_data)
                params = {k: v[0] for k, v in params.items()}

            target_date = params.get("target_date") or params.get("date", datetime.now().strftime("%Y-%m-%d"))
            scenario = params.get("scenario_id") or params.get("scenario", "auto")
            affected_corridor = params.get("affected_corridor")
            custom_shock_pct = float(params.get("custom_shock_pct", 0.0))

            pulse = auto_manager.get_live_pulse()
            current_live_index = float(pulse.get("national_index", 127.44))

            sim_result = forecast_engine.simulate_forecast(
                target_date,
                scenario=scenario,
                affected_corridor=affected_corridor,
                custom_shock_pct=custom_shock_pct
            )

            # Compute deltas against live index
            sim_result["current_live_index"] = current_live_index
            sim_result["index_delta"] = round(sim_result["projected_national_index"] - current_live_index, 2)
            sim_result["index_delta_pct"] = round(((sim_result["projected_national_index"] - current_live_index) / current_live_index) * 100.0, 1)

            # Generate bilingual executive briefing
            sim_result["ai_briefing"] = ai_engine.generate_forecast_briefing(sim_result)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(sim_result, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

def run_server():
    os.makedirs(STATIC_DIR, exist_ok=True)
    with ThreadedTCPServer(("0.0.0.0", PORT), FlightAPIHandler) as httpd:
        print(f"\n============================================================")
        print(f"  [+] AUTO-UPDATING REAL-TIME FLIGHT FETCHER RUNNING")
        print(f"  [>] URL: http://0.0.0.0:{PORT}")
        print(f"  [>] Live Pulse Stream: http://0.0.0.0:{PORT}/api/v1/live/pulse")
        print(f"============================================================\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    run_server()
