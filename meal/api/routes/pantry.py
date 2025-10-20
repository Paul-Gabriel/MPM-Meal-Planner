from pathlib import Path
import json
from meal.infra.paths import PANTRY_FILE

ALLOWED_TAGS = [
    'fruits','vegetables','meat-chicken','meat-beef','meat-pork','pasta','frozen','fish'
    ,'seafood','dairy','cheese','condiment','baking','canned','grains','oil','sauce','spice','other'
]

def _sanitize_tag_list(tag_value):
    if isinstance(tag_value, str):
        candidates = [tag_value]
    elif isinstance(tag_value, list):
        candidates = tag_value
    else:
        candidates = []
    for c in candidates:
        c_norm = str(c).strip().lower()
        if c_norm in ALLOWED_TAGS:
            return [c_norm]
    return ['other']

def _sanitize_ingredient(ing: dict):
    if not isinstance(ing, dict):
        return ing
    ing['tags'] = _sanitize_tag_list(ing.get('tags'))
    for k in ('name','unit','default_quantity','data_expirare'):
        if k not in ing:
            ing[k] = ''
    return ing

def load_ingredients():
    with open(PANTRY_FILE, encoding='utf-8') as f:
        ingredients = json.load(f)
    changed = False
    for ing in ingredients:
        before = json.dumps(ing, sort_keys=True)
        _sanitize_ingredient(ing)
        after = json.dumps(ing, sort_keys=True)
        if before != after:
            changed = True
    if changed:
        save_ingredients(ingredients)
    return ingredients

def save_ingredients(ingredients):
    sanitized = []
    for ing in ingredients:
        if isinstance(ing, dict):
            sanitized.append(_sanitize_ingredient(ing))
    with open(PANTRY_FILE, 'w', encoding='utf-8') as f:
        json.dump(sanitized, f, ensure_ascii=False, indent=2)
