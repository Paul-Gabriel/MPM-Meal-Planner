from fastapi import (
    FastAPI,
    Request,
    Query,
    Form,
    APIRouter,
    HTTPException,
    Response,
    Body
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pathlib import Path
from pydantic import BaseModel
from datetime import datetime, timedelta, date as _date
from uuid import uuid4
from typing import Optional
import logging
import json

from meal.infra.pdf_utils import generate_pdf_for_week
from meal.logic.reporting.nutrition import compute_week_nutrition  # moved from services.Reporting_Service
from meal.logic.pantry.analysis import compute_pantry_snapshots   # moved from services.pantry_analysis
from meal.infra.Plan_Repository import PlanRepository
from meal.api.routes.recipes import load_recipes
from meal.api.routes.pantry import load_ingredients, save_ingredients
from meal.api.routes.logs import load_cooked_recipes, save_cooked_recipes
from meal.logic.shopping.list_builder import build_shopping_list   # moved from rules.Shopping_List_Builder
from meal.utilities.constants import DATE_FORMAT, LOW_STOCK_THRESHOLD, DAYS_BEFORE_EXPIRY
from meal.events.event_helpers import (
    publish_expiring_snapshot,
    publish_low_stock,
    publish_near_expiry
)
from meal.events.web_observers import start as start_event_observers, get_events as get_web_events

# Routers
from meal.api.routes import add
from meal.api.api_ai import router as ai_router
from dotenv import load_dotenv
load_dotenv()

# Logging
logger = logging.getLogger("meal_app")

# Constants
ALLOWED_START = _date(2025, 9, 1)
ALLOWED_END = _date(2026, 12, 31)
DEFAULT_EXP_DELTA_DAYS = 7  # default extra days for new bought ingredient expiration

DAY_TO_ISO = {
    "Monday": 1,
    "Tuesday": 2,
    "Wednesday": 3,
    "Thursday": 4,
    "Friday": 5,
    "Saturday": 6,
    "Sunday": 7,
}

# Detect multipart support
try:
    import multipart  # noqa: F401
    _HAS_MULTIPART = True
except Exception:
    _HAS_MULTIPART = False
    logger.warning("python-multipart not available; /update_meal will accept JSON body instead of form-data.")

# Initialize FastAPI app
app = FastAPI(title="Meal Planner & Pantry API")
router = APIRouter()

# Include routers
app.include_router(add.router)
app.include_router(ai_router)

# Static files
static_dir = (Path(__file__).parent.parent / 'static').resolve()
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates_dir = (Path(__file__).parent.parent / 'templates').resolve()
templates = Jinja2Templates(directory=str(templates_dir))



@app.on_event("startup")
def _startup_web_observers():
    """Register event bus subscribers for web alerts when the app starts."""
    try:
        start_event_observers()
        logger.info("Web observers for pantry events started")
    except Exception as e:  # pragma: no cover - defensive
        logger.error("Failed to start web observers: %s", e)

def _ts() -> int:
    """Cache-busting timestamp for static assets."""
    return int(datetime.now().timestamp())

# -------------------- Helpers --------------------
def gen_weeks(first_monday: _date, count: int = 12):
    """Generate a list of weeks (start/end/label/is_current) for the custom dropdown."""
    today = _date.today()
    weeks = []
    for i in range(count):
        start = first_monday + timedelta(weeks=i)
        end = start + timedelta(days=6)
        weeks.append({
            "start": start,
            "end": end,
            "label": f"{start.strftime('%-m/%-d/%Y')} - {end.strftime('%-m/%-d/%Y')}",
            "is_current": start <= today <= end,
        })
    return weeks

# -------------------- UI PAGES --------------------
@app.get("/", response_class=HTMLResponse)
def main_page(request: Request, week: Optional[int] = Query(default=None), year: Optional[int] = Query(default=None), notice: Optional[str] = Query(default=None), chg: Optional[int] = Query(default=None)):
    if week is None or year is None:
        today = _date.today()
        iso = today.isocalendar()
        week, year = iso.week, iso.year

    repo = PlanRepository()
    plan = repo.get_week_plan(week, year)

    recipes = load_recipes()

    # Expiring soon (<= DAYS_BEFORE_EXPIRY days)
    expiring_window = DAYS_BEFORE_EXPIRY
    expiring_soon = []
    low_stock_items = []
    try:
        ingredients_home = load_ingredients()
        expiring_soon, low_stock_items = compute_pantry_snapshots(ingredients_home, window=expiring_window)
    except Exception:
        expiring_soon, low_stock_items = [], []

    nutrition = compute_week_nutrition(plan, recipes)

    notice_map = {
        "reset": "Week has been changed to default.",
        "random": "Week has been randomized.",
    }
    notice_message = notice_map.get(notice)
    if notice_message and chg is not None:
        notice_message = f"{notice_message} (Changed slots: {chg})"
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "plan": plan,
            "recipes": recipes,
            "expiring_soon": expiring_soon,
            "low_stock_items": low_stock_items,
            "time": _ts(),
            "expiring_window": expiring_window,
            "nutrition": nutrition,
            "current_date": _date.today().strftime("%d.%m.%Y"),  # added for Cook panel visibility condition
            "notice_message": notice_message,
        }
    )

