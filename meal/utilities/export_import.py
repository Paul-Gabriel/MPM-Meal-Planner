"""
Export and Import functionality for recipes, pantry, and meal plans.
"""
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class DataExporter:
    """Export meal planner data in various formats."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    def export_recipes(self, output_path: Path = None) -> Path:
        """Export all recipes to JSON file."""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"recipes_export_{timestamp}.json")

        try:
            recipes_file = self.data_dir / "recipes.json"
            if recipes_file.exists():
                with open(recipes_file, 'r', encoding='utf-8') as f:
                    recipes = json.load(f)

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(recipes, f, indent=2, ensure_ascii=False)

                logger.info(f"Exported {len(recipes)} recipes to {output_path}")
                return output_path
            else:
                logger.error("Recipes file not found")
                return None
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return None

    def export_pantry(self, output_path: Path = None) -> Path:
        """Export pantry inventory to JSON file."""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"pantry_export_{timestamp}.json")

        try:
            pantry_file = self.data_dir / "Pantry_ingredients.json"
            if pantry_file.exists():
                with open(pantry_file, 'r', encoding='utf-8') as f:
                    pantry = json.load(f)

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(pantry, f, indent=2, ensure_ascii=False)

                logger.info(f"Exported {len(pantry)} pantry items to {output_path}")
                return output_path
            else:
                logger.error("Pantry file not found")
                return None
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return None

    def export_all(self, output_path: Path = None) -> Path:
        """Export all data (recipes, pantry, plans) as a ZIP archive."""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"meal_planner_backup_{timestamp}.zip")

        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all JSON files from data directory
                for json_file in self.data_dir.glob('*.json'):
                    zipf.write(json_file, arcname=json_file.name)

                # Add metadata
                metadata = {
                    'export_date': datetime.now().isoformat(),
                    'version': '1.0',
                    'files': [f.name for f in self.data_dir.glob('*.json')]
                }
                zipf.writestr('metadata.json', json.dumps(metadata, indent=2))

            logger.info(f"Exported all data to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return None

    def export_to_csv(self, data_type: str = "recipes") -> Path:
        """Export data to CSV format for Excel compatibility."""
        import csv

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"{data_type}_export_{timestamp}.csv")

        try:
            if data_type == "recipes":
                recipes_file = self.data_dir / "recipes.json"
                with open(recipes_file, 'r', encoding='utf-8') as f:
                    recipes = json.load(f)

                with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['name', 'servings', 'calories_per_serving', 'protein', 'carbs', 'fats', 'tags']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    for recipe in recipes:
                        writer.writerow({
                            'name': recipe.get('name', ''),
                            'servings': recipe.get('servings', 0),
                            'calories_per_serving': recipe.get('calories_per_serving', 0),
                            'protein': recipe.get('macros', {}).get('protein', 0),
                            'carbs': recipe.get('macros', {}).get('carbs', 0),
                            'fats': recipe.get('macros', {}).get('fats', 0),
                            'tags': ', '.join(recipe.get('tags', []))
                        })

                logger.info(f"Exported recipes to CSV: {output_path}")
                return output_path

            elif data_type == "pantry":
                pantry_file = self.data_dir / "Pantry_ingredients.json"
                with open(pantry_file, 'r', encoding='utf-8') as f:
                    pantry = json.load(f)

                with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['name', 'quantity', 'unit', 'expiry_date', 'tags']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    for item in pantry:
                        writer.writerow({
                            'name': item.get('name', ''),
                            'quantity': item.get('default_quantity', 0),
                            'unit': item.get('unit', ''),
                            'expiry_date': item.get('data_expirare', ''),
                            'tags': ', '.join(item.get('tags', []))
                        })

                logger.info(f"Exported pantry to CSV: {output_path}")
                return output_path

        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return None


class DataImporter:
    """Import meal planner data from various formats."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    def import_recipes(self, input_path: Path, merge: bool = True) -> bool:
        """
        Import recipes from JSON file.

        Args:
            input_path: Path to JSON file containing recipes
            merge: If True, merge with existing recipes; if False, replace
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                new_recipes = json.load(f)

            recipes_file = self.data_dir / "recipes.json"

            if merge and recipes_file.exists():
                with open(recipes_file, 'r', encoding='utf-8') as f:
                    existing_recipes = json.load(f)

                # Merge without duplicates (by name)
                existing_names = {r['name'].lower() for r in existing_recipes}
                for recipe in new_recipes:
                    if recipe['name'].lower() not in existing_names:
                        existing_recipes.append(recipe)

                final_recipes = existing_recipes
                logger.info(f"Merged {len(new_recipes)} recipes with existing data")
            else:
                final_recipes = new_recipes
                logger.info(f"Importing {len(new_recipes)} recipes (replace mode)")

            with open(recipes_file, 'w', encoding='utf-8') as f:
                json.dump(final_recipes, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return False

    def import_from_zip(self, zip_path: Path) -> bool:
        """Import all data from a ZIP backup."""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                # Extract all JSON files to data directory
                for file_info in zipf.filelist:
                    if file_info.filename.endswith('.json') and file_info.filename != 'metadata.json':
                        zipf.extract(file_info, self.data_dir)
                        logger.info(f"Extracted {file_info.filename}")

            logger.info(f"Successfully imported data from {zip_path}")
            return True
        except Exception as e:
            logger.error(f"Import from ZIP failed: {e}")
            return False


# CLI interface
if __name__ == "__main__":
    import argparse
    from meal.infra.paths import DATA_DIR

    parser = argparse.ArgumentParser(description='Export/Import Meal Planner data')
    parser.add_argument('action', choices=['export', 'import'], help='Action to perform')
    parser.add_argument('--type', choices=['recipes', 'pantry', 'all'], default='all', help='Data type')
    parser.add_argument('--format', choices=['json', 'csv', 'zip'], default='json', help='Export format')
    parser.add_argument('--file', help='Input/output file path')
    parser.add_argument('--merge', action='store_true', help='Merge with existing data on import')

    args = parser.parse_args()

    if args.action == 'export':
        exporter = DataExporter(DATA_DIR)
        if args.type == 'recipes':
            if args.format == 'csv':
                result = exporter.export_to_csv('recipes')
            else:
                result = exporter.export_recipes(Path(args.file) if args.file else None)
        elif args.type == 'pantry':
            if args.format == 'csv':
                result = exporter.export_to_csv('pantry')
            else:
                result = exporter.export_pantry(Path(args.file) if args.file else None)
        else:
            result = exporter.export_all(Path(args.file) if args.file else None)

        print(f"✓ Exported to: {result}")

    elif args.action == 'import':
        if not args.file:
            print("Error: --file is required for import")
            exit(1)

        importer = DataImporter(DATA_DIR)
        if args.file.endswith('.zip'):
            success = importer.import_from_zip(Path(args.file))
        else:
            success = importer.import_recipes(Path(args.file), merge=args.merge)

        if success:
            print(f"✓ Successfully imported from: {args.file}")
        else:
            print(f"✗ Import failed")

