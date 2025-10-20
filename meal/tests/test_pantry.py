from datetime import date
import unittest
from meal.domain.Ingredient import Ingredient
from meal.domain.Pantry import Pantry


class TestPantry(unittest.TestCase):

    def setUp(self):
        self.pantry = Pantry()
    
    def test_add_item(self):
        ingredient = Ingredient("Sugar", "grams", 100, date.today())
        self.pantry.add_item(ingredient)
        self.assertIn(ingredient, self.pantry.get_items())

    def test_remove_item(self):
        ingredient = Ingredient("Sugar", "grams", 100, date.today())
        self.pantry.add_item(ingredient)
        self.pantry.remove_item(ingredient)
        self.assertNotIn(ingredient, self.pantry.get_items())

    def test_get_items(self):
        ingredient1 = Ingredient("Sugar", "grams", 100, date.today())
        ingredient2 = Ingredient("Flour", "grams", 200, date.today())
        self.pantry.add_item(ingredient1)
        self.pantry.add_item(ingredient2)
        self.assertEqual(self.pantry.get_items(), [ingredient1, ingredient2])
