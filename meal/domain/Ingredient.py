"""Ingredient domain entity: name, unit, default quantity, optional expiration date, tags."""
from datetime import date, datetime
from meal.utilities.constants import DATE_FORMAT
from typing import List, Optional


class Ingredient:
    def __init__(self, name: str = "", unit: str = "", default_quantity: int = 0,
                 data_expirare: Optional[date] = None, tags: Optional[List[str]] = None):
        # Avoid mutable default arguments
        self.name = name
        self.unit = unit
        self.default_quantity = default_quantity
        self.data_expirare = data_expirare
        self.tags = tags[:] if tags else []

    def set_quantity(self, quantity: int):
        '''Adjusts the quantity by the specified delta (can be negative).'''
        self.default_quantity += quantity

    def __str__(self) -> str:
        parts = [f"{self.name} - {self.default_quantity} {self.unit}"]
        if self.data_expirare:
            parts.append(f"Exp: {self.data_expirare.strftime(DATE_FORMAT)}")
        if self.tags:
            parts.append("Tags: " + ", ".join(self.tags))
        return " - ".join(parts)

    __repr__ = __str__

    @staticmethod
    def from_dict(data):
        '''Creates an Ingredient object from a dictionary. Ignores unknown keys.'''
        d = dict(data) if isinstance(data, dict) else {}
        if "data_expirare" in d and d["data_expirare"] and not isinstance(d["data_expirare"], (datetime, date)):
            try:
                d["data_expirare"] = datetime.strptime(d["data_expirare"], DATE_FORMAT).date()
            except Exception:
                d["data_expirare"] = None
        allowed = {"name","unit","default_quantity","data_expirare","tags"}
        filtered = {k: v for k, v in d.items() if k in allowed}
        filtered.setdefault("name", "")
        filtered.setdefault("unit", "")
        filtered.setdefault("default_quantity", 0)
        filtered.setdefault("tags", [])
        return Ingredient(**filtered)

    def to_dict(self):
        '''Converts the Ingredient object to a dictionary for JSON persistence.'''
        if isinstance(self.data_expirare, (datetime, date)):
            exp_val = self.data_expirare.strftime(DATE_FORMAT)
        else:
            exp_val = self.data_expirare if isinstance(self.data_expirare, str) else ""
        return {
            "name": self.name,
            "unit": self.unit,
            "default_quantity": self.default_quantity,
            "data_expirare": exp_val,
            "tags": self.tags
        }