import unittest
from fastapi.testclient import TestClient
from meal.api.api_run import app

class TestAvailableRecipesTimesPossible(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_times_possible_fields(self):
        resp = self.client.get('/api/recipes/available')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        recipes = {r['name']: r for r in data.get('recipes', [])}
        # Ensure expected recipes exist
        self.assertIn('Pancakes', recipes)
        self.assertIn('Spaghetti Carbonara', recipes)
        # Ensure new field present
        self.assertIn('times_possible', recipes['Pancakes'])
        self.assertIn('times_possible', recipes['Spaghetti Carbonara'])
        # Pantry stock yields Pancakes min(Flour 800/200=4, Milk 700/300=2, Egg 12/2=6, Sugar 980/20=49) -> 2
        self.assertEqual(recipes['Pancakes']['times_possible'], 2)
        # Carbonara min(Spaghetti 500/400=1, Pancetta 150/150=1, Egg 12/3=4, Parmesan 200/50=4, Pepper 50/2=25) -> 1
        self.assertEqual(recipes['Spaghetti Carbonara']['times_possible'], 1)
        # Ensure that times_possible is non-negative integer for all
        for r in data.get('recipes', []):
            self.assertIsInstance(r.get('times_possible'), int)
            self.assertGreaterEqual(r.get('times_possible'), 0)

if __name__ == '__main__':
    unittest.main()

