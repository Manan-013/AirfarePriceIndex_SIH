"""
Integration Tests for AeroDex REST API Endpoints
Tests live pulse telemetry, search endpoint, robots compliance, and microdata CSV export.
"""

import unittest
import urllib.request
import urllib.parse
import json
import socket

SERVER_URL = "http://localhost:8000"

def is_server_online(host="localhost", port=8000):
    try:
        sock = socket.create_connection((host, port), timeout=1.0)
        sock.close()
        return True
    except OSError:
        return False

@unittest.skipUnless(is_server_online(), "AeroDex server (port 8000) must be running for API integration tests")
class TestAeroDexAPI(unittest.TestCase):

    def test_live_pulse_endpoint(self):
        """Verify GET /api/v1/live/pulse returns valid JSON with national index telemetry."""
        url = f"{SERVER_URL}/api/v1/live/pulse"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("status", data)
            self.assertIn("national_index", data)
            self.assertIn("cpi_impact_bps", data)
            self.assertIn("total_quotes_logged", data)
            self.assertGreaterEqual(data["national_index"], 100.0)
            self.assertEqual(data["status"], "LIVE_FEED_ONLINE")

    def test_search_flight_endpoint(self):
        """Verify POST /api/v1/search returns formatted flight cards and Laspeyres summary."""
        url = f"{SERVER_URL}/api/v1/search"
        payload = json.dumps({"origin": "DEL", "destination": "BOM", "date": "2026-09-20"}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "success")
            self.assertTrue(data.get("is_live"), "Monitored corridor should return live data")
            self.assertIn("flights", data)
            self.assertTrue(len(data["flights"]) >= 5)

            # Check flight card structure
            flight = data["flights"][0]
            self.assertIn("carrier_name", flight)
            self.assertIn("flight_number", flight)
            self.assertIn("total_fare", flight)
            self.assertIn("base_fare", flight)
            self.assertIn("fuel_surcharge_yq", flight)
            self.assertIn("gst", flight)
            self.assertIn("verification_url", flight)

            # Check Laspeyres summary structure
            self.assertIn("summary", data)
            self.assertIn("carrier_weighted_fare", data["summary"])
            self.assertIn("route_index", data["summary"])

    def test_robots_compliance_endpoint(self):
        """Verify GET /api/v1/compliance/robots returns active ethical audit logs."""
        url = f"{SERVER_URL}/api/v1/compliance/robots"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("user_agent", data)
            self.assertIn("cached_domains", data)
            self.assertIn("total_checks", data)

    def test_export_quotes_csv_endpoint(self):
        """Verify GET /api/v1/export/quotes returns statutory RFC-4180 CSV."""
        url = f"{SERVER_URL}/api/v1/export/quotes"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            self.assertEqual(resp.status, 200)
            csv_content = resp.read().decode("utf-8")
            self.assertIn("MoSPI Airfare Price Index", csv_content)
            self.assertIn("Base_Fare_INR", csv_content)
            self.assertIn("Fuel_Surcharge_YQ_INR", csv_content)
            self.assertIn("Statutory_GST_5Pct_INR", csv_content)

    def test_forecast_live_calamities_endpoint(self):
        """Verify GET /api/v1/forecast/live_calamities returns sensor status."""
        url = f"{SERVER_URL}/api/v1/forecast/live_calamities"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("airspace_status", data)
            self.assertIn("all_stations", data)

    def test_weekly_index_endpoint(self):
        """Verify GET /api/v1/index/weekly returns 12-week rolling timeline JSON."""
        url = f"{SERVER_URL}/api/v1/index/weekly"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 12)
            week0 = data[0]
            self.assertIn("week_code", week0)
            self.assertIn("weekly_airfare_index", week0)
            self.assertIn("headline_cpi_impact_bps", week0)

    def test_export_weekly_csv_endpoint(self):
        """Verify GET /api/v1/export/weekly returns valid CSV bulletin."""
        url = f"{SERVER_URL}/api/v1/export/weekly"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            self.assertEqual(resp.status, 200)
            csv_content = resp.read().decode("utf-8")
            self.assertIn("WEEKLY AIRFARE PRICE INDEX", csv_content)
            self.assertIn("Week_Code", csv_content)
            self.assertIn("Headline_CPI_Impact_Basis_Points", csv_content)

    def test_export_daily_csv_endpoint(self):
        """Verify GET /api/v1/export/daily returns valid daily bulletin CSV."""
        url = f"{SERVER_URL}/api/v1/export/daily"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            self.assertEqual(resp.status, 200)
            csv_content = resp.read().decode("utf-8")
            self.assertIn("DAILY SECTOR BULLETIN", csv_content)
            self.assertIn("Sector_Code", csv_content)

if __name__ == "__main__":
    unittest.main()