@app.get("/meal-plan/{week}", response_class=HTMLResponse)
def meal_plan(request: Request, week: int):
    repo = PlanRepository()
    plan = repo.get_week_plan(week)
    recipes = load_recipes()
    nutrition = compute_week_nutrition(plan, recipes)

    # Mirror expiring_soon logic as on home page
    expiring_window = DAYS_BEFORE_EXPIRY
    expiring_soon = []
    low_stock_items = []
    try:
        ingredients_home = load_ingredients()
        expiring_soon, low_stock_items = compute_pantry_snapshots(ingredients_home, window=expiring_window)
    except Exception:
        expiring_soon, low_stock_items = [], []

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "plan": plan,
            "recipes": recipes,
            "expiring_soon": expiring_soon,
            "low_stock_items": low_stock_items,
            "time": _ts(),
            "expiring_window": expiring_window,
            "current_date": _date.today().strftime("%d.%m.%Y"),
            "nutrition": nutrition,
        }
    )

@app.get("/shopping-list", response_class=HTMLResponse)
def shopping_list_page(request: Request,
                       week: Optional[int] = Query(default=None),
                       year: Optional[int] = Query(default=None),
                       include_past: Optional[int] = Query(default=None)):
    # Determine current iso week/year if missing
    if week is None or year is None:
        today_iso = _date.today().isocalendar()
        week = today_iso.week if week is None else week
        year = today_iso.year if year is None else year

    repo = PlanRepository()
    plan = repo.get_week_plan(week, year)
    recipes = load_recipes()
    pantry = load_ingredients()

    # Exclude past days only for current ISO week unless include_past=1 provided
    current_iso = _date.today().isocalendar()
    skip_past = (week == current_iso.week and year == current_iso.year and (not include_past or int(include_past) == 0))

    shopping_list = build_shopping_list(plan, recipes, pantry) if not skip_past \
        else build_shopping_list(plan, recipes, pantry, skip_past_days=True)

    total_items = len(shopping_list)
    default_exp_date = (datetime.now() + timedelta(days=7)).strftime(DATE_FORMAT)
    default_exp_date_iso = datetime.strptime(default_exp_date, DATE_FORMAT).strftime('%Y-%m-%d')

    return templates.TemplateResponse(
        "shopping_list.html",
        {
            "request": request,
            "shopping_list": shopping_list,
            "week": week,
            "year": year,
            "total_items": total_items,
            "default_exp_date": default_exp_date,
            "default_exp_date_iso": default_exp_date_iso,
            "time": _ts(),
            "excluded_past_days": skip_past
        }
    )

# NEW: Recipe detail page
@app.get("/recipe/{recipe_name}", response_class=HTMLResponse)
def recipe_detail(request: Request, recipe_name: str):
    recipes = load_recipes()
    target = None
    for r in recipes:
        if r.get('name', '').lower() == recipe_name.lower():
            target = r
            break
    if not target:
        raise HTTPException(status_code=404, detail="Recipe not found")

    formatted_ingredients = [
        {
            "name": i.get('name', ''),
            "quantity": i.get('default_quantity', ''),
            "unit": i.get('unit', '')
        } for i in target.get('ingredients', [])
    ]

    # Nutrition (graceful fallbacks)
    calories = target.get('calories_per_serving') or target.get('caloriesPerServing')
    macros_raw = target.get('macros', {}) or {}
    macros = {
        'protein': macros_raw.get('protein', 0),
        'carbs': macros_raw.get('carbs', macros_raw.get('carbohydrates', 0)),
        'fats': macros_raw.get('fats', macros_raw.get('fat', 0)),
    }

    return templates.TemplateResponse(
        "recipe_detail.html",
        {
            "request": request,
            "recipe": target,
            "ingredients": formatted_ingredients,
            "steps": target.get('steps', []),
            "tags": target.get('tags', []),
            "calories": calories,
            "macros": macros,
            "time": _ts()
        }
    )

# -------------------- Update meal (supports form OR JSON) --------------------
class MealUpdate(BaseModel):
    day: str
    meal: str
    recipe: str
    week: int
    year: int

if _HAS_MULTIPART:
    @app.post("/update_meal")
    def update_meal(
        day: str = Form(...),
        meal: str = Form(...),
        recipe: str = Form(...),
        week: int = Form(...),
        year: int = Form(...)
    ):
        repo = PlanRepository()
        plan = repo.get_week_plan(week, year)
        if day not in plan.meals or meal not in plan.meals[day]:
            raise HTTPException(status_code=400, detail="Invalid day or meal")
        plan.meals[day][meal] = recipe
        repo.save_week_plan(week, plan, year)
        return RedirectResponse(url="/", status_code=303)
else:
    @app.post("/update_meal")
    def update_meal(payload: MealUpdate):  # type: ignore
        repo = PlanRepository()
        plan = repo.get_week_plan(payload.week, payload.year)
        if payload.day not in plan.meals or payload.meal not in plan.meals[payload.day]:
            raise HTTPException(status_code=400, detail="Invalid day or meal")
        plan.meals[payload.day][payload.meal] = payload.recipe
        repo.save_week_plan(payload.week, plan, payload.year)
        return RedirectResponse(url="/", status_code=303)

