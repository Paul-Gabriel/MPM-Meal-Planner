import json, os, random
from typing import Optional, List
from datetime import timedelta, date, datetime
from meal.domain.Plan import Plan
from meal.api.routes.recipes import load_recipes
from meal.infra.paths import PLAN_FILE, PANTRY_FILE
from meal.domain.Recipe import Recipe

def _week_key(year: int, week_number: int) -> str:
    return f"{year}-W{week_number:02d}"

class PlanRepository:
    def get_week_plan(self, week_number: int, year: Optional[int] = None) -> Plan:
        if year is None:
            year = date.today().isocalendar().year
        if not os.path.exists(PLAN_FILE):
            with open(PLAN_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)
        try:
            with open(PLAN_FILE, "r", encoding="utf-8") as f:
                store = json.load(f) or {}
        except Exception:
            store = {}
        key = _week_key(year, week_number)
        if key not in store:
            store[key] = {d: {"breakfast": "-", "lunch": "-", "dinner": "-"}
                          for d in ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]}
            with open(PLAN_FILE, "w", encoding="utf-8") as f:
                json.dump(store, f, indent=2, ensure_ascii=False)
        meals = store[key]
        monday = date.fromisocalendar(year, week_number, 1)
        days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        for i, day_name in enumerate(days):
            d = monday + timedelta(days=i)
            meals.setdefault(day_name, {"breakfast": "-", "lunch": "-", "dinner": "-"})
            meals[day_name].setdefault("breakfast", "-")
            meals[day_name].setdefault("lunch", "-")
            meals[day_name].setdefault("dinner", "-")
            meals[day_name]["date"] = d.strftime("%d.%m.%Y")
        plan = Plan(week_number, meals, year=year)
        plan.week = week_number
        plan.year = year
        return plan

    def save_week_plan(self, week_number: int, plan: Plan, year: Optional[int] = None) -> None:
        if year is None:
            year = getattr(plan, "year", date.today().isocalendar().year)
        try:
            with open(PLAN_FILE, "r", encoding="utf-8") as f:
                store = json.load(f) or {}
        except Exception:
            store = {}
        key = _week_key(year, week_number)
        clean_meals = {day: {k: v for k, v in meals.items() if k != "date"}
                       for day, meals in plan.meals.items()}
        store[key] = clean_meals
        with open(PLAN_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2, ensure_ascii=False)

    def reset_week(self, week_number: int, year: Optional[int] = None):
        """Reset non-cooked meals for future (or today) days only.

        Rules:
          - Do NOT modify meals whose date is in the past.
          - Do NOT modify slots already marked as cooked (dict with cooked=True).
          - Other slots are set back to '-'.

        """
        plan = self.get_week_plan(week_number, year)
        today = date.today()
        for day, meals in plan.meals.items():
            # Parse day date if present
            day_date = None
            try:
                day_date = datetime.strptime(meals.get("date",""), "%d.%m.%Y").date()
            except Exception:
                pass
            if day_date and day_date < today:
                # Skip past days entirely
                continue
            for slot in ("breakfast", "lunch", "dinner"):
                val = meals.get(slot)
                # Preserve cooked meals (dict with cooked True)
                if isinstance(val, dict) and val.get("cooked"):
                    continue
                meals[slot] = "-"
        self.save_week_plan(week_number, plan, year)

    def randomize_week(self, week_number: int, year: Optional[int] = None):
        """Fill meal plan with random recipes ensuring no duplicate recipe appears twice in the same day.

        Behavior:
          - Past days are never modified.
          - Cooked slots (dict with cooked=True) are never replaced.
          - If the entire week is in the future, non-cooked slots (including already assigned names) are re-randomized.
          - Otherwise, only empty placeholders ('-', '', None) are filled.
          - Uniqueness rule: A recipe can appear at most once per day after this operation among the slots that were (re)assigned.
            Existing duplicates that are not eligible for replacement (because we only fill empty) are left as-is.
          - If we run out of unique recipes to place, remaining target slots become '-'.

        --- Changes in this version ---
        - Enforce strict per-day uniqueness: for both randomize_week and randomize_custom we first deduplicate
          existing non-cooked string slots (keep first occurrence, blank duplicates to '-') and then proceed
          with the existing filling logic while tracking used names so no recipe is placed twice in the same day.
        """
        plan = self.get_week_plan(week_number, year)
        recipes = load_recipes()
        recipe_names = [r["name"] for r in recipes] if recipes else []
        today = date.today()
        day_dates = []
        for meals in plan.meals.values():
            try:
                day_dates.append(datetime.strptime(meals["date"], "%d.%m.%Y").date())
            except Exception:
                pass
        entire_week_in_future = bool(day_dates) and min(day_dates) > today
        fill_only_empty = not entire_week_in_future

        for day, meals in plan.meals.items():
            try:
                day_date = datetime.strptime(meals["date"], "%d.%m.%Y").date()
            except Exception:
                continue
            if day_date < today:
                continue

            # --- New: strict per-day deduplication for non-cooked slots ---
            # If the same recipe appears multiple times in non-cooked slots, keep only the first occurrence
            # and set the rest to '-'. This enforces the strict rule: never the same recipe twice in a day.
            slots = ("breakfast", "lunch", "dinner")
            seen = set()
            for slot in slots:
                val = meals.get(slot)
                # Skip cooked slots entirely
                if isinstance(val, dict) and val.get("cooked"):
                    # if cooked has a name, register it as used
                    if isinstance(val.get("name"), str) and val.get("name"):
                        seen.add(val.get("name"))
                    continue
                if isinstance(val, str) and val not in ("-", "", None):
                    if val in seen:
                        # duplicate -> blank it out
                        meals[slot] = "-"
                    else:
                        seen.add(val)
            # --- End deduplication ---

            # Track used recipes for this day (strings) among slots we keep
            used = set()
            if fill_only_empty:
                for slot in ("breakfast", "lunch", "dinner"):
                    cur = meals.get(slot)
                    if isinstance(cur, str) and cur not in ("-", "", None):
                        # Keep existing; register to avoid duplicates for newly filled slots
                        used.add(cur)
            # Determine slots to modify
            for slot in ("breakfast", "lunch", "dinner"):
                cur = meals.get(slot)
                # Always skip cooked
                if isinstance(cur, dict) and cur.get("cooked"):
                    continue
                if fill_only_empty and cur not in (None, "", "-"):
                    continue
                # Build available choices excluding already used
                available = [r for r in recipe_names if r not in used]
                if not available:
                    meals[slot] = "-"
                    continue
                choice = random.choice(available)
                meals[slot] = choice
                used.add(choice)
        self.save_week_plan(week_number, plan, year)

    def randomize_custom(self, week_number: int, year: Optional[int] = None, days: Optional[List[str]] = None, replace_existing: bool = False, only_available: bool = False) -> int:
        """Randomize specific days with uniqueness (no recipe appears twice in the same day).

        Args:
            week_number: ISO week number
            year: year
            days: list of day names (Monday..Sunday); if None -> all
            replace_existing: if True, replace any non-cooked slot (string) including already assigned recipes
            only_available: if True, restrict pool to recipes fully satisfiable by current pantry quantities
        Returns:
            int: number of slots modified (value actually changed)
        Rules:
          - Never modify past calendar days.
          - Never modify cooked slots (dict with cooked=True).
          - If only_available=True and no recipes qualify, nothing is changed for requested slots.
          - Uniqueness: Within each day after this call, any slot that was modified will not duplicate an existing (kept) or other newly assigned recipe.
            If insufficient distinct recipes exist, remaining target slots become '-'.
        """
        plan = self.get_week_plan(week_number, year)
        recipes = load_recipes()
        recipe_names = [r["name"] for r in recipes] if recipes else []

        if only_available and recipes:
            try:
                with open(PANTRY_FILE, 'r', encoding='utf-8') as f:
                    pantry_items = json.load(f) or []
            except Exception:
                pantry_items = []
            stock = {}
            for ing in pantry_items:
                name = ing.get('name','')
                qty = ing.get('default_quantity',0)
                try:
                    qty = int(qty)
                except Exception:
                    qty = 0
                key = Recipe._normalize_name(name) if hasattr(Recipe,'_normalize_name') else name.strip().lower()
                stock[key] = stock.get(key,0) + qty
            avail = []
            for r in recipes:
                ok = True
                for ing in r.get('ingredients', []):
                    iname = ing.get('name','')
                    req = ing.get('default_quantity',0)
                    try:
                        req = int(req)
                    except Exception:
                        req = 0
                    key = Recipe._normalize_name(iname) if hasattr(Recipe,'_normalize_name') else iname.strip().lower()
                    if stock.get(key,0) < req:
                        ok = False
                        break
                if ok:
                    avail.append(r.get('name'))
            recipe_names_available = avail
        else:
            recipe_names_available = recipe_names

        today = date.today()
        valid_days = {"Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"}
        target_days = set(d for d in (days or valid_days) if d in valid_days)
        modified = 0
        if only_available and not recipe_names_available:
            return 0
        for day_name, meals in plan.meals.items():
            if day_name not in target_days:
                continue
            try:
                day_date = datetime.strptime(meals.get("date",""), "%d.%m.%Y").date()
            except Exception:
                continue
            if day_date < today:
                continue
            # Determine slots to possibly modify
            candidate_slots = []
            for slot in ("breakfast", "lunch", "dinner"):
                cur = meals.get(slot)
                if isinstance(cur, dict) and cur.get("cooked"):
                    continue
                if replace_existing:
                    candidate_slots.append(slot)
                else:
                    if cur in (None, "", "-"):
                        candidate_slots.append(slot)
            if not candidate_slots:
                continue

            # --- New: strict per-day deduplication for non-cooked slots ---
            # Remove duplicates among non-cooked string slots by keeping first occurrence and blanking others.
            slots = ("breakfast", "lunch", "dinner")
            seen = set()
            for slot in slots:
                val = meals.get(slot)
                # Skip cooked slots and register cooked names
                if isinstance(val, dict) and val.get("cooked"):
                    if isinstance(val.get("name"), str) and val.get("name"):
                        seen.add(val.get("name"))
                    continue
                if isinstance(val, str) and val not in ("-", "", None):
                    if val in seen:
                        # duplicate -> blank it out; if this slot is in candidate_slots, it's considered modified
                        if meals.get(slot) != "-":
                            meals[slot] = "-"
                            # Count as modification only if this slot was considered for modification
                            if slot in candidate_slots:
                                modified += 1
                    else:
                        seen.add(val)
            # --- End deduplication ---

            # Build initial used set from slots we are NOT modifying (to preserve uniqueness) + cooked names if any
            used = set()
            for slot in ("breakfast", "lunch", "dinner"):
                if slot not in candidate_slots:
                    val = meals.get(slot)
                    if isinstance(val, str) and val not in ("-", "", None):
                        used.add(val)
                else:
                    # cooked already skipped earlier, but just in case include cooked names
                    val = meals.get(slot)
                    if isinstance(val, dict) and val.get("name"):
                        used.add(val.get("name"))
            # For replace_existing we will blank out then fill with unique choices
            for slot in candidate_slots:
                cur = meals.get(slot)
                available = [r for r in recipe_names_available if r not in used]
                if not available:
                    # No unique recipe left
                    if cur != "-":
                        meals[slot] = "-"
                        if cur != "-":
                            modified += 1
                    else:
                        meals[slot] = "-"  # stays same
                    continue
                choice = random.choice(available)
                if choice != cur:
                    meals[slot] = choice
                    modified += 1
                used.add(choice)
        self.save_week_plan(week_number, plan, year)
        return modified
