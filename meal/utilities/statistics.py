"""
Statistics and Analytics module for Meal Planner.
Provides insights into cooking habits, nutrition trends, and pantry usage.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MealPlannerStats:
    """Generate statistics and insights from meal planner data."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    def _load_cooked_recipes(self) -> List[Dict]:
        """Load cooked recipes log."""
        try:
            with open(self.data_dir / "Pantry_recipe_cooked.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load cooked recipes: {e}")
            return []

    def _load_recipes(self) -> List[Dict]:
        """Load all recipes."""
        try:
            with open(self.data_dir / "recipes.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load recipes: {e}")
            return []

    def _load_plan(self) -> Dict:
        """Load meal plan."""
        try:
            with open(self.data_dir / "plan.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load plan: {e}")
            return {}

    def most_cooked_recipes(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get the most frequently cooked recipes."""
        cooked = self._load_cooked_recipes()
        recipe_names = [entry.get('recipe_name', '') for entry in cooked if entry.get('recipe_name')]
        counter = Counter(recipe_names)
        return counter.most_common(limit)

    def cooking_frequency_by_day(self) -> Dict[str, int]:
        """Get cooking frequency by day of week."""
        cooked = self._load_cooked_recipes()
        day_counter = Counter()

        for entry in cooked:
            date_str = entry.get('date_cooked', '')
            if date_str:
                try:
                    # Parse date (DD-MM-YYYY format)
                    dt = datetime.strptime(date_str, "%d-%m-%Y")
                    day_name = dt.strftime("%A")
                    day_counter[day_name] += 1
                except Exception:
                    continue

        return dict(day_counter)

    def average_nutrition_per_week(self, weeks: int = 4) -> Dict[str, float]:
        """Calculate average nutrition for recent weeks."""
        cooked = self._load_cooked_recipes()
        recipes = {r['name']: r for r in self._load_recipes()}

        # Filter last N weeks
        cutoff_date = datetime.now() - timedelta(weeks=weeks)
        recent_cooked = []

        for entry in cooked:
            date_str = entry.get('date_cooked', '')
            try:
                dt = datetime.strptime(date_str, "%d-%m-%Y")
                if dt >= cutoff_date:
                    recent_cooked.append(entry)
            except Exception:
                continue

        # Sum nutrition
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fats = 0
        count = 0

        for entry in recent_cooked:
            recipe_name = entry.get('recipe_name', '')
            recipe = recipes.get(recipe_name)
            if recipe:
                servings = entry.get('servings_cooked', 1)
                total_calories += recipe.get('calories_per_serving', 0) * servings
                macros = recipe.get('macros', {})
                total_protein += macros.get('protein', 0) * servings
                total_carbs += macros.get('carbs', 0) * servings
                total_fats += macros.get('fats', 0) * servings
                count += 1

        if count == 0:
            return {'calories': 0, 'protein': 0, 'carbs': 0, 'fats': 0}

        days = weeks * 7
        return {
            'calories_per_day': round(total_calories / days, 2),
            'protein_per_day': round(total_protein / days, 2),
            'carbs_per_day': round(total_carbs / days, 2),
            'fats_per_day': round(total_fats / days, 2),
            'meals_per_week': round(count / weeks, 2)
        }

    def recipe_tags_distribution(self) -> Dict[str, int]:
        """Get distribution of recipe tags."""
        recipes = self._load_recipes()
        tag_counter = Counter()

        for recipe in recipes:
            for tag in recipe.get('tags', []):
                tag_counter[tag] += 1

        return dict(tag_counter.most_common())

    def unused_recipes(self) -> List[str]:
        """Find recipes that have never been cooked."""
        recipes = self._load_recipes()
        cooked = self._load_cooked_recipes()

        all_recipes = {r['name'] for r in recipes}
        cooked_recipes = {entry.get('recipe_name') for entry in cooked}

        return sorted(all_recipes - cooked_recipes)

    def pantry_value_estimate(self, price_per_kg: float = 10.0) -> Dict[str, float]:
        """Estimate pantry value (rough calculation)."""
        try:
            with open(self.data_dir / "Pantry_ingredients.json", 'r', encoding='utf-8') as f:
                pantry = json.load(f)

            total_weight_g = 0
            total_volume_ml = 0
            item_count = 0

            for item in pantry:
                qty = item.get('default_quantity', 0)
                unit = item.get('unit', '')

                if unit == 'g':
                    total_weight_g += qty
                elif unit == 'ml':
                    total_volume_ml += qty
                elif unit in ['pcs', 'cloves']:
                    item_count += qty

            return {
                'total_weight_kg': round(total_weight_g / 1000, 2),
                'total_volume_l': round(total_volume_ml / 1000, 2),
                'item_count': item_count,
                'estimated_value': round((total_weight_g / 1000) * price_per_kg, 2)
            }
        except Exception as e:
            logger.error(f"Failed to estimate pantry value: {e}")
            return {}

    def meal_diversity_score(self, weeks: int = 4) -> float:
        """
        Calculate meal diversity score (0-100).
        Higher score = more variety in meals.
        """
        cooked = self._load_cooked_recipes()

        # Filter recent weeks
        cutoff_date = datetime.now() - timedelta(weeks=weeks)
        recent_recipes = []

        for entry in cooked:
            date_str = entry.get('date_cooked', '')
            try:
                dt = datetime.strptime(date_str, "%d-%m-%Y")
                if dt >= cutoff_date:
                    recent_recipes.append(entry.get('recipe_name', ''))
            except Exception:
                continue

        if not recent_recipes:
            return 0.0

        unique_recipes = len(set(recent_recipes))
        total_meals = len(recent_recipes)

        # Score: (unique / total) * 100
        diversity = (unique_recipes / total_meals) * 100
        return round(diversity, 2)

    def generate_report(self) -> Dict:
        """Generate comprehensive statistics report."""
        return {
            'most_cooked': self.most_cooked_recipes(10),
            'cooking_by_day': self.cooking_frequency_by_day(),
            'nutrition_averages': self.average_nutrition_per_week(4),
            'tag_distribution': self.recipe_tags_distribution(),
            'unused_recipes': self.unused_recipes(),
            'pantry_stats': self.pantry_value_estimate(),
            'diversity_score': self.meal_diversity_score(4),
            'generated_at': datetime.now().isoformat()
        }

    def print_report(self):
        """Print a formatted statistics report."""
        report = self.generate_report()

        print("\n" + "="*60)
        print("📊 MEAL PLANNER STATISTICS REPORT")
        print("="*60)

        print("\n🏆 TOP 10 MOST COOKED RECIPES:")
        for i, (recipe, count) in enumerate(report['most_cooked'], 1):
            print(f"  {i}. {recipe}: {count} times")

        print("\n📅 COOKING FREQUENCY BY DAY:")
        for day, count in sorted(report['cooking_by_day'].items()):
            bar = "█" * count
            print(f"  {day:10s}: {bar} ({count})")

        print("\n🥗 AVERAGE NUTRITION (Last 4 weeks):")
        nutr = report['nutrition_averages']
        print(f"  Calories/day: {nutr.get('calories_per_day', 0):.0f} kcal")
        print(f"  Protein/day:  {nutr.get('protein_per_day', 0):.1f} g")
        print(f"  Carbs/day:    {nutr.get('carbs_per_day', 0):.1f} g")
        print(f"  Fats/day:     {nutr.get('fats_per_day', 0):.1f} g")
        print(f"  Meals/week:   {nutr.get('meals_per_week', 0):.1f}")

        print("\n🏷️  RECIPE TAG DISTRIBUTION:")
        for tag, count in list(report['tag_distribution'].items())[:10]:
            print(f"  {tag:15s}: {count}")

        print(f"\n🍽️  DIVERSITY SCORE: {report['diversity_score']:.1f}/100")

        print("\n📦 PANTRY STATISTICS:")
        pantry = report['pantry_stats']
        print(f"  Total weight: {pantry.get('total_weight_kg', 0)} kg")
        print(f"  Total volume: {pantry.get('total_volume_l', 0)} L")
        print(f"  Item count:   {pantry.get('item_count', 0)} pcs")
        print(f"  Est. value:   ${pantry.get('estimated_value', 0):.2f}")

        unused = report['unused_recipes']
        if unused:
            print(f"\n💤 UNUSED RECIPES ({len(unused)}):")
            for recipe in unused[:10]:
                print(f"  - {recipe}")
            if len(unused) > 10:
                print(f"  ... and {len(unused) - 10} more")

        print("\n" + "="*60)
        print(f"Report generated: {report['generated_at']}")
        print("="*60 + "\n")


# CLI interface
if __name__ == "__main__":
    from meal.infra.paths import DATA_DIR

    stats = MealPlannerStats(DATA_DIR)
    stats.print_report()

    # Save JSON report
    report = stats.generate_report()
    output_file = Path("meal_planner_stats.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"✓ Detailed report saved to: {output_file}")