# -------------------- Recipes list page --------------------
@app.get("/recipes-page", response_class=HTMLResponse)
def recipes_page(request: Request, tag: str = Query(default="", alias="tag")):
    recipes = load_recipes()

    # colectăm toate tag-urile pentru dropdown
    all_tags = set()
    for r in recipes:
        all_tags.update(r.get('tags', []))
    tags = sorted(all_tags)

    # aplicăm filtrarea dacă e selectat un tag
    filtered = [r for r in recipes if tag in r.get('tags', [])] if tag else recipes

    recipe_dicts = []
    for r in filtered:
        # --- Ingrediente formatate ---
        ingredients = r.get('ingredients', [])
        formatted_ingredients = [
            f"{i.get('name', '')}, {i.get('default_quantity', '')} {i.get('unit', '')}".strip(", ")
            for i in ingredients
        ]

        # --- Imagine ---
        image_name = r.get('image') or (r.get('name', '').lower().replace(' ', '_') + '.jpg')

        # --- Calorii + Macronutrienți ---
        calories = r.get('calories_per_serving') or r.get('caloriesPerServing') or None
        macros_raw = r.get('macros', {}) or {}

        macros = {
            "protein": macros_raw.get("protein", 0),
            "carbohydrates": macros_raw.get("carbohydrates", macros_raw.get("carbs", 0)),
            "fats": macros_raw.get("fats", macros_raw.get("fat", 0)),
        }

        # --- Construcția finală a dicționarului ---
        recipe_dicts.append({
            "name": r.get('name', ''),
            "servings": r.get('servings', ''),
            "ingredients": formatted_ingredients,
            "image": image_name,
            "tags": r.get('tags', []),
            "calories_per_serving": calories,
            "macros": macros,
        })

    # --- Returnăm template-ul complet ---
    return templates.TemplateResponse(
        "recipes.html",
        {
            "request": request,
            "recipes": recipe_dicts,
            "tags": tags,
            "selected_tag": tag,
            "time": _ts()
        }
    )


# -------------------- Camara (pantry) --------------------
@app.get("/camara", response_class=HTMLResponse)
def camara_page(request: Request):
    ingredients = load_ingredients()
    cooked_recipes = load_cooked_recipes()
    expiring_soon, low_stock_items = compute_pantry_snapshots(ingredients, window=DAYS_BEFORE_EXPIRY)
    try:
        publish_expiring_snapshot(expiring_soon)
    except Exception:
        pass
    return templates.TemplateResponse(
        "camara.html",
        {"request": request, "ingredients": ingredients, "cooked_recipes": cooked_recipes,
         "expiring_soon": expiring_soon, "low_stock_items": low_stock_items, "time": _ts(),
         "expiring_window": DAYS_BEFORE_EXPIRY}
    )

@app.get("/pantry", response_class=HTMLResponse)
def pantry_page_alias(request: Request):
    # Alias for English route; reuse the same view
    return camara_page(request)

@app.get("/camara/edit", response_class=HTMLResponse)
def camara_edit_page(request: Request):
    ingredients = load_ingredients()
    cooked_recipes = load_cooked_recipes()
    return templates.TemplateResponse(
        "edit_pantry.html",
        {
            "request": request,
            "ingredients": ingredients,
            "cooked_recipes": cooked_recipes,
            "time": _ts()
        }
    )

@app.get("/pantry/edit", response_class=HTMLResponse)
def pantry_edit_page_alias(request: Request):
    # Alias for English route; reuse the same view
    return camara_edit_page(request)

# -------------------- API: Pantry Alerts (polled by frontend) --------------------
@app.get('/api/pantry/alerts')
def api_pantry_alerts(
    since: Optional[int] = Query(default=None, description="Return events with id greater than this value")
):
    """
    Return recent pantry alert events (low stock, near expiry).

    Client polling strategy:
        1. First call without 'since' to load current backlog (optional).
        2. Store 'next_cursor' from response.
        3. Subsequent polls: /api/pantry/alerts?since=<next_cursor>
    """
    if since is None:
        snapshot = get_web_events(None)
        if not snapshot['events']:
            try:
                ingredients = load_ingredients()
                today = _date.today()
                for ing in ingredients:
                    try:
                        q = int(ing.get('default_quantity') or 0)
                    except Exception:
                        q = 0
                    unit = ing.get('unit','')
                    th = LOW_STOCK_THRESHOLD.get(unit, 0)
                    if q <= th:
                        publish_low_stock(ing, q, th)
                    exp_str = ing.get('data_expirare')
                    if exp_str:
                        try:
                            exp_date = datetime.strptime(exp_str, DATE_FORMAT).date()
                            days_left = (exp_date - today).days
                            if days_left <= DAYS_BEFORE_EXPIRY:
                                publish_near_expiry(ing, days_left, DAYS_BEFORE_EXPIRY)
                        except Exception:
                            pass
                snapshot = get_web_events(None)
            except Exception:
                pass
            return snapshot
        return snapshot
    return get_web_events(since)

# -------------------- API: Pantry Ingredients --------------------
@router.post('/api/pantry/ingredient')
def add_ingredient(data: dict):
    ingredients = load_ingredients()
    if any(i['name'] == data['name'] for i in ingredients):
        raise HTTPException(status_code=400, detail='Ingredient already exists')
    ingredients.append(data)
    save_ingredients(ingredients)
    return {"success": True}

@router.put('/api/pantry/ingredient/{name}')
def edit_ingredient(name: str, data: dict):
    ingredients = load_ingredients()
    new_name = data.get('name')
    if new_name != name and any(i['name'] == new_name for i in ingredients):
        raise HTTPException(status_code=400, detail='Another ingredient with this name already exists')
    for i, ingr in enumerate(ingredients):
        if ingr['name'] == name:
            ingredients[i] = data
            save_ingredients(ingredients)
            return {"success": True}
    raise HTTPException(status_code=404, detail='Ingredient not found')

