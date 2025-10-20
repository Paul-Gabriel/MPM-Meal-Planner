"""Pantry repository helpers (file persistence)."""

import json
from datetime import datetime
from meal.domain.Pantry import Pantry
from meal.domain.Ingredient import Ingredient
from meal.infra.paths import PANTRY_FILE


def reading_from_ingredients():
    """Load pantry ingredients from JSON file and return Pantry aggregate (graceful error handling)."""
    try:
        with open(PANTRY_FILE, 'r', encoding='utf-8') as f:
            ingredient_data = json.load(f)
        pantry = Pantry()
        for entry in ingredient_data:
            if entry.get("data_expirare"):
                try:
                    entry["data_expirare"] = datetime.strptime(entry["data_expirare"], "%d-%m-%Y")
                except Exception:
                    entry["data_expirare"] = None
            ingredient = Ingredient.from_dict(entry)
            pantry.add_item(ingredient)
        return pantry
    except Exception as e:
        print(f"Error reading ingredients: {e}")
