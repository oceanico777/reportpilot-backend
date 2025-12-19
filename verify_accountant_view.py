import unittest
from unittest.mock import MagicMock
from app.services.report_generator import generate_tour_summary
from app import models

class TestAccountantView(unittest.TestCase):
    def test_tour_summary_aggregation(self):
        # 1. Setup Mock Reports
        r1 = MagicMock(spec=models.Report)
        r1.tour_id = "TOUR-001"
        r1.amount = 100
        r1.category = "Transport"
        r1.client_name = "Guide A"
        r1.user_id = "u1"

        r2 = MagicMock(spec=models.Report)
        r2.tour_id = "TOUR-001"
        r2.amount = 50
        r2.category = "Food"
        r2.client_name = "Guide A"
        r2.user_id = "u1"

        r3 = MagicMock(spec=models.Report)
        r3.tour_id = "TOUR-002"
        r3.amount = 200
        r3.category = "Transport"
        r3.client_name = "Guide B"
        r3.user_id = "u2"

        reports = [r1, r2, r3]

        # 2. Call Service
        summary = generate_tour_summary(reports)

        # 3. Assertions
        # Should have 2 tours
        self.assertEqual(len(summary), 2)
        
        # Sort by tour_id to be deterministic
        summary.sort(key=lambda x: x["tour_id"])
        
        # TOUR-001 Stats
        t1 = summary[0]
        self.assertEqual(t1["tour_id"], "TOUR-001")
        self.assertEqual(t1["total_amount"], 150)
        self.assertEqual(t1["reports_count"], 2)
        self.assertEqual(t1["categories"]["Transport"], 100)
        self.assertEqual(t1["categories"]["Food"], 50)
        self.assertEqual(t1["guide_name"], "Guide A")

        # TOUR-002 Stats
        t2 = summary[1]
        self.assertEqual(t2["tour_id"], "TOUR-002")
        self.assertEqual(t2["total_amount"], 200)

        print("\nSUCCESS: Tour Aggregation Logic Verified!")

if __name__ == "__main__":
    unittest.main()
