import json, os, tempfile, shutil
from fastapi import Form, UploadFile, File, APIRouter
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx
from fastapi import FastAPI
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Use configuration instead of hardcoded API key
try:
    from meal.utilities.config import SPOONACULAR_API_KEY
    API_KEY = SPOONACULAR_API_KEY
except ImportError:
    # Fallback for backwards compatibility
    API_KEY = "5ff4f96c305e44fd8a8bb9d94278e058"
    logger.warning("Using fallback API key. Consider using config.py for better security.")

# === Paths corecte ===
HERE = os.path.dirname(os.path.abspath(__file__))  # .../meal/api/routes
MEAL_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
STATIC_DIR = os.path.join(MEAL_DIR, "static")
PICTURES_DIR = os.path.join(STATIC_DIR, "pictures")
TEMPLATES_DIR = os.path.join(MEAL_DIR, "templates")
RECIPES_FILE = os.path.join(MEAL_DIR, "data", "recipes.json")

# Ensure pictures directory exists
os.makedirs(PICTURES_DIR, exist_ok=True)


# === Helperi pentru recipes.json ===
def _safe_load_recipes():
    if not os.path.exists(RECIPES_FILE):
        return []
    try:
        with open(RECIPES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def _atomic_write(recipes: list):
    os.makedirs(os.path.dirname(RECIPES_FILE), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(RECIPES_FILE), prefix=".recipes_", suffix=".json"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            json.dump(recipes, tmp, indent=2, ensure_ascii=False)
        shutil.move(tmp_path, RECIPES_FILE)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass


# === Rute frontend ===
@router.get("/add-recipe")
async def get_add_recipe():
    return FileResponse(os.path.join(TEMPLATES_DIR, "add_recipe.html"))


# === Save recipe with upload ===
@router.post("/recipes")
async def add_recipe(
    name: str = Form(...),
    servings: int = Form(...),
    ingredients: str = Form(...),  # trimis ca JSON string
    steps: str = Form(""),
    tags: str = Form(""),
    image: UploadFile = File(None)
):
    recipes = _safe_load_recipes()
    if any(r["name"].lower() == name.strip().lower() for r in recipes):
        return JSONResponse(status_code=400, content={"error": "Recipe with this name already exists"})

    # --- save image if provided ---
    image_filename = ""
    if image is not None:
        if not image.content_type.startswith("image/"):
            return JSONResponse(status_code=400, content={"error": "Invalid image type"})
        image_filename = image.filename
        file_path = os.path.join(PICTURES_DIR, image_filename)
        with open(file_path, "wb") as f:
            f.write(await image.read())

    # --- convert ingredients JSON string into list ---
    try:
        ingredients_obj = json.loads(ingredients)
    except:
        ingredients_obj = []

    # --- parse tags and steps ---
    steps_list = [s.strip() for s in steps.split("\n") if s.strip()]
    tags_list = [t.strip() for t in tags.split(",") if t.strip()]

    # --- prepare Spoonacular payload ---
    def _fmt_ing(ing):
        unit = ing.get("unit", "").strip()
        qty = ing.get("default_quantity", 0)
        name = ing.get("name", "").strip()
        return f"{qty}{unit} {name}".strip()

    spoonacular_ingredients = [_fmt_ing(ing) for ing in ingredients_obj]

    url = f"https://api.spoonacular.com/recipes/analyze?apiKey={API_KEY}&includeNutrition=true"
    payload = {
        "title": name,
        "servings": servings,
        "ingredients": spoonacular_ingredients
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        if response.status_code != 200:
            return JSONResponse(
                status_code=response.status_code,
                content={"error": response.text}
            )
        data = response.json()

    # --- extract macros ---
    macros = {}
    if "nutrition" in data and "nutrients" in data["nutrition"]:
        for n in data["nutrition"]["nutrients"]:
            if n["name"] in ["Calories", "Fat", "Carbohydrates", "Protein"]:
                macros[n["name"]] = round(float(n["amount"]), 2)

    recipe = {
        "name": name.strip(),
        "servings": servings,
        "ingredients": ingredients_obj,
        "steps": steps_list,
        "tags": tags_list,
        "image": image_filename,  # only file name
        "calories_per_serving": macros.get("Calories", 0),
        "macros": {
            "protein": macros.get("Protein", 0),
            "carbohydrates": macros.get("Carbohydrates", 0),
            "fats": macros.get("Fat", 0),
        },
    }

    # --- save to JSON ---
    recipes.append(recipe)
    _atomic_write(recipes)

    return {"status": "success", "saved_to": RECIPES_FILE, "recipe": recipe}


# === Debug ===
@router.get("/_debug/recipes-path")
def dbg_path():
    return {"recipes_file": RECIPES_FILE}


@router.get("/_debug/recipes")
def dbg_recipes():
    return _safe_load_recipes()


# === Static mount ===
app = FastAPI(title="Add Recipe Module")
app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
