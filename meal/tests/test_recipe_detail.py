import unittest
from fastapi.testclient import TestClient
from meal.api.api_run import app

class TestRecipeDetail(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_recipe_detail_ok(self):
        resp = self.client.get('/recipe/Spaghetti%20Bolognese')
        self.assertEqual(resp.status_code, 200)
        body = resp.text
        # Basic content
        self.assertIn('Spaghetti Bolognese', body)
        self.assertIn('Servings', body)
        self.assertIn('Ingredients', body)
        self.assertIn('Steps', body)
        # Nutrition content (calories + macros chips)
        self.assertIn('Calories / serving:', body)
        self.assertIn('Protein', body)
        self.assertIn('Carbs', body)
        self.assertIn('Fats', body)

    def test_recipe_detail_not_found(self):
        resp = self.client.get('/recipe/ThisRecipeDoesNotExistXYZ')
        self.assertEqual(resp.status_code, 404)
        data = resp.json()
        self.assertEqual(data.get('detail'), 'Recipe not found')
