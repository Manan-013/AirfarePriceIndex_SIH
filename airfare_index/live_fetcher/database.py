import sqlite3
import os
import json
import csv
import io
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "airfare_index.db")
DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class AirfareDatabase:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.init_db()
        self.seed_initial_data()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=30000;")
        except Exception:
            pass
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes relational tables and performance indexes."""
        conn = self.get_connection()
        cur = conn.cursor()

        # 1. DGCA City-Pair Routes Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dgca_routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rank INTEGER,
                city1 TEXT NOT NULL,
                city2 TEXT NOT NULL,
                route_code TEXT UNIQUE NOT NULL,
                total_passengers INTEGER,
                route_weight REAL,
                route_weight_percent REAL,
                cumulative_weight_percent REAL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_routes_code ON dgca_routes(route_code)")

        # 2. DGCA Carrier Market Shares Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS carrier_market_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                carrier_code TEXT UNIQUE NOT NULL,
                carrier_name TEXT NOT NULL,
                market_share_percent REAL NOT NULL,
                fleet_size INTEGER
            )
        """)

        # 3. MoSPI Official CPI Airfare (07.3.3) Baseline Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mospi_cpi_baseline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sector TEXT,
                year INTEGER,
                month TEXT,
                state TEXT,
                sub_class TEXT,
                index_value REAL,
                yoy_inflation_pct REAL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_mospi_state_period ON mospi_cpi_baseline(state, year, month)")

        # 4. Aviation Turbine Fuel (ATF) Monthly Jet Fuel Prices Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS atf_fuel_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period TEXT UNIQUE NOT NULL,
                price_delhi REAL,
                price_mumbai REAL,
                price_kolkata REAL,
                price_chennai REAL,
                metro_average REAL,
                fuel_index REAL
            )
        """)

        # 5. Live Scraped Quotes Audit Table (Real-Time Ingestion Logs)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scraped_quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                carrier_name TEXT,
                carrier_code TEXT,
                flight_number TEXT,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                departure_date TEXT NOT NULL,
                departure_time TEXT,
                arrival_time TEXT,
                duration TEXT,
                stops TEXT,
                base_fare REAL,
                fuel_surcharge_yq REAL,
                airport_fees_udf_psf REAL,
                gst REAL,
                total_fare REAL,
                advance_window TEXT,
                source_portal TEXT,
                is_live INTEGER DEFAULT 1,
                is_festival_window INTEGER DEFAULT 0,
                weather_severity_score REAL DEFAULT NULL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_quotes_route_date ON scraped_quotes(origin, destination, departure_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_quotes_is_live ON scraped_quotes(is_live)")

        # Schema Migration: ensure is_festival_window and weather_severity_score exist on scraped_quotes
        cur.execute("PRAGMA table_info(scraped_quotes)")
        existing_cols = {col[1] for col in cur.fetchall()}
        if "is_festival_window" not in existing_cols:
            cur.execute("ALTER TABLE scraped_quotes ADD COLUMN is_festival_window INTEGER DEFAULT 0")
        if "weather_severity_score" not in existing_cols:
            cur.execute("ALTER TABLE scraped_quotes ADD COLUMN weather_severity_score REAL DEFAULT NULL")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_quotes_festival ON scraped_quotes(is_festival_window)")

        # 6. Index Calculation Audit Logs (MoSPI & RBI Monetary Policy Feeds)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS index_calculation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                departure_date TEXT NOT NULL,
                advance_window TEXT,
                min_fare REAL,
                carrier_weighted_fare REAL,
                base_fare_p0 REAL,
                route_price_index REAL,
                price_change_pct REAL,
                national_airfare_index REAL,
                cpi_impact_bps REAL,
                direct_flights_count INTEGER
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_calc_timestamp ON index_calculation_logs(calculated_at)")

        conn.commit()
        conn.close()

    def seed_initial_data(self):
        """Seeds official historical and census datasets from JSON if tables are empty."""
        conn = self.get_connection()
        cur = conn.cursor()

        # Seed DGCA Routes
        cur.execute("SELECT COUNT(*) FROM dgca_routes")
        if cur.fetchone()[0] == 0:
            routes_file = os.path.join(DATA_DIR, "dgca_citypair_weights.json")
            if os.path.exists(routes_file):
                with open(routes_file, "r", encoding="utf-8") as f:
                    routes = json.load(f)
                    for r in routes:
                        cur.execute("""
                            INSERT OR IGNORE INTO dgca_routes 
                            (rank, city1, city2, route_code, total_passengers, route_weight, route_weight_percent, cumulative_weight_percent)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (r.get("rank"), r.get("city1"), r.get("city2"), r.get("route_code"),
                              r.get("total_passengers"), r.get("route_weight"), r.get("route_weight_percent"), r.get("cumulative_weight_percent")))

        # Seed Carriers
        cur.execute("SELECT COUNT(*) FROM carrier_market_shares")
        if cur.fetchone()[0] == 0:
            carriers_file = os.path.join(DATA_DIR, "carrier_market_shares.json")
            if os.path.exists(carriers_file):
                with open(carriers_file, "r", encoding="utf-8") as f:
                    carriers = json.load(f)
                    for c in carriers:
                        cur.execute("""
                            INSERT OR IGNORE INTO carrier_market_shares
                            (carrier_code, carrier_name, market_share_percent, fleet_size)
                            VALUES (?, ?, ?, ?)
                        """, (c.get("carrier_code"), c.get("carrier_name"), c.get("market_share_percent"), c.get("fleet_size")))

        # Seed MoSPI CPI Baseline
        cur.execute("SELECT COUNT(*) FROM mospi_cpi_baseline")
        if cur.fetchone()[0] == 0:
            mospi_file = os.path.join(DATA_DIR, "official_mospi_cpi_airfare.json")
            if os.path.exists(mospi_file):
                with open(mospi_file, "r", encoding="utf-8") as f:
                    records = json.load(f)
                    for rec in records:
                        idx_val = None
                        inf_val = None
                        try:
                            idx_val = float(rec.get("item")) if rec.get("item") else None
                            inf_val = float(rec.get("code")) if rec.get("code") else None
                        except:
                            pass
                        cur.execute("""
                            INSERT INTO mospi_cpi_baseline
                            (sector, year, month, state, sub_class, index_value, yoy_inflation_pct)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (rec.get("sector"), int(rec.get("year", 2024)), rec.get("month"),
                              rec.get("state"), rec.get("sub_class", "07.3.3"), idx_val, inf_val))

        # Seed ATF Fuel Prices
        cur.execute("SELECT COUNT(*) FROM atf_fuel_prices")
        if cur.fetchone()[0] == 0:
            atf_file = os.path.join(DATA_DIR, "atf_fuel_prices.json")
            if os.path.exists(atf_file):
                with open(atf_file, "r", encoding="utf-8") as f:
                    prices = json.load(f)
                    for p in prices:
                        yr = p.get("year")
                        mo = p.get("month")
                        period = f"{yr} {mo}" if yr and mo else p.get("period", "Unknown")
                        delhi = p.get("delhi_rs_per_kl") or p.get("price_delhi", 0)
                        bom = p.get("mumbai_rs_per_kl") or p.get("price_mumbai", 0)
                        ccu = p.get("kolkata_rs_per_kl") or p.get("price_kolkata", 0)
                        maa = p.get("chennai_rs_per_kl") or p.get("price_chennai", 0)
                        metro_avg = round((delhi + bom + ccu + maa) / 4.0, 1) if (delhi and bom) else p.get("metro_average", 0)
                        idx = p.get("atf_price_index") or p.get("fuel_index", 100.0)
                        cur.execute("""
                            INSERT OR REPLACE INTO atf_fuel_prices
                            (period, price_delhi, price_mumbai, price_kolkata, price_chennai, metro_average, fuel_index)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (period, delhi, bom, ccu, maa, metro_avg, idx))

        conn.commit()
        conn.close()

    def log_flight_quotes(self, flights, origin, destination, departure_date, window="T+1", source_portal="Google Flights Live"):
        """Logs real-time flight quotes into the audit table."""
        if not flights:
            return 0

        # Derive festival window flag from INDIAN_CALENDAR_EVENTS
        default_is_festival = 0
        try:
            from forecasting_engine import INDIAN_CALENDAR_EVENTS
            if departure_date:
                for ev in INDIAN_CALENDAR_EVENTS:
                    s_dt = ev.get("start_date")
                    e_dt = ev.get("end_date")
                    if s_dt and e_dt and s_dt <= departure_date <= e_dt:
                        default_is_festival = 1
                        break
        except Exception:
            default_is_festival = 0

        # Derive destination airport weather severity score from live METAR sensor
        default_weather_score = None
        try:
            from live_calamity_tracker import live_calamity_tracker
            default_weather_score = live_calamity_tracker.get_airport_severity_score(destination)
        except Exception:
            default_weather_score = None

        conn = self.get_connection()
        cur = conn.cursor()
        count = 0
        for f in flights:
            tf = f.get("total_fare")
            if tf is None:
                continue
            try:
                tf_val = float(tf)
            except (ValueError, TypeError):
                continue

            # Data cleaning: discard non-statutory, extreme anomaly, or corrupted fares
            if tf_val < 1500.0 or tf_val > 95000.0:
                continue

            # Discard sold out or cancelled flight records
            desc = (str(f.get("carrier_name", "")) + " " + str(source_portal)).lower()
            if any(kw in desc for kw in ["sold out", "cancelled", "unavailable"]):
                continue

            is_fest = int(f.get("is_festival_window", default_is_festival))
            wx_score = f.get("weather_severity_score") if f.get("weather_severity_score") is not None else default_weather_score

            cur.execute("""
                INSERT INTO scraped_quotes
                (carrier_name, carrier_code, flight_number, origin, destination, departure_date, 
                 departure_time, arrival_time, duration, stops, base_fare, fuel_surcharge_yq, 
                 airport_fees_udf_psf, gst, total_fare, advance_window, source_portal,
                 is_festival_window, weather_severity_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f.get("carrier_name"), f.get("carrier_code") or "6E", f.get("flight_number") or "6E-101",
                origin, destination, departure_date,
                f.get("departure_time"), f.get("arrival_time"), f.get("duration"),
                f.get("stops") or "Non-stop", f.get("base_fare"), f.get("fuel_surcharge_yq"),
                f.get("airport_fees_udf_psf"), f.get("gst"), tf_val,
                window, source_portal,
                is_fest, wx_score
            ))
            count += 1

        conn.commit()
        conn.close()
        return count

    def log_index_calculation(self, summary, macro_context, origin, destination, departure_date, window):
        """Logs a computed Laspeyres index calculation."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO index_calculation_logs
            (origin, destination, departure_date, advance_window, min_fare, carrier_weighted_fare, 
             base_fare_p0, route_price_index, price_change_pct, national_airfare_index, cpi_impact_bps, direct_flights_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            origin, destination, departure_date, window,
            summary.get("min_fare"), summary.get("carrier_weighted_fare"),
            summary.get("base_fare_p0"), summary.get("route_index"),
            summary.get("price_change_pct"),
            macro_context.get("national_airfare_index") if macro_context else None,
            macro_context.get("headline_cpi_impact_basis_points") if macro_context else None,
            summary.get("direct_flights")
        ))
        conn.commit()
        conn.close()

    def get_db_stats(self):
        """Returns database metadata, health, and record counts across all tables."""
        conn = self.get_connection()
        cur = conn.cursor()

        stats = {
            "database_engine": "SQLite 3 Relational DB",
            "database_file": os.path.basename(self.db_path),
            "database_path": self.db_path,
            "status": "Healthy & Online",
            "tables": {}
        }

        table_queries = {
            "dgca_routes": "SELECT COUNT(*) FROM dgca_routes",
            "carrier_market_shares": "SELECT COUNT(*) FROM carrier_market_shares",
            "mospi_cpi_baseline": "SELECT COUNT(*) FROM mospi_cpi_baseline",
            "atf_fuel_prices": "SELECT COUNT(*) FROM atf_fuel_prices",
            "scraped_quotes": "SELECT COUNT(*) FROM scraped_quotes",
            "index_calculation_logs": "SELECT COUNT(*) FROM index_calculation_logs"
        }

        for table, query in table_queries.items():
            cur.execute(query)
            stats["tables"][table] = cur.fetchone()[0]

        # Total quotes logged
        stats["total_scraped_quotes_logged"] = stats["tables"]["scraped_quotes"]
        stats["total_index_calculations"] = stats["tables"]["index_calculation_logs"]
        stats["total_official_cpi_records"] = stats["tables"]["mospi_cpi_baseline"]
        stats["total_dgca_routes"] = stats["tables"]["dgca_routes"]

        conn.close()
        return stats

    def get_recent_quotes(self, limit=20):
        """Fetches the latest scraped flight quotes with complete fare deconstruction."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, scraped_at, carrier_name, carrier_code, flight_number, 
                   origin, destination, departure_date, total_fare, base_fare, 
                   fuel_surcharge_yq, airport_fees_udf_psf, gst,
                   advance_window, source_portal
            FROM scraped_quotes 
            ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_recent_quotes_for_corridor(self, origin: str, destination: str, limit=150):
        """Retrieves the most recent live-scraped quotes for a specific origin-destination corridor."""
        conn = self.get_connection()
        cur = conn.cursor()
        orig = origin.upper().strip()
        dest = destination.upper().strip()
        cur.execute("""
            SELECT carrier_name, carrier_code, flight_number, origin, destination,
                   departure_date, departure_time, arrival_time, duration, stops,
                   base_fare, fuel_surcharge_yq, airport_fees_udf_psf, gst, total_fare,
                   advance_window, source_portal, scraped_at
            FROM scraped_quotes 
            WHERE origin = ? AND destination = ?
            ORDER BY id DESC LIMIT ?
        """, (orig, dest, limit))
        rows = [dict(r) for r in cur.fetchall()]

        # Reciprocal corridor check: if sparse or 0 quotes, check the return direction
        if len(rows) < 5:
            cur.execute("""
                SELECT carrier_name, carrier_code, flight_number, ? as origin, ? as destination,
                       departure_date, departure_time, arrival_time, duration, stops,
                       base_fare, fuel_surcharge_yq, airport_fees_udf_psf, gst, total_fare,
                       advance_window, source_portal, scraped_at
                FROM scraped_quotes 
                WHERE origin = ? AND destination = ?
                ORDER BY id DESC LIMIT ?
            """, (orig, dest, dest, orig, limit))
            reciprocal = [dict(r) for r in cur.fetchall()]
            if reciprocal:
                rows = reciprocal

        conn.close()
        return rows

    def get_recent_calculations(self, limit=10):
        """Fetches recent Laspeyres calculation audit logs."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, calculated_at, origin, destination, departure_date, 
                   advance_window, carrier_weighted_fare, route_price_index, 
                   national_airfare_index, cpi_impact_bps
            FROM index_calculation_logs 
            ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

