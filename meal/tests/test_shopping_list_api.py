import unittest
from fastapi.testclient import TestClient
from meal.api.api_run import app
from meal.infra.Plan_Repository import PlanRepository
from datetime import date

class TestShoppingListAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_api_shopping_list_basic(self):
        # Prepare plan for current ISO week (dynamic)
        iso = date.today().isocalendar()
        week = iso.week
        repo = PlanRepository()
        plan = repo.get_week_plan(week)

        # Reset plan meals for deterministic test context
        for day, meals in plan.meals.items():
            meals['breakfast'] = '-'
            meals['lunch'] = '-'
            meals['dinner'] = '-'

        days = list(plan.meals.keys())
        if len(days) >= 5:
            # If enough days, assign recipes across different slots
            plan.meals[days[0]]['lunch'] = 'Chicken Curry'
            plan.meals[days[1]]['breakfast'] = 'Vegetable Stir Fry'
            plan.meals[days[2]]['dinner'] = 'Chicken Curry'
            plan.meals[days[3]]['dinner'] = 'Spaghetti Bolognese'
            plan.meals[days[4]]['lunch'] = 'Chicken Curry'
        else:
            first = days[0]
            plan.meals[first]['breakfast'] = 'Vegetable Stir Fry'
            plan.meals[first]['lunch'] = 'Chicken Curry'
            plan.meals[first]['dinner'] = 'Chicken Curry'

        repo.save_week_plan(week, plan)

        # Fetch shopping list (no params -> current week)
        resp = self.client.get('/api/shopping-list')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('week', data)
        self.assertEqual(data['week'], week)
        self.assertIn('items', data)
        self.assertIn('count', data)
        items = data['items']
        if items:
            for it in items:
                for key in ('name','unit','required','have','missing'):
                    self.assertIn(key, it)
        # Bell pepper should appear as missing
        bell = [i for i in items if i['name'].lower() == 'bell pepper']
        self.assertTrue(bell, 'Bell pepper should be missing (not in pantry).')
        # Spaghetti should not appear (pantry has enough)
        spaghetti = [i for i in items if i['name'].lower() == 'spaghetti']
        self.assertFalse(spaghetti, 'Spaghetti should not be missing (pantry has enough).')
        # Potential future assertion: chicken breast deficit
