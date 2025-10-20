import unittest
from fastapi.testclient import TestClient
from meal.api.api_run import app

class TestAvailableRecipesAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_available_recipes_basic(self):
        resp = self.client.get('/api/recipes/available')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('count', data)
        self.assertIn('total', data)
        self.assertIn('recipes', data)
        names = {r['name'] for r in data['recipes']}
        # Expect at least Pancakes and Spaghetti Carbonara based on pantry stock
        self.assertIn('Pancakes', names)
        self.assertIn('Spaghetti Carbonara', names)
        # A recipe missing ingredients should not appear
        self.assertNotIn('Vegetable Stir Fry', names)
        # Count should be >= 2
        self.assertGreaterEqual(data['count'], 2)

if __name__ == '__main__':
    unittest.main()

