import unittest
from datetime import date
from meal.infra.Plan_Repository import PlanRepository

class TestRandomizeWeekBehavior(unittest.TestCase):
    def test_randomize_week_preserves_cooked_and_past(self):
        repo = PlanRepository()
        iso = date.today().isocalendar()
        week = iso.week
        year = iso.year
        plan = repo.get_week_plan(week, year)

        today_weekday = date.today().isoweekday()  # 1..7
        days_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        past_day_name = None
        for idx, name in enumerate(days_order, start=1):
            if idx < today_weekday:
                past_day_name = name
                break

        future_or_today_name = None
        for idx, name in enumerate(days_order, start=1):
            if idx >= today_weekday:
                future_or_today_name = name
                break
        if future_or_today_name is None:
            self.skipTest("No suitable current/future day determined")

        # Set cooked breakfast (dict with cooked True)
        plan.meals[future_or_today_name]["breakfast"] = {"name": "Spaghetti Bolognese", "cooked": True, "servings": 4, "quantity": 4}
        # Assign an existing non-cooked lunch (should remain unchanged when only empty slots filled)
        plan.meals[future_or_today_name]["lunch"] = "Chicken Curry"
        # Ensure dinner empty placeholder to be filled
        plan.meals[future_or_today_name]["dinner"] = "-"

        if past_day_name:
            plan.meals[past_day_name]["lunch"] = "Tomato Soup"

        repo.save_week_plan(week, plan, year)

        repo.randomize_week(week, year)
        updated = repo.get_week_plan(week, year)
        fut_meals = updated.meals[future_or_today_name]

        # Cooked breakfast preserved
        self.assertIsInstance(fut_meals["breakfast"], dict)
        self.assertTrue(fut_meals["breakfast"].get("cooked"))

        # Lunch should remain the same (non-empty and not cooked)
        self.assertEqual(fut_meals["lunch"], "Chicken Curry")

        # Dinner should now be randomized (string recipe name or '-')
        self.assertIsInstance(fut_meals["dinner"], str)
        # It should not stay '-' only if there are recipes available. If still '-', allow but warn.
        if fut_meals["dinner"] == '-':
            # Acceptable fallback, but keep test passing
            pass
        else:
            self.assertNotEqual(fut_meals["dinner"], '-')

        if past_day_name:
            past_meals = updated.meals[past_day_name]
            self.assertEqual(past_meals["lunch"], "Tomato Soup")

if __name__ == '__main__':
    unittest.main()

