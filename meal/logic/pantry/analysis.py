"""Pantry analysis helpers.

Moved from meal.services.pantry_analysis to meal.logic.pantry.analysis.
"""
from __future__ import annotations
from datetime import datetime, date as _date
from typing import List, Dict, Any
from meal.utilities.constants import DATE_FORMAT, LOW_STOCK_THRESHOLD, DAYS_BEFORE_EXPIRY

__all__ = ["compute_expiring_soon", "compute_low_stock", "compute_pantry_snapshots"]

def compute_expiring_soon(ingredients: List[Dict[str, Any]], *, window: int | None = None) -> List[Dict[str, Any]]:
    """Return ingredients expiring in <= window days (including already expired)."""
    expiring_window = window if window is not None else DAYS_BEFORE_EXPIRY
    today = _date.today()
    result: List[Dict[str, Any]] = []
    for ing in ingredients:
        exp_str = ing.get('data_expirare')
        if not exp_str:
            continue
        try:
            exp_date = datetime.strptime(exp_str, DATE_FORMAT).date()
            days_left = (exp_date - today).days
            if days_left <= expiring_window:
                result.append({
                    'name': ing.get('name', ''),
                    'quantity': ing.get('default_quantity', ''),
                    'unit': ing.get('unit', ''),
                    'exp': exp_str,
                    'days_left': days_left,
                    'tag': (ing.get('tags') or [''])[0]
                })
        except Exception:
            continue
    result.sort(key=lambda x: (x['days_left'], x['name']))
    return result

def compute_low_stock(ingredients: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return ingredients whose stock is below or equal to the LOW_STOCK_THRESHOLD for their unit."""
    low: List[Dict[str, Any]] = []
    for ing in ingredients:
        try:
            q = int(ing.get('default_quantity') or 0)
        except Exception:
            q = 0
        unit = ing.get('unit','')
        th = LOW_STOCK_THRESHOLD.get(unit, 0)
        if th > 0 and q <= th:
            low.append({
                'name': ing.get('name',''),
                'quantity': q,
                'unit': unit,
                'threshold': th,
                'tag': (ing.get('tags') or [''])[0]
            })
    low.sort(key=lambda x: (x['quantity'], x['name']))
    return low

def compute_pantry_snapshots(ingredients: List[Dict[str, Any]], *, window: int | None = None):
    exp = compute_expiring_soon(ingredients, window=window)
    low = compute_low_stock(ingredients)
    return exp, low

