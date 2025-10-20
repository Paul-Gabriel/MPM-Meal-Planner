import unittest
from datetime import date, datetime
from meal.infra.Plan_Repository import PlanRepository

class TestResetWeekBehavior(unittest.TestCase):
    def test_reset_week_preserves_cooked_and_past(self):
        repo = PlanRepository()
        iso = date.today().isocalendar()
        week = iso.week
        year = iso.year
        plan = repo.get_week_plan(week, year)

        # Identify a past day (if any) based on today's weekday (1=Mon .. 7=Sun)
        today_weekday = date.today().isoweekday()  # 1..7
        days_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        past_day_name = None
        for idx, name in enumerate(days_order, start=1):
            if idx < today_weekday:  # past
                past_day_name = name
                break

        # Choose a future or today day for cooked & non-cooked examples
        future_or_today_name = None
        for idx, name in enumerate(days_order, start=1):
            if idx >= today_weekday:
                future_or_today_name = name
                break
        if future_or_today_name is None:
            self.skipTest("Could not determine a suitable current/future day")

        # Set a cooked meal in breakfast for future/today day
        plan.meals[future_or_today_name]["breakfast"] = {"name": "Spaghetti Bolognese", "cooked": True, "servings": 4, "quantity": 4}
        # Set a normal (not cooked) meal in lunch for same day
        plan.meals[future_or_today_name]["lunch"] = "Chicken Curry"
        # Set dinner as already '-' to ensure it remains '-'
        plan.meals[future_or_today_name]["dinner"] = plan.meals[future_or_today_name].get("dinner", "-") or "-"

        # If we have a past day, assign a recipe that should not be reset
        if past_day_name:
            plan.meals[past_day_name]["lunch"] = "Tomato Soup"

        repo.save_week_plan(week, plan, year)

        # Perform reset
        repo.reset_week(week, year)

        updated = repo.get_week_plan(week, year)
        fut_meals = updated.meals[future_or_today_name]
        # Cooked breakfast should be preserved as dict with cooked True
        self.assertIsInstance(fut_meals["breakfast"], dict, "Cooked breakfast should remain a dict")
        self.assertTrue(fut_meals["breakfast"].get("cooked"), "Cooked flag should be preserved")
        # Lunch (non cooked) should be reset to '-'
        self.assertEqual(fut_meals["lunch"], "-", "Non-cooked future meal should be reset")
        # Dinner should still be '-'
        self.assertEqual(fut_meals["dinner"], "-", "Dinner should remain reset")

        if past_day_name:
            past_meals = updated.meals[past_day_name]
            self.assertEqual(past_meals["lunch"], "Tomato Soup", "Past day meal should not be reset")

if __name__ == '__main__':
    unittest.main()

