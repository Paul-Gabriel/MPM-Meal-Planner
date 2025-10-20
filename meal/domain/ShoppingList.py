"""ShoppingList aggregate: list of items to purchase (extends Pantry for reuse)."""

from meal.domain.Ingredient import Ingredient
from meal.domain.Pantry import Pantry


class ShoppingList(Pantry):
    def __init__(self):
        super().__init__()

    def add_item(self, item: Ingredient):
        '''
        Adds an item to the shopping list.
        '''
        super().add_item(item)

    def remove_item(self, item: Ingredient):
        '''
        Removes an item from the shopping list.
        '''
        super().remove_item(item)

    def get_items(self):
        '''
        Returns the list of shopping list items.
        '''
        return super().get_items()
    
    def copy_from_pantry(self, pantry: Pantry):
        '''
        Copies items from the pantry to the shopping list.
        '''
        self.items = pantry.get_items().copy()
    
    def __str__(self) -> str:  
        return f"Shopping List {super().__str__()}"

    def __repr__(self) -> str:  
        return self.__str__()