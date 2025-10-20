"""Pantry aggregate: collection of Ingredient items with optional expiration tracking."""
import json
import os
from datetime import date
from typing import List, Callable, Optional
from meal.domain.Ingredient import Ingredient
from meal.events.Event_Bus import GLOBAL_EVENT_BUS
from meal.utilities.constants import DAYS_BEFORE_EXPIRY, LOW_STOCK_THRESHOLD


class Pantry:
    def __init__(self):
        self.items: List[Ingredient] = []  # List of PantryItem objects
        self._event_bus = GLOBAL_EVENT_BUS

    # --- Observer helpers -------------------------------------------------
    def set_event_bus(self, bus):
        self._event_bus = bus
        return self

    def _notify_low_stock(self, ingredient: Ingredient):
        self._event_bus.publish("pantry.low_stock", {
            "ingredient": ingredient,
            "remaining": ingredient.default_quantity,
            "threshold": LOW_STOCK_THRESHOLD.get(ingredient.unit, 0)
        })

    def _notify_near_expiry(self, ingredient: Ingredient, days_left: int):
        self._event_bus.publish("pantry.near_expiry", {
            "ingredient": ingredient,
            "days_left": days_left,
            "threshold": DAYS_BEFORE_EXPIRY
        })

    def add_item(self, item: Ingredient):
        '''
        Adds an item to the pantry.
        '''
        self.items.append(item)
        # Evaluate immediately
        self._evaluate_item(item)

    def remove_item(self, item: Ingredient):
        '''
        Removes an item from the pantry.
        '''
        self.items.remove(item)
        self._evaluate_item(item)

    def update_quantity(self, ingredient_name: str, new_quantity: int):
        '''
        Updates the quantity of a specific ingredient in the pantry.
        '''
        if new_quantity < 0:
            raise ValueError(f"Quantity cannot be negative: {new_quantity}")

        for item in self.items:
            if item.name == ingredient_name:
                # Replace absolute set with direct assignment semantics (new total) - keep original pattern
                current = item.default_quantity
                # If user expects 'new_quantity' to overwrite, compute delta
                delta = new_quantity - current
                item.set_quantity(delta)
                self._evaluate_item(item)
                return
        raise ValueError(f"Ingredient '{ingredient_name}' not found in pantry.")

    # --- Evaluation logic --------------------------------------------------
    def _evaluate_item(self, item: Ingredient):
        # Low stock check
        if item.default_quantity <= LOW_STOCK_THRESHOLD.get(item.unit, 0):
            self._notify_low_stock(item)
        # Expiry check
        if getattr(item, 'data_expirare', None):
            today = date.today()
            days_left = (item.data_expirare - today).days
            if days_left <= DAYS_BEFORE_EXPIRY:
                self._notify_near_expiry(item, days_left)

    def scan_and_notify(self):
        for item in self.items:
            self._evaluate_item(item)
        return self

    def get_items(self):
        '''
        Returns the list of pantry items.
        '''
        return self.items

    def __str__(self) -> str:
        items_str = ",\n\t".join(str(item) for item in self.items)
        return f"Items:\n\t{items_str}"

    def __repr__(self) -> str:
        return self.__str__()

    def from_dict(self, data):
        '''
        Populates the Pantry object from a list of dictionaries.
        '''
        for item_data in data:
            # add_item already triggers evaluation
            self.add_item(Ingredient.from_dict(item_data))
        return self

    def to_dict(self):
        '''
        Converts the Pantry object to a list of dictionaries.
        '''
        return [item.to_dict() for item in self.items]

    def read_from_json(self, file_name: str):
        '''
        Reads pantry items from a JSON file and populates the pantry.
        file_name: Name of the JSON file (without .json extension) located in the data directory.
        '''
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, '..', 'data', file_name + '.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                ingredient_data = json.load(f)
            self.from_dict(ingredient_data)
            self.scan_and_notify()
        except Exception as e:
            print(f"Error reading recipes: {e}")
        return self