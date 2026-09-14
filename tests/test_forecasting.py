import unittest
import os
import sys
import numpy as np

LIVE_FETCHER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "airfare_index", "live_fetcher")
if LIVE_FETCHER_DIR not in sys.path:
    sys.path.insert(0, LIVE_FETCHER_DIR)

from database import AirfareDatabase
from forecasting_engine import AirfareForecastingEngine, INDIAN_CALENDAR_EVENTS

class TestForecastingEngineML(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = AirfareDatabase()
        cls.engine = AirfareForecastingEngine()

    def test_database_columns_and_quote_population(self):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(scraped_quotes)")
        cols = {row["name"]: row["type"] for row in cur.fetchall()}
        self.assertIn("is_festival_window", cols, "is_festival_window column missing from scraped_quotes")
        self.assertIn("weather_severity_score", cols, "weather_severity_score column missing from scraped_quotes")

        test_flight = [{
            "carrier_name": "IndiGo",
            "carrier_code": "6E",
            "flight_number": "6E-TEST-FESTIVAL-99",
            "departure_time": "08:00",
            "arrival_time": "10:15",
            "duration": "2h 15m",
            "stops": "Non-stop",
            "base_fare": 4500,
            "fuel_surcharge_yq": 1100,
            "airport_fees_udf_psf": 400,
            "gst": 300,
            "total_fare": 6300
        }]

        self.db.log_flight_quotes(test_flight, "DEL", "BOM", "2026-09-15", window="T+1", source_portal="Test Suite")

        cur.execute("SELECT is_festival_window, weather_severity_score FROM scraped_quotes WHERE flight_number = ? ORDER BY id DESC LIMIT 1", ("6E-TEST-FESTIVAL-99",))
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["is_festival_window"], 1, "Flight on 2026-09-15 must be tagged as is_festival_window=1")

        cur.execute("DELETE FROM scraped_quotes WHERE flight_number = ?", ("6E-TEST-FESTIVAL-99",))
        conn.commit()
        conn.close()

    def test_feature_vector_shape_matches_predict(self):
        self.assertIsNotNone(self.engine.model, "Model must be trained and loaded")
        self.assertEqual(self.engine.model.n_features_in_, 9, "Model must have 9 input features")

        sample_x = np.array([[7, 4850.0, 1148, 11, 6, 1, 42, 1, 0.25]])
        pred = self.engine.model.predict(sample_x)
        self.assertEqual(len(pred), 1)
        self.assertGreater(float(pred[0]), 1500.0)

    def test_honesty_guard_fails_loudly_on_unverified_ml_claim(self):
        self.engine.is_festival_learned = True
        with self.assertRaises(AssertionError) as ctx:
            self.engine.simulate_forecast("2026-11-08", scenario="auto")
        self.assertIn("Honesty Violation", str(ctx.exception))
        self.engine.is_festival_learned = False

    def test_heuristic_fallback_honesty_labels(self):
        sim = self.engine.simulate_forecast("2026-11-08", scenario="auto")
        self.assertEqual(sim["multiplier_type"], "Econometric Heuristic Estimate (Calibrated)")
        self.assertIn("calibrated heuristic", sim["methodology_note"].lower())
        self.assertTrue(sim["is_festival_window"])

if __name__ == "__main__":
    unittest.main()