@router.delete('/api/pantry/ingredient/{name}')
def delete_ingredient(name: str):
    ingredients = load_ingredients()
    new_ingredients = [i for i in ingredients if i['name'] != name]
    if len(new_ingredients) == len(ingredients):
        raise HTTPException(status_code=404, detail='Ingredient not found')
    save_ingredients(new_ingredients)
    return {"success": True}

class BulkDeleteRequest(BaseModel):
    names: list[str]

@router.post('/api/pantry/ingredients/bulk-delete')
def bulk_delete_ingredients(payload: BulkDeleteRequest):
    """Delete multiple ingredients by name. Returns lists of deleted and not_found."""
    if not payload.names:
        return {"deleted": [], "not_found": [], "total_deleted": 0}
    ingredients = load_ingredients()
    name_set = set(payload.names)
    deleted = []
    remaining = []
    for ing in ingredients:
        if ing.get('name') in name_set:
            deleted.append(ing.get('name'))
        else:
            remaining.append(ing)
    not_found = [n for n in payload.names if n not in deleted]
    if deleted:
        save_ingredients(remaining)
    return {"deleted": deleted, "not_found": not_found, "total_deleted": len(deleted)}

# -------------------- API: Cooked Recipes --------------------
@router.post('/api/pantry/cooked')
def add_cooked(data: dict):
    cooked = load_cooked_recipes()
    if any(c['name'] == data.get('name') and c['date_cooked'] == data.get('date_cooked') for c in cooked):
        raise HTTPException(status_code=400, detail='Cooked recipe with same name and date already exists')
    cooked.append(data)
    save_cooked_recipes(cooked)
    return {"success": True}

@router.put('/api/pantry/cooked/{name}')
def edit_cooked(name: str, data: dict):
    cooked = load_cooked_recipes()
    new_name = data.get('name')
    if new_name != name and any(c['name'] == new_name for c in cooked):
        raise HTTPException(status_code=400, detail='Another cooked recipe with this name already exists')
    for i, rec in enumerate(cooked):
        if rec['name'] == name:
            cooked[i] = data
            save_cooked_recipes(cooked)
            return {"success": True}
    raise HTTPException(status_code=404, detail='Cooked recipe not found')

@router.delete('/api/pantry/cooked/{name}')
def delete_cooked(name: str):
    cooked = load_cooked_recipes()
    new_cooked = [c for c in cooked if c['name'] != name]
    if len(new_cooked) == len(cooked):
        raise HTTPException(status_code=404, detail='Cooked recipe not found')
    save_cooked_recipes(new_cooked)
    return {"success": True}

# Register router
app.include_router(router)

# Remove direct include that caused AttributeError; add safe wrapper
try:
    from fastapi import FastAPI as _FastAPI  # type: ignore
    _add_router = getattr(add, 'router', None)
    if _add_router and hasattr(_add_router, 'routes') and hasattr(_add_router, 'include_router'):
        app.include_router(_add_router)
except Exception:
    pass

# -------------------- API: Recipes availability (pantry has all ingredients) --------------------
@app.get('/api/recipes/available')
def api_recipes_available():
    """Return list of recipes for which pantry currently has all required ingredient quantities.

    Response JSON structure:
        {
          "count": <int>,
          "total": <int>,
          "recipes": [ { name, servings, calories, tags, times_possible } ]
        }
    """
    try:
        from meal.api.routes.recipes import load_recipes
        from meal.api.routes.pantry import load_ingredients
        from meal.domain.Recipe import Recipe  # for _normalize_name helper
    except Exception as e:  # pragma: no cover - defensive import
        raise HTTPException(status_code=500, detail=f"Import failure: {e}")

    try:
        recipes = load_recipes()  # list[dict]
        pantry = load_ingredients()  # list[dict]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data load error: {e}")

    # Build stock map (normalized name -> total quantity)
    stock: dict[str, int] = {}
    for ing in pantry:
        name = ing.get('name', '')
        qty = ing.get('default_quantity', 0)
        try:
            qty_int = int(qty)
        except Exception:
            qty_int = 0
        norm = Recipe._normalize_name(name) if hasattr(Recipe, '_normalize_name') else name.strip().lower()
        stock[norm] = stock.get(norm, 0) + qty_int

    def has_all_and_times(recipe: dict) -> tuple[bool, int]:
        times_min = None
        for ing in recipe.get('ingredients', []):
            rname = ing.get('name', '')
            required = ing.get('default_quantity', 0)
            try:
                required_int = int(required)
            except Exception:
                required_int = 0
            if required_int <= 0:
                # skip zero/invalid requirement so it doesn't affect calculation
                continue
            norm_r = Recipe._normalize_name(rname) if hasattr(Recipe, '_normalize_name') else rname.strip().lower()
            avail_qty = stock.get(norm_r, 0)
            if avail_qty < required_int:
                return False, 0
            possible_here = avail_qty // required_int if required_int else 0
            times_min = possible_here if times_min is None else min(times_min, possible_here)
        # If recipe has no ingredients times_min can default to 0 -> set to 0
        return True, (times_min if times_min is not None else 0)

    available = []
    for r in recipes:
        ok, times_possible = has_all_and_times(r)
        if ok:
            available.append({
                'name': r.get('name'),
                'servings': r.get('servings'),
                'calories': r.get('calories_per_serving') or r.get('caloriesPerServing'),
                'tags': r.get('tags', []),  # keep for backward compatibility (UI may ignore)
                'times_possible': times_possible
            })

    return {
        'count': len(available),
        'total': len(recipes),
        'recipes': available
    }

