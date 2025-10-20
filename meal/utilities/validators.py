"""
Input validation schemas using Pydantic for better data integrity.
"""
from pydantic import BaseModel, Field, validator, field_validator
from typing import List, Optional
from datetime import date

class IngredientInput(BaseModel):
    """Schema for ingredient input validation."""
    name: str = Field(..., min_length=1, max_length=100)
    unit: str = Field(..., min_length=1, max_length=20)
    default_quantity: int = Field(..., ge=0, le=100000)
    data_expirare: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    @field_validator('name', 'unit')
    @classmethod
    def strip_whitespace(cls, v):
        """Remove leading/trailing whitespace."""
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Ensure tags are non-empty strings."""
        return [tag.strip() for tag in v if tag and tag.strip()]


class RecipeInput(BaseModel):
    """Schema for recipe input validation."""
    name: str = Field(..., min_length=3, max_length=200)
    servings: int = Field(..., ge=1, le=50)
    ingredients: List[IngredientInput]
    steps: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    image: Optional[str] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate recipe name."""
        if not v.strip():
            raise ValueError('Recipe name cannot be empty')
        return v.strip()

    @field_validator('ingredients')
    @classmethod
    def validate_ingredients(cls, v):
        """Ensure recipe has at least one ingredient."""
        if not v:
            raise ValueError('Recipe must have at least one ingredient')
        return v

    @field_validator('steps')
    @classmethod
    def validate_steps(cls, v):
        """Filter out empty steps."""
        return [step.strip() for step in v if step and step.strip()]


class PlanUpdateInput(BaseModel):
    """Schema for meal plan update validation."""
    week: int = Field(..., ge=1, le=53)
    year: int = Field(..., ge=2020, le=2030)
    day: str = Field(..., pattern=r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$')
    slot: str = Field(..., pattern=r'^(breakfast|lunch|dinner)$')
    recipe_name: str = Field(..., min_length=1)


class ShoppingListItemInput(BaseModel):
    """Schema for shopping list item validation."""
    name: str = Field(..., min_length=1, max_length=100)
    unit: str = Field(..., min_length=1, max_length=20)
    quantity: int = Field(..., ge=1)
    data_expirare: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class PantryUpdateInput(BaseModel):
    """Schema for pantry update validation."""
    ingredient_name: str = Field(..., min_length=1)
    new_quantity: int = Field(..., ge=0)

    @field_validator('new_quantity')
    @classmethod
    def validate_quantity(cls, v):
        """Ensure quantity is not negative."""
        if v < 0:
            raise ValueError('Quantity cannot be negative')
        return v


class NutritionGoals(BaseModel):
    """Schema for user nutrition goals."""
    daily_calories: Optional[int] = Field(None, ge=1000, le=5000)
    daily_protein: Optional[int] = Field(None, ge=0, le=500)
    daily_carbs: Optional[int] = Field(None, ge=0, le=1000)
    daily_fats: Optional[int] = Field(None, ge=0, le=300)

    @field_validator('daily_calories', 'daily_protein', 'daily_carbs', 'daily_fats')
    @classmethod
    def round_values(cls, v):
        """Round nutrition values to integers."""
        return int(v) if v is not None else None

