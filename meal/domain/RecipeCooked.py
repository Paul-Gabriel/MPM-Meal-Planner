from datetime import date, timedelta
from meal.domain.Ingredient import Ingredient
from typing import List, Optional

class RecipeCooked(Ingredient):
    def __init__(self, name: str = "", default_quantity: int = 0, unit: str = 'pcs',
                 data_expirare: Optional[date] = None, tags: Optional[List[str]] = None, kallories: int = 0):
        if data_expirare is None:
            data_expirare = date.today() + timedelta(days=5)
        super().__init__(name, unit, default_quantity, data_expirare, tags or [])
        self.kallories = kallories

    def __str__(self) -> str:
        return f"{super().__str__()} - Kcal: {self.kallories}"

    __repr__ = __str__