# -------------------- API: Shopping List (JSON) --------------------
@app.get('/api/shopping-list')
@app.get('/api/shopping-list/')
def api_shopping_list(week: Optional[int] = Query(default=None),
                      year: Optional[int] = Query(default=None),
                      skip_past: Optional[int] = Query(default=None)):
    if week is None or year is None:
        iso = _date.today().isocalendar()
        week = iso.week if week is None else week
        year = iso.year if year is None else year
    repo = PlanRepository()
    plan = repo.get_week_plan(week, year)
    recipes = load_recipes()
    pantry = load_ingredients()
    current_iso = _date.today().isocalendar()
    apply_skip = (skip_past is not None and int(skip_past) == 1 and week == current_iso.week and year == current_iso.year)
    items = build_shopping_list(plan, recipes, pantry, skip_past_days=True) if apply_skip else build_shopping_list(plan, recipes, pantry)
    return {"week": week, "year": year, "items": items, "count": len(items), "skipped_past_days": apply_skip}

@app.get('/api/shopping-list/current')
@app.get('/api/shopping-list/current/')
def api_shopping_list_current(skip_past: Optional[int] = Query(default=None)):
    iso = _date.today().isocalendar()
    week, year = iso.week, iso.year
    repo = PlanRepository()
    plan = repo.get_week_plan(week, year)
    recipes = load_recipes()
    pantry = load_ingredients()
    apply_skip = (skip_past is not None and int(skip_past) == 1)
    items = build_shopping_list(plan, recipes, pantry, skip_past_days=True) if apply_skip else build_shopping_list(plan, recipes, pantry)
    return {"week": week, "year": year, "items": items, "count": len(items), "skipped_past_days": apply_skip}

TRANSACTIONS_FILE = (Path(__file__).parent.parent / 'data' / 'shopping_transactions.json').resolve()

