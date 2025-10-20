from pathlib import Path

# Centralized paths for data files (single source of truth)
DATA_DIR = (Path(__file__).parent.parent / 'data').resolve()
RECIPES_FILE = DATA_DIR / 'recipes.json'
PANTRY_FILE = DATA_DIR / 'Pantry_ingredients.json'
PLAN_FILE = DATA_DIR / 'plan.json'
COOKED_FILE = DATA_DIR / 'Pantry_recipe_cooked.json'
SHOPPING_TRANSACTIONS_FILE = DATA_DIR / 'shopping_transactions.json'

__all__ = ['DATA_DIR','RECIPES_FILE','PANTRY_FILE','PLAN_FILE','COOKED_FILE','SHOPPING_TRANSACTIONS_FILE']

