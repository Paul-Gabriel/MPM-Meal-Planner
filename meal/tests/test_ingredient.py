from datetime import date
import unittest
from meal.domain.Ingredient import Ingredient


class TestIngredient(unittest.TestCase):
    
    def test_set_quantity(self):
        ingredient = Ingredient("Sugar", "grams", 100, date.today())
        ingredient.set_quantity(50)
        self.assertEqual(ingredient.default_quantity, 150)
        ingredient.set_quantity(-30)
        self.assertEqual(ingredient.default_quantity, 120)
