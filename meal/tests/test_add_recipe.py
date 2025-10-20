import json
import pytest
from httpx import AsyncClient
from meal.api.routes import add


@pytest.mark.asyncio
async def test_add_recipe_and_prevent_duplicate(tmp_path, monkeypatch):
    """Test adding a recipe and preventing a duplicate with the same name."""

    # Use a temporary file for recipes.json (don't alter the real one)
    fake_recipes = tmp_path / "recipes.json"
    monkeypatch.setattr(add, "RECIPES_FILE", str(fake_recipes))

    # === 1. First add (should succeed) ===
    async with AsyncClient(app=add.app, base_url="http://test") as ac:
        resp1 = await ac.post(
            "/recipes",
            data={
                "name": "Pizza Test",
                "servings": 2,
                "ingredients": json.dumps([
                    {"name": "Cheese", "default_quantity": 100, "unit": "g"}
                ]),
                "steps": "1. Add cheese\n2. Bake",
                "tags": "Italian, test",
            },
        )
    assert resp1.status_code == 200, resp1.text
    data1 = resp1.json()
    assert data1["status"] == "success"

    # === 2. Second add with same name (should be rejected) ===
    async with AsyncClient(app=add.app, base_url="http://test") as ac:
        resp2 = await ac.post(
            "/recipes",
            data={
                "name": "Pizza Test",
                "servings": 2,
                "ingredients": json.dumps([
                    {"name": "Cheese", "default_quantity": 50, "unit": "g"}
                ]),
                "steps": "Same steps",
                "tags": "duplicate",
            },
        )
    assert resp2.status_code == 400
    data2 = resp2.json()
    assert data2["error"] == "Recipe with this name already exists"