def _load_transactions():
    if TRANSACTIONS_FILE.exists():
        try:
            with open(TRANSACTIONS_FILE, encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception as e:
            logger.error("Failed to load transactions: %s", e)
    return []

def _save_transactions(transactions):
    try:
        with open(TRANSACTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(transactions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Failed to save transactions: %s", e)

@app.post('/api/shopping-list/buy')
@app.post('/api/shopping-list/buy/')
async def api_shopping_list_buy(payload: dict):
    week = payload.get('week', 39)
    items_to_buy = payload.get('items', []) or []
    if not isinstance(items_to_buy, list):
        raise HTTPException(status_code=400, detail="'items' must be a list")
    logger.info("ShoppingList BUY request week=%s items=%s", week, items_to_buy)

    plan = PlanRepository().get_week_plan(week)
    recipes = load_recipes()
    pantry = load_ingredients()
    shopping_list = build_shopping_list(plan, recipes, pantry)
    sl_index = {i['name'].lower(): i for i in shopping_list}

    def _norm(n: str): return (n or '').strip().lower().rstrip('.')
    def _stem(word: str):
        if word.endswith('ies') and len(word) > 3: return word[:-3] + 'y'
        if word.endswith('oes') and len(word) > 3: return word[:-3] + 'o'
        if word.endswith('ses') and len(word) > 3: return word[:-2]
        if word.endswith('es') and len(word) > 2 and word[-3] not in 'aeiou': return word[:-2]
        if word.endswith('s') and not word.endswith('ss') and len(word) > 1: return word[:-1]
        return word
    def _key(n: str): return _stem(_norm(n))

    def categorize(name: str) -> str:
        n = _norm(name)
        mapping = [
            ('chicken', 'meat-chicken'), ('ground beef', 'meat-beef'), ('beef', 'meat-beef'), ('pork','meat-pork'),
            ('pancetta','meat-pork'), ('fish','fish'), ('salmon','fish'), ('tuna','fish'), ('shrimp','seafood'),
            ('garlic','vegetables'), ('onion','vegetables'), ('pepper','vegetables'), ('carrot','vegetables'),
            ('broccoli','vegetables'), ('cabbage','vegetables'), ('tomato','vegetables'), ('potato','vegetables'),
            ('lettuce','vegetables'), ('cucumber','vegetables'), ('basil','spice'), ('oregano','spice'),
            ('paprika','spice'), ('cumin','spice'), ('cinnamon','spice'), ('salt','spice'), ('pepper','spice'),
            ('rice','grains'), ('spaghetti','pasta'), ('pasta','pasta'), ('flour','baking'), ('yeast','baking'),
            ('baking powder','baking'), ('milk','dairy'), ('cheese','dairy'), ('butter','dairy'), ('parmesan','dairy'),
            ('egg','dairy'), ('eggs','dairy'), ('oil','oil'), ('olive oil','oil'), ('sauce','sauce'),
            ('soy sauce','sauce'), ('dressing','sauce'), ('beans','canned'), ('canned','canned'), ('stock','canned'),
            ('sugar','baking')
        ]
        for frag, tag in mapping:
            if frag in n:
                return tag
        return 'other'

    today = datetime.now()
    updated, added, skipped = [], [], []
    transaction_id = str(uuid4())
    transaction = {
        'id': transaction_id,
        'timestamp': datetime.now().isoformat(),
        'week': week,
        'merged': [],
        'added': []
    }

    def parse_existing_exp(exp_str: str):
        return exp_str.strip() if exp_str else ''

    pantry_index_same_date = {}
    for idx, p in enumerate(pantry):
        name_key = _key(p.get('name',''))
        exp = parse_existing_exp(p.get('data_expirare',''))
        pantry_index_same_date.setdefault((name_key, exp), []).append((idx, p))

    for raw in items_to_buy:
        if isinstance(raw, dict):
            raw_name = raw.get('name')
            desired_qty = raw.get('quantity')
            exp_date_input = raw.get('exp_date') or raw.get('expiration') or raw.get('data_expirare')
        else:
            raw_name = raw
            desired_qty = None
            exp_date_input = None

        if not isinstance(raw_name, str):
            skipped.append({'name': raw_name, 'reason': 'not a string'})
            continue

        lookup = sl_index.get(raw_name.lower())
        if not lookup:
            candidates = [v for k, v in sl_index.items() if _key(k) == _key(raw_name)]
            lookup = candidates[0] if candidates else None
        if not lookup:
            skipped.append({'name': raw_name, 'reason': 'not in shopping list'})
            continue

        missing_qty = int(lookup['missing'])
        if missing_qty <= 0:
            skipped.append({'name': raw_name, 'reason': 'nothing missing'})
            continue

        if desired_qty is not None:
            try:
                desired_qty = int(desired_qty)
                if desired_qty <= 0:
                    skipped.append({'name': raw_name, 'reason': 'non-positive quantity ignored'})
                    continue
                qty_to_add = desired_qty
            except Exception:
                qty_to_add = missing_qty
        else:
            qty_to_add = missing_qty

        if exp_date_input:
            exp_date_str = None
            for fmt in (DATE_FORMAT, '%Y-%m-%d', '%d.%m.%Y'):
                try:
                    exp_date_str = datetime.strptime(exp_date_input, fmt).strftime(DATE_FORMAT)
                    break
                except Exception:
                    continue
            if not exp_date_str:
                exp_date_str = (today + timedelta(days=DEFAULT_EXP_DELTA_DAYS)).strftime(DATE_FORMAT)
        else:
            exp_date_str = (today + timedelta(days=DEFAULT_EXP_DELTA_DAYS)).strftime(DATE_FORMAT)

        k = _key(lookup['name'])
        merge_candidates = pantry_index_same_date.get((k, exp_date_str), [])
        if merge_candidates:
            idx, target = merge_candidates[0]
            prev_q = int(target.get('default_quantity') or 0)
            target['default_quantity'] = prev_q + qty_to_add
            updated.append({'name': target.get('name'), 'added': qty_to_add, 'new_total': target['default_quantity'], 'exp_date': exp_date_str})
            transaction['merged'].append({'index': idx, 'name': target.get('name'), 'prev_quantity': prev_q, 'added': qty_to_add, 'exp_date': exp_date_str})
        else:
            new_item = {
                'name': lookup['name'],
                'default_quantity': qty_to_add,
                'unit': lookup.get('unit',''),
                'data_expirare': exp_date_str,
                'tags': [categorize(lookup['name'])],
                'batch_id': transaction_id
            }
            pantry.append(new_item)
            added.append({'name': new_item['name'], 'quantity': qty_to_add, 'exp_date': exp_date_str})
            transaction['added'].append({'name': new_item['name'], 'quantity': qty_to_add, 'exp_date': exp_date_str})
            pantry_index_same_date.setdefault((k, exp_date_str), []).append((len(pantry)-1, new_item))

    if updated or added:
        save_ingredients(pantry)
        txs = _load_transactions()
        txs.append(transaction)
        _save_transactions(txs)

    new_shopping = build_shopping_list(plan, recipes, load_ingredients())
    return {
        'week': week,
        'transaction_id': transaction_id,
        'updated': updated,
        'added': added,
        'skipped': skipped,
        'remaining_count': len(new_shopping),
        'remaining_items': new_shopping
    }

@app.get('/api/shopping-list/undo/status')
@app.get('/api/shopping-list/undo/status/')
def shopping_undo_status():
    txs = _load_transactions()
    if not txs:
        return {'available': False, 'count': 0}
    last = txs[-1]
    return {'available': True, 'count': len(txs), 'last_id': last.get('id'), 'last_timestamp': last.get('timestamp')}

@app.post('/api/shopping-list/undo')
@app.post('/api/shopping-list/undo/')
async def shopping_undo():
    txs = _load_transactions()
    if not txs:
        raise HTTPException(status_code=400, detail='No transaction to undo')
    last = txs.pop()
    pantry = load_ingredients()

    for m in reversed(last.get('merged', [])):
        idx = m.get('index')
        if isinstance(idx, int) and 0 <= idx < len(pantry):
            prev_q = m.get('prev_quantity')
            if prev_q is not None:
                pantry[idx]['default_quantity'] = prev_q

    batch_id = last.get('id')
    if batch_id:
        pantry = [p for p in pantry if p.get('batch_id') != batch_id]

    save_ingredients(pantry)
    _save_transactions(txs)

    plan = PlanRepository().get_week_plan(last.get('week', 39))
    recipes = load_recipes()
    shopping_list = build_shopping_list(plan, recipes, pantry)
    return {'undone': True, 'remaining_transactions': len(txs), 'shopping_items': shopping_list, 'count': len(shopping_list)}

# -------------------- API: Nutrition --------------------
@app.get('/api/nutrition')
def api_nutrition(week: Optional[int] = Query(default=None), year: Optional[int] = Query(default=None)):
    """Return current nutrition aggregation for the given (week, year)."""
    if week is None or year is None:
        iso = _date.today().isocalendar()
        week = iso.week if week is None else week
        year = iso.year if year is None else year
    repo = PlanRepository()
    plan = repo.get_week_plan(week, year)
    recipes = load_recipes()
    nutrition = compute_week_nutrition(plan, recipes)
    return {"week": week, "year": year, **nutrition}

# -------------------- AJAX: get_week + partial --------------------
@app.get("/get_week")
def get_week(start: str = Query(..., description="Start date (Monday)")):
    # 1) parse
    start_date = None
    for fmt in (DATE_FORMAT, "%Y-%m-%d"):
        try:
            start_date = datetime.strptime(start, fmt).date()
            break
        except ValueError:
            pass
    if not start_date:
        return JSONResponse(status_code=400, content={"error": f"Invalid date format. Expected {DATE_FORMAT} or YYYY-MM-DD"})

    # 2) range guard
    if not (ALLOWED_START <= start_date <= ALLOWED_END):
        return JSONResponse(status_code=400, content={"error": "Week out of allowed range (2025-09-01 .. 2026-12-31)"})

    # 3) week/year
    iso = start_date.isocalendar()
    week = iso.week
    year = iso.year

    # 4) data
    repo = PlanRepository()
    plan = repo.get_week_plan(week, year)

    # 5) payload
    day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    days = [start_date + timedelta(days=i) for i in range(7)]

    week_data = {}
    for i, day in enumerate(day_names):
        meals = plan.meals.get(day, {"breakfast": "-", "lunch": "-", "dinner": "-"})
        week_data[day] = {
            "date": days[i].strftime("%d.%m.%Y"),
            "breakfast": meals.get("breakfast", "-"),
            "lunch": meals.get("lunch", "-"),
            "dinner": meals.get("dinner", "-"),
        }

    return {"meta": {"week": week, "year": year}, "days": week_data}

@app.get("/partial/meal-tbody", response_class=HTMLResponse)
def partial_meal_tbody(request: Request, start: str = Query(...)):
    # parse start
    start_date = None
    for fmt in (DATE_FORMAT, "%Y-%m-%d"):
        try:
            start_date = datetime.strptime(start, fmt).date()
            break
        except ValueError:
            pass
    if not start_date:
        raise HTTPException(status_code=400, detail=f"Invalid date (expected {DATE_FORMAT} or YYYY-MM-DD)")

    if not (ALLOWED_START <= start_date <= ALLOWED_END):
        raise HTTPException(status_code=400, detail="Week out of allowed range (2025-09-01 .. 2026-12-31)")

    iso = start_date.isocalendar()
    week = iso.week
    year = iso.year

    repo = PlanRepository()
    plan = repo.get_week_plan(week, year)
    plan.year = year
    plan.week = week

    recipes = load_recipes()
    resp = templates.TemplateResponse(
        "partials/meal_tbody.html",
        {"request": request, "plan": plan, "recipes": recipes, "time": _ts()}
    )
    resp.headers["Cache-Control"] = "no-store"
    return resp

def _is_past_calendar_day(day_name: str, week: int, year: int) -> bool:
    """Return True if (year, week, day_name) is before today."""
    try:
        iso_wd = DAY_TO_ISO[day_name]
        target = _date.fromisocalendar(year, week, iso_wd)
        return target < _date.today()
    except Exception:
        return False

@app.get("/reset_week")
def reset_week(week: int, year: int):
    repo = PlanRepository()
    repo.reset_week(week, year)
    return RedirectResponse(url=f"/?week={week}&year={year}&notice=reset", status_code=302)

@app.get("/randomize_week")
def randomize_week(week: int, year: int):
    repo = PlanRepository()
    repo.randomize_week(week, year)
    return RedirectResponse(url=f"/?week={week}&year={year}&notice=random", status_code=302)

@app.get("/export_pdf")
def export_pdf(week: int, year: int):
    repo = PlanRepository()
    plan = repo.get_week_plan(week, year)
    pdf_bytes = generate_pdf_for_week(plan)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=meal_plan_{year}_W{week}.pdf"
        },
    )

from meal.domain.Recipe import Recipe
from meal.domain.Ingredient import Ingredient

@app.post("/cook/{day}/{meal}")
def cook_recipe(day: str, meal: str, week: Optional[int] = Query(None), year: Optional[int] = Query(None)):
    repo = PlanRepository()

    # determine week/year if missing
    if week is None or year is None:
        today = _date.today()
        iso = today.isocalendar()
        week, year = iso.week, iso.year

    plan = repo.get_week_plan(week, year)
    recipe_name = plan.meals.get(day, {}).get(meal)

    if not recipe_name or recipe_name == "-":
        return RedirectResponse("/", status_code=303)

    # find recipe by name
    recipes_data = load_recipes()
    recipe_dict = next((r for r in recipes_data if r.get("name") == recipe_name), None)
    if not recipe_dict:
        return RedirectResponse("/", status_code=303)

    recipe = Recipe.from_dict(recipe_dict)
    available_ingredients = [Ingredient.from_dict(i) for i in load_ingredients()]

    # execute cook() method
    cooked = recipe.cook(available_ingredients)

    if cooked:
        # mark cooked in plan
        plan.meals[day][meal] = {"name": recipe.name, "cooked": True, "servings": recipe.servings, "quantity": recipe.servings}
        repo.save_week_plan(week, plan, year)

        # update pantry after consumption
        save_ingredients([i.to_dict() for i in available_ingredients])

        # optional log
        cooked_log = load_cooked_recipes()
        cooked_log.append({
            "name": recipe.name,
            "date_cooked": _date.today().strftime(DATE_FORMAT),
            "day": day,
            "meal": meal,
            "servings": recipe.servings,
            "quantity": recipe.servings,
            "unit": "pcs"
        })
        save_cooked_recipes(cooked_log)

    return RedirectResponse("/", status_code=303)

# -------------------- NEW: Helper for per-slot recipe fetch (for Cook panel) --------------------
@app.get("/api/plan/slot-recipe")
def api_get_slot_recipe(day: str, meal: str, week: int = Query(...), year: int = Query(...)):
    repo = PlanRepository()
    plan = repo.get_week_plan(week, year)
    slot_val = plan.meals.get(day, {}).get(meal)
    if not slot_val or slot_val == "-":
        raise HTTPException(status_code=404, detail="No recipe assigned to this slot")
    if isinstance(slot_val, dict) and slot_val.get("cooked"):
        return {"already_cooked": True, "name": slot_val.get("name")}

    recipes_data = load_recipes()
    recipe_dict = next((r for r in recipes_data if r.get("name") == slot_val), None)
    if not recipe_dict:
        raise HTTPException(status_code=404, detail="Recipe not found")
    # Return only shallow recipe + ingredients for editing (no steps needed here)
    ing_list = []
    for ing in recipe_dict.get("ingredients", []):
        ing_list.append({
            "name": ing.get("name"),
            "default_quantity": ing.get("default_quantity"),
            "unit": ing.get("unit")
        })
    return {
        "name": recipe_dict.get("name"),
        "ingredients": ing_list,
        "servings": recipe_dict.get("servings"),
        "calories_per_serving": recipe_dict.get("calories_per_serving"),
        "macros": recipe_dict.get("macros", {}),
    }

# -------------------- NEW: Cook with overrides (no recipe mutation) --------------------
class CookOverride(BaseModel):
    name: str
    used_quantity: int

class CookRequest(BaseModel):
    day: str
    meal: str
    week: int
    year: int
    overrides: list[CookOverride] | None = None

@app.post("/api/cook")
def api_cook_with_overrides(payload: CookRequest):
    repo = PlanRepository()
    plan = repo.get_week_plan(payload.week, payload.year)
    slot_val = plan.meals.get(payload.day, {}).get(payload.meal)
    if not slot_val or slot_val == "-":
        raise HTTPException(status_code=404, detail="No recipe assigned to this slot")
    if isinstance(slot_val, dict) and slot_val.get("cooked"):
        raise HTTPException(status_code=400, detail="Already cooked")

    recipe_name = slot_val if isinstance(slot_val, str) else slot_val.get("name")
    recipes_data = load_recipes()
    recipe_dict = next((r for r in recipes_data if r.get("name") == recipe_name), None)
    if not recipe_dict:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Build Recipe object & override ingredient quantities if provided
    base_recipe = Recipe.from_dict(json.loads(json.dumps(recipe_dict)))  # deep-ish copy through json
    overrides_map = {o.name: int(o.used_quantity) for o in (payload.overrides or []) if o.used_quantity is not None}
    for ing in base_recipe.ingredients:
        if ing.name in overrides_map:
            try:
                val = int(overrides_map[ing.name])
                if val < 0:
                    raise ValueError
                ing.default_quantity = val
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid quantity for {ing.name}")

    # Load pantry ingredients as Ingredient domain objects
    available_ingredients = [Ingredient.from_dict(i) for i in load_ingredients()]

    # Validate availability manually (base_recipe.check_ingredients already does that)
    if not base_recipe.check_ingredients(available_ingredients):
        raise HTTPException(status_code=400, detail="Insufficient ingredients in pantry for selected quantities")

    cooked_obj = base_recipe.cook(available_ingredients)
    if not cooked_obj:
        raise HTTPException(status_code=400, detail="Cook failed")

    # Mark plan slot cooked with overrides
    plan.meals[payload.day][payload.meal] = {"name": recipe_name, "cooked": True, "overrides": overrides_map, "servings": base_recipe.servings, "quantity": base_recipe.servings}
    repo.save_week_plan(payload.week, plan, payload.year)

    # Persist pantry deductions
    save_ingredients([i.to_dict() for i in available_ingredients])

    # Log cooked
    cooked_log = load_cooked_recipes()
    cooked_log.append({
        "name": recipe_name,
        "date_cooked": _date.today().strftime(DATE_FORMAT),
        "day": payload.day,
        "meal": payload.meal,
        "overrides": overrides_map,
        "servings": base_recipe.servings,
        "quantity": base_recipe.servings,
        "unit": "pcs"
    })
    save_cooked_recipes(cooked_log)

    return {"success": True, "cooked": {"name": recipe_name, "overrides": overrides_map, "servings": base_recipe.servings}}

class RandomizeCustomRequest(BaseModel):
    week: int
    year: int
    days: list[str] | None = None
    replace_existing: bool = False
    only_available: bool = False

@app.post("/randomize_custom")
def randomize_custom(payload: RandomizeCustomRequest):
    repo = PlanRepository()
    modified = repo.randomize_custom(payload.week, payload.year, payload.days, payload.replace_existing, payload.only_available)
    return {"modified": modified, "week": payload.week, "year": payload.year}