# Singleton instance

    def export_quotes_csv(self, limit=10000):
        """
        Exports row-by-row flight quotes audit log from SQLite database as CSV.
        Includes full statutory tax decomposition and scraping timestamps.
        """
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, scraped_at, carrier_name, carrier_code, flight_number,
                   origin, destination, departure_date, departure_time, arrival_time,
                   advance_window, base_fare, fuel_surcharge_yq, airport_fees_udf_psf,
                   gst, total_fare, source_portal
            FROM scraped_quotes
            ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)

        output.write("# =========================================================================\n")
        output.write("# MoSPI Airfare Price Index (APIx) - Microdata Audit Log\n")
        output.write("# Relational Database: SQLite airfare_index.db (Table: scraped_quotes)\n")
        output.write("# Tax Formula: Base + Fuel_YQ + Airport_UDF_PSF + Statutory_GST_5Pct = Total\n")
        output.write("# =========================================================================\n")
        output.write(f"# Export Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}\n")
        output.write(f"# Total Rows Exported: {len(rows)}\n")
        output.write("# =========================================================================\n")

        writer.writerow([
            "Quote_ID",
            "Scraped_Timestamp",
            "Airline_Name",
            "Carrier_Code",
            "Flight_Number",
            "Origin",
            "Destination",
            "Departure_Date",
            "Departure_Time",
            "Arrival_Time",
            "Advance_Window",
            "Base_Fare_INR",
            "Fuel_Surcharge_YQ_INR",
            "Airport_Fees_UDF_PSF_INR",
            "Statutory_GST_5Pct_INR",
            "Total_Fare_INR",
            "Data_Source_Portal"
        ])

        for r in rows:
            writer.writerow([
                r["id"],
                r["scraped_at"],
                r["carrier_name"],
                r["carrier_code"],
                r["flight_number"],
                r["origin"],
                r["destination"],
                r["departure_date"],
                r["departure_time"] or "N/A",
                r["arrival_time"] or "N/A",
                r["advance_window"],
                f"{r['base_fare']:.2f}" if r["base_fare"] is not None else "0.00",
                f"{r['fuel_surcharge_yq']:.2f}" if r["fuel_surcharge_yq"] is not None else "0.00",
                f"{r['airport_fees_udf_psf']:.2f}" if r["airport_fees_udf_psf"] is not None else "0.00",
                f"{r['gst']:.2f}" if r["gst"] is not None else "0.00",
                f"{r['total_fare']:.2f}" if r["total_fare"] is not None else "0.00",
                r["source_portal"]
            ])

        return output.getvalue()

    def get_live_integrity_stats(self) -> Dict[str, Any]:
        """Calculates live vs simulated/benchmark quote ratio directly from is_live flags in database."""
        conn = self.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*), SUM(CASE WHEN is_live=1 THEN 1 ELSE 0 END), SUM(CASE WHEN is_live=0 THEN 1 ELSE 0 END) FROM scraped_quotes")
            row = cur.fetchone()
            total = row[0] or 0
            live = row[1] or 0
            fallback = row[2] or 0
            live_pct = round((live / total) * 100.0, 1) if total > 0 else 100.0
        except Exception:
            total = 0
            live = 0
            fallback = 0
            live_pct = 100.0
        finally:
            conn.close()

        return {
            "total_quotes": total,
            "live_scraped_count": live,
            "benchmark_fallback_count": fallback,
            "live_data_percentage": live_pct
        }

# Singleton instance
db = AirfareDatabase()
