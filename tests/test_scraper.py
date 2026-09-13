"""
Unit Tests for Real-Time Flight Scraper & Data Cleaning Pipeline
Tests statutory fare deconstruction, IQR outlier trimming, deeplinks, and RobotGuard.
"""

import unittest
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "airfare_index", "live_fetcher"))

from scraper import RealtimeFlightScraper
from robot_guard import robot_guard

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
        """Verify generation of valid 1-click verification URLs for all OTAs."""
        links = self.scraper._generate_deeplinks("DEL", "BOM", "2026-09-20", "6E")
        self.assertIn("easemytrip_url", links)
        self.assertIn("verification_url", links)
        self.assertIn("makemytrip_url", links)
        self.assertIn("airline_portal_url", links)

        self.assertTrue(links["easemytrip_url"].startswith("https://flight.easemytrip.com/"))
        self.assertTrue(links["verification_url"].startswith("https://www.google.com/travel/flights"))
        self.assertTrue(links["makemytrip_url"].startswith("https://www.makemytrip.com/"))
        self.assertIn("DEL", links["easemytrip_url"])
        self.assertIn("BOM", links["easemytrip_url"])

    def test_robot_guard_compliance(self):
        """Verify RobotGuard checks robots.txt and tracks domain compliance."""
        status = robot_guard.get_compliance_status()
        self.assertIn("user_agent", status)
        self.assertIn("cached_domains", status)
        self.assertIn("total_checks", status)

        # EaseMyTrip should be checked and allowed under search path
        allowed, reason = robot_guard.can_fetch("https://flight.easemytrip.com/FlightList/Index?srch=DEL-BOM")
        self.assertTrue(allowed, "EaseMyTrip search route should be permitted under robots.txt")

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