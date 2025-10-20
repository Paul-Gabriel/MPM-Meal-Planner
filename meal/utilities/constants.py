from typing import Final

DATE_FORMAT: Final[str] = "%d-%m-%Y"
DAYS_BEFORE_EXPIRY: Final[int] = 5
LOW_STOCK_THRESHOLD: Final[dict[str, int]] = {"g": 200, "ml": 500, "pcs": 3, "cloves": 2}
PRROMPT_TEMPLATE: Final[str] = (
    """
    Make a recipe in JSON format with the following format: 

    """
)
RECIPE_JSON_FORMAT: Final[str] = (
    """
{
    "name": str,
    "servings": int,
    "ingredients": [
      {
        "name": str,
        "default_quantity": int,
        "unit": str
      },
      {
        "name": str,
        "default_quantity": int,
        "unit": str
      },
    ],
    "steps": [
      str,
      str,
    ],
    "tags": [
        str,
        str,
    ],
    "image": str(food name with _, end format, e.g. pizza_margherita.png),
    "calories_per_serving": int,
    "macros": {
      "protein": int,
      "carbohydrates": int,
      "fats": int
    }
  }
    """
)