# Meal Planner & Pantry Management (FastAPI)

A lightweight meal planning, pantry inventory, and shopping list assistant built with **FastAPI**, **Jinja2** templates, and simple JSON persistence (no database required). It helps you:

- Organize weekly meal plans (breakfast / lunch / dinner)
- Track pantry stock, low‑stock items, and expiring ingredients
- Store and enrich recipes (macros + calories) using the Spoonacular API
- Auto‑generate shopping lists (optionally skipping past days in the current week)
- Inspect nutrition totals per day and aggregated for the week
- View individual recipe details with ingredients, steps, and macro breakdown

---
## Table of Contents
1. Features
2. Project Structure
3. Data & Persistence Layer
4. Domain Model Overview
5. Installation
6. Running the Application
7. API & UI Endpoints
8. Nutrition & Shopping List Logic
9. Events & Alerts
10. Tests
11. Configuration & Environment
12. Security Notes (API Key)
13. Roadmap / Possible Improvements
14. Troubleshooting

---
## 1. Features
- Weekly meal plan (ISO week + year aware) rendered via `index.html`
- Ingredient tagging & normalization (plural→singular heuristics for shopping list)
- Automatic detection of:
  - Low stock items (threshold per unit)
  - Items nearing or past expiry (configurable window)
- Recipe ingestion via form + optional image upload
- Nutrition enrichment (calories + macros) from Spoonacular API
- Shopping list builder that considers pantry quantities and cooked meals
- Per‑day + per‑week nutrition aggregation (calories, protein, carbs, fats)
- Basic event observer hooks (low stock / expiry) for future UI alerts
- Pure JSON storage (easy to inspect & version) – no DB dependency

---
## 2. Project Structure
```
meal/
  api/              # FastAPI application + routes (UI + JSON helpers)
  domain/           # Core business entities (Ingredient, Recipe, Plan, etc.)
  infra/            # File-based repositories & PDF utilities
  logic/            # Consolidated business logic (shopping, reporting, pantry analysis)
  events/           # Event bus + web observers
  utilities/        # Constants & helpers
  static/           # JS, CSS, images, thumbnails
  templates/        # Jinja2 HTML templates
  data/             # JSON persistence layer
  tests/            # Unit & integration tests (pytest + unittest mix)
```
Root launcher: `meal/main.py` (runs the FastAPI app with Uvicorn).

---
## 3. Data & Persistence Layer
All state is stored in JSON under `meal/data/`:
- `recipes.json` – canonical recipe catalog
- `Pantry_ingredients.json` – pantry stock with quantities, units, expiry dates, tags
- `Pantry_recipe_cooked.json` – log of cooked recipes (date_cooked normalized to `DD-MM-YYYY`)
- `plan.json` – meal plans keyed by (week, year)
- `shopping_transactions.json` – (reserved / future use)

Changes are written atomically where appropriate (e.g. recipe additions).

---
## 4. Domain Model Overview
- `Ingredient` – name, unit, quantity (`default_quantity`), optional expiry (`data_expirare`), tags
- `Recipe` – name, servings, list of ingredients, steps, tags, calories_per_serving, macros
- `Plan` – weekly structure: `plan.meals[day][slot]` where slot ∈ {breakfast, lunch, dinner}
- `RecipeCooked` (logged when cooking; affects pantry logic)
- Shopping list builder consolidates required vs. available ingredients (`required - have = missing`)

Plural/singular normalization and case-insensitive matching reduce duplicates (`Tomatoes` vs `tomato`).

---
## 5. Installation
Requires Python >= 3.9.

