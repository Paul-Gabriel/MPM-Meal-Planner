import unittest
from datetime import date
from meal.infra.Plan_Repository import PlanRepository
import json
from meal.infra.paths import PANTRY_FILE, RECIPES_FILE
from meal.domain.Recipe import Recipe

class TestRandomizeCustomOnlyAvailable(unittest.TestCase):
    def setUp(self):
        self.repo = PlanRepository()
        iso = date.today().isocalendar()
        self.week, self.year = iso.week, iso.year
        self.plan = self.repo.get_week_plan(self.week, self.year)
        # Choose first non-past day
        today_wd = date.today().isoweekday()
        order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        self.target_day = None
        for idx, name in enumerate(order, start=1):
            if idx >= today_wd:
                self.target_day = name
                break
        if not self.target_day:
            self.skipTest("No suitable target day")
        # Prepare day slots
        self.plan.meals[self.target_day]['breakfast'] = 'Spaghetti Bolognese'
        self.plan.meals[self.target_day]['lunch'] = '-'
        self.plan.meals[self.target_day]['dinner'] = '-'
        self.repo.save_week_plan(self.week, self.plan, self.year)

    def _available_set(self):
        with open(RECIPES_FILE, 'r', encoding='utf-8') as fr:
            recipes = json.load(fr)
        try:
            with open(PANTRY_FILE, 'r', encoding='utf-8') as fp:
                pantry = json.load(fp)
        except Exception:
            pantry = []
        stock = {}
        for ing in pantry:
            name = ing.get('name','')
            qty = ing.get('default_quantity',0)
            try: qty=int(qty)
            except Exception: qty=0
            key = Recipe._normalize_name(name) if hasattr(Recipe,'_normalize_name') else name.strip().lower()
            stock[key] = stock.get(key,0)+qty
        avail = set()
        for r in recipes:
            ok=True
            for ing in r.get('ingredients', []):
                iname = ing.get('name','')
                req = ing.get('default_quantity',0)
                try: req=int(req)
                except Exception: req=0
                key = Recipe._normalize_name(iname) if hasattr(Recipe,'_normalize_name') else iname.strip().lower()
                if stock.get(key,0) < req:
                    ok=False; break
            if ok:
                avail.add(r.get('name'))
        return avail

    def test_only_available_randomize(self):
        available = self._available_set()
        if len(available) < 1:
            self.skipTest('No available recipes in current pantry state')
        changed = self.repo.randomize_custom(self.week, self.year, days=[self.target_day], replace_existing=False, only_available=True)
        plan_after = self.repo.get_week_plan(self.week, self.year)
        lunch_val = plan_after.meals[self.target_day]['lunch']
        self.assertIn(lunch_val, available, 'Lunch should be filled with an available recipe')
        # Now test replace_existing with only_available
        prev_breakfast = plan_after.meals[self.target_day]['breakfast']
        self.repo.randomize_custom(self.week, self.year, days=[self.target_day], replace_existing=True, only_available=True)
        plan_after2 = self.repo.get_week_plan(self.week, self.year)
        new_breakfast = plan_after2.meals[self.target_day]['breakfast']
        self.assertIn(new_breakfast, available)
        # If pool >1 we expect a potential change (not mandatory to assert due to randomness)

if __name__ == '__main__':
    unittest.main()

