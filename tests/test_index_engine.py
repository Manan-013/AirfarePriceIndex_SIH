"""
Unit Tests for National Airfare Price Index (APIx) Calculation Engine
Tests Laspeyres index mathematical aggregation, carrier weighting, and CPI impacts.
"""

import unittest
import os
import sys

# Add airfare_index directories to path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "airfare_index", "live_fetcher"))
sys.path.insert(0, os.path.join(REPO_ROOT, "airfare_index"))

from index_engine import AirfareIndexEngine, MOSPI_AIRFARE_CPI_WEIGHT

class TestAirfareIndexEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AirfareIndexEngine()

    def test_datasets_loaded(self):
        """Verify DGCA route weights, carrier shares, and baseline data loaded properly."""
        self.assertTrue(len(self.engine.routes_list) > 0, "DGCA routes list should not be empty")
        self.assertTrue(len(self.engine.carriers_list) > 0, "Carrier market shares should not be empty")
        self.assertTrue("DEL-BOM" in self.engine.base_fares, "DEL-BOM should have base fare calibrated")

    def test_laspeyres_single_route_index(self):
        """Verify Laspeyres index: I = (P_t / P_0) * 100."""
        route = "DEL-BOM"
        p0 = self.engine.get_route_base_fare(route)
        self.assertEqual(p0, 4850.0)

        # Case 1: Current fare = Base fare -> Index = 100.0
        res_base = self.engine.calculate_route_index(route, 4850.0)
        self.assertAlmostEqual(res_base["route_index"], 100.0, places=2)
        self.assertAlmostEqual(res_base["price_change_pct"], 0.0, places=2)

        # Case 2: 50% Surge (P_t = 7275.0) -> Index = 150.0
        res_surge = self.engine.calculate_route_index(route, 7275.0)
        self.assertAlmostEqual(res_surge["route_index"], 150.0, places=2)
        self.assertAlmostEqual(res_surge["price_change_pct"], 50.0, places=2)

        # Case 3: 20% Discount (P_t = 3880.0) -> Index = 80.0
        res_discount = self.engine.calculate_route_index(route, 3880.0)
        self.assertAlmostEqual(res_discount["route_index"], 80.0, places=2)
        self.assertAlmostEqual(res_discount["price_change_pct"], -20.0, places=2)

    def test_carrier_weighted_fare_math(self):
        """Verify carrier market share weighted average: Sum(W_c * P_c) / Sum(W_c)."""
        flights = [
            {"carrier_code": "6E", "total_fare": 6000.0},
            {"carrier_code": "6E", "total_fare": 6400.0}, # Avg 6E = 6200
            {"carrier_code": "AI", "total_fare": 7000.0},
            {"carrier_code": "AI", "total_fare": 7400.0}, # Avg AI = 7200
            {"carrier_code": "QP", "total_fare": 5800.0}, # Avg QP = 5800
        ]
        cw_fare = self.engine.compute_carrier_weighted_fare(flights)
        self.assertGreater(cw_fare, 5800.0)
        self.assertLess(cw_fare, 7200.0)

    def test_outlier_filtering_in_carrier_weighting(self):
        """Verify extreme business class / faulty quotes (>2.2x median) do not distort the index."""
        normal_flights = [
            {"carrier_code": "6E", "total_fare": 6000.0},
            {"carrier_code": "6E", "total_fare": 6200.0},
            {"carrier_code": "AI", "total_fare": 6500.0},
            {"carrier_code": "AI", "total_fare": 6800.0},
        ]
        outlier_flights = list(normal_flights) + [
            {"carrier_code": "AI", "total_fare": 55000.0} # 55k outlier
        ]
        fare_normal = self.engine.compute_carrier_weighted_fare(normal_flights)
        fare_with_outlier = self.engine.compute_carrier_weighted_fare(outlier_flights)
        # Outlier should be trimmed and not inflate the fare beyond ₹8,000
        self.assertLess(fare_with_outlier, 8000.0)
        self.assertAlmostEqual(fare_normal, fare_with_outlier, delta=300.0)

    def test_national_composite_index(self):
        """Verify National Composite Laspeyres aggregation across multiple sectors."""
        sampled_routes = [
            {"route_code": "DEL-BOM", "fare": 6062.5}, # 6062.5 / 4850 = 125.0
            {"route_code": "BLR-DEL", "fare": 6500.0}, # 6500.0 / 5200 = 125.0
            {"route_code": "BOM-GOI", "fare": 3875.0}, # 3875.0 / 3100 = 125.0
        ]
        national_res = self.engine.compute_national_index(sampled_routes)
        self.assertIn("national_airfare_index", national_res)
        self.assertIn("headline_cpi_impact_basis_points", national_res)
        self.assertAlmostEqual(national_res["national_airfare_index"], 125.0, places=1)
        self.assertAlmostEqual(national_res["airfare_inflation_vs_base_pct"], 25.0, places=1)

        # CPI Impact: 25% inflation * 0.00077 item weight * 10,000 bps = ~1.92 bps
        expected_bps = (25.0 / 100.0) * MOSPI_AIRFARE_CPI_WEIGHT * 10000.0
        self.assertAlmostEqual(national_res["headline_cpi_impact_basis_points"], expected_bps, delta=0.02)

    def test_sector_heatmap_matrix_structure(self):
        """Verify Sector x Window elasticity heatmap matrix dimensions and bounds."""
        matrix_data = self.engine.get_sector_heatmap_matrix()
        self.assertIn("windows", matrix_data)
        self.assertIn("sectors", matrix_data)
        self.assertEqual(len(matrix_data["windows"]), 5) # T+1, T+7, T+15, T+30, T+45
        self.assertTrue(len(matrix_data["sectors"]) >= 10)

        for sector in matrix_data["sectors"]:
            self.assertIn("route_code", sector)
            self.assertIn("base_fare_p0", sector)
            # T+1 fare should be higher than T+45 fare (dynamic pricing curve)
            t1_fare = sector["windows"]["T+1"]["fare"]
            t45_fare = sector["windows"]["T+45"]["fare"]
            self.assertGreater(t1_fare, t45_fare)

    def test_weekly_aggregation_timeline(self):
        """Verify 12-week rolling aggregation timeline structure, WoW change, and CPI impact."""
        timeline = self.engine.get_weekly_aggregation_timeline(weeks=12)
        self.assertEqual(len(timeline), 12)
        for w in timeline:
            self.assertIn("week_code", w)
            self.assertIn("weekly_airfare_index", w)
            self.assertIn("weighted_average_fare_inr", w)
            self.assertIn("week_over_week_change_pct", w)
            self.assertIn("headline_cpi_impact_bps", w)
            self.assertIn("status", w)
            self.assertGreaterEqual(w["weekly_airfare_index"], 100.0)

    def test_weekly_bulletin_csv(self):
        """Verify Weekly Bulletin CSV export adheres to MoSPI RFC-4180 metadata standards."""
        csv_str = self.engine.generate_weekly_bulletin_csv(weeks=12)
        self.assertIn("WEEKLY AIRFARE PRICE INDEX", csv_str)
        self.assertIn("Week_Code", csv_str)
        self.assertIn("Headline_CPI_Impact_Basis_Points", csv_str)
        self.assertIn("2026-W37", csv_str)

if __name__ == "__main__":
    unittest.main()