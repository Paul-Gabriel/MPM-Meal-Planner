import unittest
from datetime import date, timedelta
from meal.infra.Plan_Repository import PlanRepository

class TestRandomizeUniqueness(unittest.TestCase):
    def _find_future_week(self):
        today = date.today()
        # Try up to 10 weeks ahead
        year = today.isocalendar().year
        week = today.isocalendar().week
        for add in range(1, 10):
            # compute monday of candidate week
            candidate_week = week + add
            candidate_year = year
            # Adjust year/week rollover (ISO weeks can be 52 or 53)
            # We'll brute-force by trying to construct date until success
            for adjust in range(0, 3):  # small attempts
                try:
                    monday = date.fromisocalendar(candidate_year, candidate_week, 1)
                    if monday > today:
                        return candidate_week, candidate_year
                    break
                except ValueError:
                    # rollover to next year
                    candidate_week -= 52
                    candidate_year += 1
        # Fallback: just return current week (tests may skip if not future)
        return week, year

    def test_randomize_week_uniqueness(self):
        repo = PlanRepository()
        future_week, future_year = self._find_future_week()
        plan = repo.get_week_plan(future_week, future_year)
        # Force placeholders so all three slots attempt assignment
        for day, meals in plan.meals.items():
            meals['breakfast'] = '-'
            meals['lunch'] = '-'
            meals['dinner'] = '-'
        repo.save_week_plan(future_week, plan, future_year)
        repo.randomize_week(future_week, future_year)
        updated = repo.get_week_plan(future_week, future_year)
        for day, meals in updated.meals.items():
            names = []
            for slot in ('breakfast','lunch','dinner'):
                v = meals.get(slot)
                if isinstance(v, str) and v not in ('-', '', None):
                    names.append(v)
            # Ensure uniqueness among assigned names
            self.assertEqual(len(names), len(set(names)), f"Duplicate recipe in day {day}: {names}")

    def test_randomize_custom_uniqueness(self):
        repo = PlanRepository()
        future_week, future_year = self._find_future_week()
        plan = repo.get_week_plan(future_week, future_year)
        # Pick first day (Monday) which is surely in the future for future_week
        target_day = 'Monday'
        # Intentionally set duplicates to ensure replacement logic works
        plan.meals[target_day]['breakfast'] = 'Spaghetti Bolognese'
        plan.meals[target_day]['lunch'] = 'Spaghetti Bolognese'
        plan.meals[target_day]['dinner'] = 'Spaghetti Bolognese'
        repo.save_week_plan(future_week, plan, future_year)
        repo.randomize_custom(future_week, future_year, days=[target_day], replace_existing=True)
        updated = repo.get_week_plan(future_week, future_year)
        meals = updated.meals[target_day]
        assigned = [meals[s] for s in ('breakfast','lunch','dinner') if isinstance(meals.get(s), str) and meals.get(s) not in ('-','',None)]
        self.assertEqual(len(assigned), len(set(assigned)), f"Duplicate after custom randomize: {assigned}")

if __name__ == '__main__':
    unittest.main()