Windows (CMD):
```
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

(Optional) For development reload:
```
pip install watchdog
```

---
## 6. Running the Application
Basic run (default port 8000):
```
python -m meal.main
```
Or directly with Uvicorn (hot reload during development):
```
uvicorn meal.api.api_run:app --reload --port 8000
```
Then open: http://localhost:8000/

---
## 7. API & UI Endpoints
(Primary outputs are server‑rendered HTML; some routes return JSON/text.)

UI / HTML
- `GET /` – Main dashboard (current or selected week): plan, expiring & low stock, nutrition
- `GET /meal-plan/{week}` – Alternate view for a specific week (legacy style)
- `GET /shopping-list` – Computed shopping list page (skips past days in current week unless `?include_past=1`)
- `GET /recipe/{recipe_name}` – Recipe detail with macro summary
- `GET /recipes-page` – Grid listing; filter by tag (`?tag=vegetarian`)
- `GET /add-recipe` – Form to add a new recipe

Recipe Creation & Debug
- `POST /recipes` – (Multipart/Form) Create a recipe + optional image; enriches nutrition via Spoonacular
- `GET /_debug/recipes` – Raw recipes JSON (debug only)
- `GET /_debug/recipes-path` – Path to `recipes.json`

Plan Updates
- `POST /update_meal` – Update a meal slot (accepts either `multipart/form-data` or JSON depending on availability of `python-multipart`)

Base Recipes Listing (from `recipes.py` router)
- `GET /` (root of that sub-router when mounted) – Text dump of recipes (each `repr` on new line)
- `POST /` – Echo test endpoint (accepts arbitrary recipe dict)

Static Assets
- `/static/*` – JS, CSS, images

NOTE: Authentication is not implemented; all endpoints are open (suitable only for local / trusted environments).

---
## 8. Nutrition & Shopping List Logic
### Nutrition
`compute_week_nutrition(plan, recipes)` aggregates per meal slot → per day → week totals:
```
{
  days: { 'Monday': { calories, protein, carbs, fats, meals: { breakfast: {...}, ... } }, ... },
  week_totals: { calories, protein, carbs, fats }
}
```
Gracefully skips unknown / missing recipes.

### Shopping List
`build_shopping_list(plan, recipes, pantry, skip_past_days=False)`:
- Indexes recipes by normalized name
- Accumulates required ingredient quantities for planned (not yet cooked) meals
- Subtracts pantry `have` amounts
- Returns only items where `missing > 0`
- Sorts alphabetically
- If `skip_past_days=True` and a meal day has a date earlier than today, it's ignored

---
## 9. Events & Alerts
The event bus registers observers on startup (`start_event_observers()`):
- Potential hooks for: low stock alerts, near-expiry notifications, expiring snapshot
Currently surfaced primarily via internal lists rendered on the homepage (low stock + expiring soon).

Constants (`utilities/constants.py`):
- `DATE_FORMAT = "%d-%m-%Y"`
- `DAYS_BEFORE_EXPIRY = 5`
- `LOW_STOCK_THRESHOLD = {"g": 200, "ml": 500, "pcs": 3, "cloves": 2}`

---
## 10. Tests
Located in `meal/tests/` (mix of `pytest` async test + classic `unittest`).

Run all tests:
```
pytest -q
```
Highlights:
- `test_add_recipe.py` – Adds a recipe via API and rejects duplicate name
- `test_recipe_detail.py` – Verifies recipe detail page & 404 branch
- `test_ingredient.py` – Quantity adjust logic
- `test_pantry.py` – Pantry add/remove/list behavior
- `test_recipe.py` – Ingredient availability + cooking simulation adjusting pantry
- Additional builder / shopping list tests (if present) validate list generation

---
## 11. Configuration & Environment
Environment variables you may introduce:
- `SPOONACULAR_API_KEY` – Instead of the hard-coded key (see Security Notes)
- `PORT` – If wrapping a custom runner script

For now, JSON file paths are relative and derived from module locations; no .env loader is required.

---
## 12. Security Notes (API Key)
`meal/api/routes/add.py` currently contains a hard-coded Spoonacular API key:
```
API_KEY = "5ff4f96c305e44fd8a8bb9d94278e058"
```
You SHOULD replace this with an environment variable:
```python
import os
API_KEY = os.getenv("SPOONACULAR_API_KEY", "")
```
Never commit real production keys. Regenerate if this key was exposed publicly.

---
## 13. Roadmap / Possible Improvements
Short Term:
- Replace hard-coded API key with env variable (see above)
- Add authentication (API token or simple login) for mutation endpoints
- Add endpoint documentation via FastAPI OpenAPI tags
- Improve plural/singular stemming (use `inflect` library)
- Add unit tests for nutrition aggregation edge cases
- Add PDF export for weekly plan & shopping list (foundation exists in `pdf_utils`)

Medium Term:
- Persist cooked meals updates to plan automatically
- WebSocket push for inventory alerts (currently event bus is internal only)
- Multi-user plans / profiles
- Switch to SQLite or Postgres (optional) behind repository abstraction

Long Term:
- Meal recommendation engine based on macros
- Inventory forecasting & waste reduction analytics

---
## 14. Troubleshooting
| Issue | Cause | Fix |
|-------|-------|-----|
| Images not displaying | File not saved or wrong name | Check `static/pictures/` and recipe `image` field |
| Duplicate ingredients on shopping list | Slight name variants | Standardize names; enhance stemming rules |
| Nutrition zeros | API failure or missing macros | Inspect Spoonacular response; verify API key quota |
| Form POST to `/update_meal` fails | Missing `python-multipart` | Install dependency (already in requirements) |
| 404 on recipe detail | Name mismatch (spaces/case) | Ensure URL-encoding and matching lower-case name |

Logging: (Add custom logging config if needed – currently minimal.)

---
## Contributing
1. Fork / branch
2. Add or adjust tests (aim for clear unit coverage)
3. Keep JSON schema backward compatible where possible
4. Open a PR with a clear description & rationale

---
## License
(Define a license here – e.g. MIT, Apache 2.0. Currently unspecified.)

---
## Quick Start (Copy/Paste)
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn meal.api.api_run:app --reload --port 8000
```
Open http://localhost:8000/

Add a recipe at: http://localhost:8000/add-recipe
Generate a shopping list: http://localhost:8000/shopping-list

---
Enjoy building and extending your Meal Planner! 🍽️
