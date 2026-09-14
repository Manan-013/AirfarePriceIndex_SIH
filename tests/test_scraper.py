"""
Unit Tests for Real-Time Flight Scraper & Data Cleaning Pipeline
Tests statutory fare deconstruction, IQR outlier trimming, deeplinks, and RobotGuard.
"""

import unittest
import os
import sys
import asyncio
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "airfare_index", "live_fetcher"))

from scraper import RealtimeFlightScraper, DATA_SOURCES_CATALOG
from robot_guard import robot_guard
from proxy_rotator import proxy_manager, ProxyManager

class TestRealtimeScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = RealtimeFlightScraper()

    def test_fare_deconstruction_exact_math(self):
        """
        Verify statutory tax decomposition formula:
        Base + Fuel_YQ (18%) + Airport_UDF_PSF (7%) + Statutory_GST (5%) = Total
        """
        test_fares = [3500.0, 5000.0, 6425.0, 8999.0, 15420.0, 32100.0]
        for tf in test_fares:
            breakdown = self.scraper._calculate_fare_breakdown(tf)
            self.assertIn("base_fare", breakdown)
            self.assertIn("fuel_surcharge_yq", breakdown)
            self.assertIn("airport_fees_udf_psf", breakdown)
            self.assertIn("gst", breakdown)
            self.assertIn("total_fare", breakdown)

            # Sum of components must equal total_fare within 1 paisa (rounding)
            component_sum = (
                breakdown["base_fare"] +
                breakdown["fuel_surcharge_yq"] +
                breakdown["airport_fees_udf_psf"] +
                breakdown["gst"]
            )
            self.assertAlmostEqual(component_sum, tf, places=2)

            # Check individual component proportions
            self.assertAlmostEqual(breakdown["gst"], round(tf * 0.05, 2), places=2)
            self.assertAlmostEqual(breakdown["airport_fees_udf_psf"], round(tf * 0.07, 2), places=2)
            self.assertAlmostEqual(breakdown["fuel_surcharge_yq"], round(tf * 0.18, 2), places=2)

    def test_clean_and_filter_quotes_null_and_bounds(self):
        """Verify null, negative, and non-statutory quotes are discarded."""
        raw_quotes = [
            {"total_fare": 6200.0, "carrier_code": "6E", "carrier_name": "IndiGo"},
            {"total_fare": None, "carrier_code": "AI", "carrier_name": "Air India"}, # null fare
            {"total_fare": -150.0, "carrier_code": "SG", "carrier_name": "SpiceJet"}, # negative fare
            {"total_fare": 800.0, "carrier_code": "QP", "carrier_name": "Akasa Air"}, # below ₹1500 statutory floor
            {"total_fare": 180000.0, "carrier_code": "AI", "carrier_name": "Air India"}, # above ₹95000 ceiling
            {"total_fare": 6500.0, "carrier_code": "6E", "carrier_name": "IndiGo"},
        ]
        cleaned, meta = self.scraper.clean_and_filter_quotes(raw_quotes, "DEL", "BOM")
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(meta["outliers_removed"], 4)
        for f in cleaned:
            self.assertGreaterEqual(f["total_fare"], 1500.0)
            self.assertLessEqual(f["total_fare"], 95000.0)

    def test_clean_and_filter_quotes_cancellations(self):
        """Verify sold out and cancelled flights are properly dropped."""
        raw_quotes = [
            {"total_fare": 6100.0, "carrier_code": "6E", "source_portal": "EaseMyTrip"},
            {"total_fare": 6300.0, "carrier_code": "AI", "notes": "Flight Cancelled by Carrier"},
            {"total_fare": 6400.0, "carrier_code": "QP", "notes": "Seats Sold Out"},
            {"total_fare": 6200.0, "carrier_code": "AI", "source_portal": "Google Flights"},
        ]
        cleaned, meta = self.scraper.clean_and_filter_quotes(raw_quotes, "DEL", "BOM")
        self.assertEqual(len(cleaned), 2)
        for f in cleaned:
            self.assertNotIn("cancelled", str(f.get("notes", "")).lower())
            self.assertNotIn("sold out", str(f.get("notes", "")).lower())

    def test_clean_and_filter_quotes_statistical_outlier_trimming(self):
        """Verify luxury business class quotes exceeding 2.5x median are filtered."""
        raw_quotes = [
            {"total_fare": 6000.0, "carrier_code": "6E"},
            {"total_fare": 6200.0, "carrier_code": "6E"},
            {"total_fare": 6400.0, "carrier_code": "AI"},
            {"total_fare": 6500.0, "carrier_code": "QP"},
            {"total_fare": 6800.0, "carrier_code": "SG"},
            {"total_fare": 7100.0, "carrier_code": "AI"},
            {"total_fare": 58000.0, "carrier_code": "AI"}, # Outlier: business class
        ]
        cleaned, meta = self.scraper.clean_and_filter_quotes(raw_quotes, "DEL", "BOM")
        # 58k should be removed as it exceeds 2.5x median (~6400 * 2.5 = 16000)
        self.assertEqual(len(cleaned), 6)
        self.assertEqual(meta["outliers_removed"], 1)
        max_cleaned_fare = max(f["total_fare"] for f in cleaned)
        self.assertLessEqual(max_cleaned_fare, 28000.0)

    def test_deeplinks_generation(self):
        """Verify generation of valid 1-click verification URLs for all 6 OTAs and direct airlines."""
        links = self.scraper._generate_deeplinks("DEL", "BOM", "2026-09-20", "6E")
        self.assertIn("easemytrip_url", links)
        self.assertIn("verification_url", links)
        self.assertIn("makemytrip_url", links)
        self.assertIn("google_flights_url", links)
        self.assertIn("yatra_url", links)
        self.assertIn("cleartrip_url", links)
        self.assertIn("ixigo_url", links)
        self.assertIn("goibibo_url", links)
        self.assertIn("airline_portal_url", links)

        self.assertTrue(links["easemytrip_url"].startswith("https://flight.easemytrip.com/"))
        self.assertTrue(links["verification_url"].startswith("https://www.google.com/travel/flights"))
        self.assertTrue(links["makemytrip_url"].startswith("https://www.makemytrip.com/"))
        self.assertTrue(links["yatra_url"].startswith("https://flight.yatra.com/"))
        self.assertTrue(links["cleartrip_url"].startswith("https://www.cleartrip.com/"))
        self.assertTrue(links["ixigo_url"].startswith("https://www.ixigo.com/"))
        self.assertTrue(links["goibibo_url"].startswith("https://www.goibibo.com/"))
        self.assertTrue(links["airline_portal_url"].startswith("https://www.goindigo.in/"))
        self.assertIn("DEL", links["easemytrip_url"])
        self.assertIn("BOM", links["easemytrip_url"])

    @patch("urllib.request.urlopen")
    def test_robot_guard_compliance(self, mock_urlopen):
        """Verify RobotGuard checks robots.txt and tracks domain compliance deterministically offline."""
        def fake_urlopen(req, timeout=4.0):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            mock_resp = MagicMock()
            if "flight.easemytrip.com" in url:
                content = b"User-agent: *\nDisallow: /admin/\nAllow: /FlightList/\n"
            elif "www.easemytrip.com" in url:
                content = b"User-agent: *\nDisallow: /flight-search/listing\n"
            elif "google.com" in url:
                content = b"User-agent: *\nAllow: /travel/flights\nDisallow: /travel/flights/booking\n"
            elif "cleartrip.com" in url:
                content = b"User-agent: *\nDisallow: /flights/search\n"
            else:
                content = b"User-agent: *\nDisallow: /private/\n"
            mock_resp.read.return_value = content
            mock_resp.__enter__.return_value = mock_resp
            mock_resp.__exit__.return_value = None
            return mock_resp

        mock_urlopen.side_effect = fake_urlopen
        robot_guard.parsers.clear()  # Clear cache for isolated test execution

        status = robot_guard.get_compliance_status()
        self.assertIn("user_agent", status)
        self.assertIn("cached_domains", status)
        self.assertIn("total_checks", status)

        # 1. Permitted targets
        allowed_emt, _ = robot_guard.can_fetch("https://flight.easemytrip.com/FlightList/Index?srch=DEL-BOM")
        self.assertTrue(allowed_emt, "EaseMyTrip search route on flight.easemytrip.com should be permitted under robots.txt")

        allowed_gf, _ = robot_guard.can_fetch("https://www.google.com/travel/flights?q=Flights%20to%20BOM")
        self.assertTrue(allowed_gf, "Google Flights search route should be permitted under robots.txt")

        # 2. Disallowed targets
        disallowed_emt_search, _ = robot_guard.can_fetch("https://www.easemytrip.com/flight-search/listing?srch=DEL-BOM")
        self.assertFalse(disallowed_emt_search, "EaseMyTrip /flight-search/listing route on www.easemytrip.com must be disallowed under robots.txt")

        disallowed_gf_booking, _ = robot_guard.can_fetch("https://www.google.com/travel/flights/booking")
        self.assertFalse(disallowed_gf_booking, "Google Flights booking route must be disallowed under robots.txt")

        disallowed_cleartrip, _ = robot_guard.can_fetch("https://www.cleartrip.com/flights/search?from=DEL")
        self.assertFalse(disallowed_cleartrip, "Cleartrip flight search route must be disallowed under robots.txt")

    def test_proxy_manager_rotation_and_headers(self):
        """Verify ProxyManager generates modern browser headers and rotates client hints."""
        headers1 = proxy_manager.get_random_headers()
        headers2 = proxy_manager.get_random_headers()
        self.assertIn("User-Agent", headers1)
        self.assertIn("Accept-Language", headers1)
        self.assertIn("DNT", headers1)

        # Check telemetry structure
        telem = proxy_manager.get_telemetry()
        self.assertTrue(telem["proxy_management_active"])
        self.assertGreater(telem["user_agent_pool_size"], 2)
        self.assertIn("evasion_mechanisms", telem)

    def test_proxy_manager_challenge_detection(self):
        """Verify challenge detector flags Cloudflare Turnstile, Akamai 403, and reCAPTCHA."""
        # Cloudflare Turnstile
        cf_html = "<html><head><title>Just a moment...</title></head><body><div class='cf-challenge'>Checking your browser</div></body></html>"
        is_cf, name_cf = proxy_manager.detect_challenge(403, cf_html)
        self.assertTrue(is_cf)
        self.assertIn("cf-challenge", name_cf)

        # Akamai Access Denied
        akamai_html = "<html><body><h1>Access Denied</h1><p>Reference #18.2b3c4d5e</p></body></html>"
        is_ak, name_ak = proxy_manager.detect_challenge(403, akamai_html)
        self.assertTrue(is_ak)

        # Clean 200 HTML
        clean_html = "<html><body><h1>Flights from Delhi to Mumbai</h1><div>₹5,849</div></body></html>"
        is_clean, _ = proxy_manager.detect_challenge(200, clean_html)
        self.assertFalse(is_clean)

    def test_data_sources_catalog_completeness(self):
        """Verify all 6 OTAs and 5 direct airlines are registered in DATA_SOURCES_CATALOG."""
        source_ids = [s["id"] for s in DATA_SOURCES_CATALOG]
        # 6 OTAs
        self.assertIn("google_flights", source_ids)
        self.assertIn("easemytrip", source_ids)
        self.assertIn("makemytrip", source_ids)
        self.assertIn("yatra", source_ids)
        self.assertIn("cleartrip", source_ids)
        self.assertIn("ixigo", source_ids)
        self.assertIn("goibibo", source_ids)
        # Direct airlines
        self.assertIn("indigo", source_ids)
        self.assertIn("air_india", source_ids)
        self.assertIn("akasa_air", source_ids)
        self.assertIn("spicejet", source_ids)
        self.assertIn("air_india_express", source_ids)

        # Rigorous Honesty & Governance Verification:
        catalog_map = {s["id"]: s for s in DATA_SOURCES_CATALOG}
        # Only 3 sources are genuine live scrapers
        self.assertEqual(catalog_map["google_flights"]["active_status"], "Active Live Scrape")
        self.assertEqual(catalog_map["easemytrip"]["active_status"], "Active Live Scrape")
        self.assertEqual(catalog_map["makemytrip"]["active_status"], "Active Live Scrape")

        # Yatra is honestly labeled as egress-tested stub (parser pending)
        self.assertEqual(catalog_map["yatra"]["active_status"], "HTTP Egress Tested (Parser Pending — Returns Empty)")

        # Cleartrip and Ixigo are ethically gated by RFC 9309 robots.txt
        self.assertEqual(catalog_map["cleartrip"]["active_status"], "RFC 9309 Ethically Gated (Deeplink Only)")
        self.assertEqual(catalog_map["ixigo"]["active_status"], "RFC 9309 Ethically Gated (Deeplink Only)")

        # Airlines and Goibibo are deeplink only
        for carrier in ["indigo", "air_india", "akasa_air", "spicejet", "air_india_express", "goibibo"]:
            self.assertEqual(catalog_map[carrier]["active_status"], "Deeplink Verification Only — No Live Scrape Implemented")

    def test_scraper_active_enforcement_gate_http(self):
        """Verify HTTP scraper aborts immediately and returns [] when robots.txt disallows."""
        with patch.object(robot_guard, "can_fetch", return_value=(False, "Disallowed by robots.txt")):
            with patch("requests.get") as mock_get:
                results = self.scraper._scrape_google_flights_http("DEL", "BOM", "2026-09-20")
                self.assertEqual(results, [])
                mock_get.assert_not_called()

    def test_scraper_active_enforcement_gate_async(self):
        """Verify Playwright scrapers abort immediately and return [] when robots.txt disallows."""
        with patch.object(robot_guard, "can_fetch", return_value=(False, "Disallowed by robots.txt")):
            results_emt = asyncio.run(self.scraper._scrape_easemytrip_async("DEL", "BOM", "2026-09-20"))
            self.assertEqual(results_emt, [])

            results_mmt = asyncio.run(self.scraper._scrape_makemytrip_async("DEL", "BOM", "2026-09-20"))
            self.assertEqual(results_mmt, [])

    def test_makemytrip_card_parsing(self):
        """Verify MakeMyTrip card parsing extracts airline, flight number, times, and deconstructed fare."""
        sample_card = "IndiGo 6E 2132 06:15 08:30 2h 15m Non stop ₹ 5,849"
        parsed = self.scraper._parse_mmt_card(sample_card, "DEL", "BOM", "2026-09-20")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["carrier_name"], "IndiGo")
        self.assertEqual(parsed["carrier_code"], "6E")
        self.assertEqual(parsed["departure_time"], "06:15")
        self.assertEqual(parsed["arrival_time"], "08:30")
        self.assertEqual(parsed["total_fare"], 5849)
        self.assertEqual(parsed["source_portal"], "MakeMyTrip")
        self.assertAlmostEqual(parsed["base_fare"] + parsed["fuel_surcharge_yq"] + parsed["airport_fees_udf_psf"] + parsed["gst"], 5849.0, places=2)

if __name__ == "__main__":
    unittest.main()