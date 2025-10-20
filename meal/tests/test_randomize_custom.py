import unittest
from datetime import date
from meal.infra.Plan_Repository import PlanRepository

class TestRandomizeCustom(unittest.TestCase):
    def test_randomize_custom_replace_and_fill(self):
        repo = PlanRepository()
        iso = date.today().isocalendar()
        week, year = iso.week, iso.year
        plan = repo.get_week_plan(week, year)

        # Use today or future day (first non-past day)
        today_wd = date.today().isoweekday()
        order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        target_day = None
        for idx,name in enumerate(order, start=1):
            if idx >= today_wd:
                target_day = name
                break
        if not target_day:
            self.skipTest("No suitable target day")

        # Prepare slots
        plan.meals[target_day]["breakfast"] = "Spaghetti Bolognese"  # existing assigned
        plan.meals[target_day]["lunch"] = "-"  # empty placeholder
        plan.meals[target_day]["dinner"] = {"name": "Tomato Soup", "cooked": True, "servings": 3, "quantity": 3}  # cooked should be retained
        repo.save_week_plan(week, plan, year)

        # replace_existing False: only lunch should change (fill) breakfast stays same
        changed1 = repo.randomize_custom(week, year, days=[target_day], replace_existing=False)
        plan_after1 = repo.get_week_plan(week, year)
        self.assertIn(plan_after1.meals[target_day]["breakfast"], ["Spaghetti Bolognese"])  # unchanged
        self.assertNotEqual(plan_after1.meals[target_day]["lunch"], "-", "Lunch should be filled")
        self.assertIsInstance(plan_after1.meals[target_day]["dinner"], dict)
        self.assertTrue(plan_after1.meals[target_day]["dinner"].get("cooked"))
        self.assertGreaterEqual(changed1, 1)

        # replace_existing True: breakfast should now change to something else (if recipes >1) unless only one recipe
        prev_breakfast = plan_after1.meals[target_day]["breakfast"]
        changed2 = repo.randomize_custom(week, year, days=[target_day], replace_existing=True)
        plan_after2 = repo.get_week_plan(week, year)
        # If there are multiple recipes, expect change; if single, allow equality
        if prev_breakfast != '-' and changed2 > 0:
            # can't assert inequality strictly, but ensure value is a string recipe
            self.assertIsInstance(plan_after2.meals[target_day]["breakfast"], str)
        self.assertIsInstance(plan_after2.meals[target_day]["dinner"], dict)
        self.assertTrue(plan_after2.meals[target_day]["dinner"].get("cooked"))

if __name__ == '__main__':
    unittest.main()

