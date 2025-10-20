import json
import logging
from meal.domain.Recipe import Recipe
from meal.infra.paths import RECIPES_FILE

logger = logging.getLogger(__name__)

def reading_from_recipes():
    """Read recipes from JSON file with proper error handling."""
    try:
        with open(RECIPES_FILE, 'r', encoding='utf-8') as f:
            recipes_data = json.load(f)
        recipes = [Recipe.from_dict(entry) for entry in recipes_data]
        return recipes
    except FileNotFoundError:
        logger.warning(f"Recipes file not found: {RECIPES_FILE}. Returning empty list.")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in recipes file: {e}")
        return []
    except Exception as e:
        logger.error(f"Error reading recipes: {e}")
        return []
