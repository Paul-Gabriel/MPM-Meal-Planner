from fastapi import APIRouter, Response
from meal.infra.Recipe_Repository import reading_from_recipes
from meal.infra.paths import RECIPES_FILE
import json

router = APIRouter()

def load_recipes():
    with open(RECIPES_FILE, encoding='utf-8') as f:
        return json.load(f)

@router.get("/", response_class=Response)
def list_recipes():
    """Return all recipes, each on its own line, as text."""
    try:
        recipes = reading_from_recipes()
        if not recipes:
            return Response(content="No recipes found.", media_type="text/plain")
        lines = [repr(recipe) for recipe in recipes]
        return Response(content="\n".join(lines), media_type="text/plain")
    except Exception as e:
        return Response(content=f"Error reading recipes: {e}", media_type="text/plain")

# endpoint POST de test
@router.post("/")
def add_recipe(recipe: dict):
    return {"status": "ok", "recipe_added": recipe}
