from datetime import date
import unittest
from meal.domain.Ingredient import Ingredient
from meal.domain.Pantry import Pantry
from meal.domain.Recipe import Recipe
from meal.domain.RecipeCooked import RecipeCooked

class TestRecipe(unittest.TestCase):

    def setUp(self):
        self.recipe_pancakes = Recipe(
            name="Pancakes",
            servings=4,
            ingredients=[
                Ingredient("Flour", "grams", 200),
                Ingredient("Milk", "ml", 300),
                Ingredient("Eggs", "pieces", 2)
            ],
            steps=["Mix ingredients", "Cook on skillet"],
            tags=["breakfast", "vegetarian"],
            calories_per_serving=500
        )
        self.recipe_omelette = Recipe(
            name="Omelette",
            servings=2,
            ingredients=[
                Ingredient("Eggs", "pieces", 3),
                Ingredient("Cheese", "grams", 100)
            ],
            steps=["Beat eggs", "Cook with cheese"],
            tags=["breakfast", "vegetarian"],
            calories_per_serving=400
        )
        self.pantry = Pantry()
        self.pantry.add_item(Ingredient("Flour", "g", 200, date.today()))
        self.pantry.add_item(Ingredient("Milk", "ml", 300, date.today()))
        self.pantry.add_item(Ingredient("Eggs", "pcs", 2, date.today()))

    def test_check_ingredients(self):
        self.assertTrue(self.recipe_pancakes.check_ingredients(self.pantry.get_items()))
        self.assertFalse(self.recipe_omelette.check_ingredients(self.pantry.get_items()))

    def test_cook(self):
        recipe_cooked = self.recipe_pancakes.cook(self.pantry.get_items())
        self.assertTrue(recipe_cooked)
        recipe_cooked = self.recipe_omelette.cook(self.pantry.get_items())
        self.assertFalse(recipe_cooked)
