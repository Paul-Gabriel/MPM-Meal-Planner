from pathlib import Path
import json
import re

DATE_OLD_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')

def _convert_to_new_format(date_str: str) -> str:
    if DATE_OLD_PATTERN.match(date_str):
        y, m, d = date_str.split('-')
        return f"{d}-{m}-{y}"  # DD-MM-YYYY
    return date_str

def load_cooked_recipes():
    json_path = (Path(__file__).parent.parent.parent / 'data' / 'Pantry_recipe_cooked.json').resolve()
    with open(json_path, encoding='utf-8') as f:
        cooked = json.load(f)
    changed = False
    for rec in cooked:
        dc = rec.get('date_cooked')
        if isinstance(dc, str):
            new_dc = _convert_to_new_format(dc)
            if new_dc != dc:
                rec['date_cooked'] = new_dc
                changed = True
    if changed:
        # Persist conversion so we only do it once
        save_cooked_recipes(cooked)
    return cooked

def save_cooked_recipes(cooked):
    json_path = (Path(__file__).parent.parent.parent / 'data' / 'Pantry_recipe_cooked.json').resolve()
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(cooked, f, ensure_ascii=False, indent=2)
