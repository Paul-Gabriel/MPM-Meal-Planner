import os
import re
import json
import logging
from json import JSONDecodeError
from typing import Optional
from openai import OpenAI
from fastapi import APIRouter, HTTPException, Body

from meal.domain.Recipe import Recipe
from meal.infra.Recipe_Repository import reading_from_recipes
from meal.utilities.constants import PRROMPT_TEMPLATE, RECIPE_JSON_FORMAT

logger = logging.getLogger(__name__)


# === Helper: Get OpenAI Client ===
def _get_openai_client():
    """Return an OpenAI client if OPENAI_API_KEY is set, otherwise None."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


# === Test Function ===
def de_test():
    """Try to call the OpenAI API if the key is set."""
    client = _get_openai_client()
    if client is None:
        logger.warning("OPENAI_API_KEY not set — skipping AI call in de_test().")
        return None

    response = client.responses.create(
        model="gpt-4o-mini",
        input="scrie o rețetă pentru o cină sănătoasă folosind pui și legume",
    )

    print(response.output_text)
    return response


# === Recipe Generation ===
def create_recipe_from_ai(prompt: str = "") -> Recipe | None:
    """Create a Recipe object from an AI-generated response based on the prompt."""
    client = _get_openai_client()
    if client is None:
        logger.warning("OPENAI_API_KEY not set — cannot create recipe from AI.")
        return None

    # Dacă promptul e gol, generează din rețetele existente
    if not prompt:
        try:
            recipes = reading_from_recipes()
            items = recipes.values() if isinstance(recipes, dict) else (
                recipes if isinstance(recipes, (list, tuple))
                else ([recipes] if recipes is not None else [])
            )

            names = []
            for r in items:
                if r is None:
                    continue
                if isinstance(r, dict):
                    name = r.get("name") or r.get("title") or r.get("recipe_name")
                else:
                    name = getattr(r, "name", None) or getattr(r, "title", None)
                if name:
                    names.append(str(name))

            prompt = ", ".join(sorted(set(names))) if names else ""
            prompt += " Make a different recipe that is not listed here."
        except Exception:
            logger.exception("Failed to build recipe names string from repository")
            prompt = ""

    # === OpenAI Call ===
    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt + PRROMPT_TEMPLATE + RECIPE_JSON_FORMAT,
    )

    recipe_data = (response.output_text or "").strip()
    if not recipe_data:
        logger.warning("AI returned empty recipe data")
        return None

    # === JSON Parsing ===
    try:
        parsed = json.loads(recipe_data)
        return Recipe.from_dict(parsed)
    except JSONDecodeError:
        recipe_data_stripped = _strip_code_fences(recipe_data)
        recipe_data_clean = _remove_trailing_commas(recipe_data_stripped)
        candidate = _extract_json_by_balancing(recipe_data_clean)

        if candidate:
            try:
                candidate_clean = _remove_trailing_commas(candidate)
                parsed = json.loads(candidate_clean)
                return Recipe.from_dict(parsed)
            except JSONDecodeError:
                logger.exception("Failed to decode extracted JSON from AI output")

    # === Backup: save raw AI response ===
    try:
        with open(os.path.join(os.path.dirname(__file__), '..', 'data', 'ai_last_raw.txt'), 'w', encoding='utf-8') as f:
            f.write(recipe_data)
    except Exception:
        logger.exception("Failed to write ai_last_raw.txt")

    # === Try to fix the JSON via AI ===
    fixed = _request_json_fix(client, recipe_data)
    if fixed:
        try:
            with open(os.path.join(os.path.dirname(__file__), '..', 'data', 'ai_last_fixed.txt'), 'w', encoding='utf-8') as f:
                f.write(fixed)
        except Exception:
            logger.exception("Failed to write ai_last_fixed.txt")

        try:
            fixed_clean = _remove_trailing_commas(_strip_code_fences(fixed))
            parsed = json.loads(fixed_clean)
            return Recipe.from_dict(parsed)
        except JSONDecodeError:
            logger.exception("Fixed AI output still could not be decoded")

    logger.exception("AI output is not valid JSON and no JSON substring found")
    return None


# === Text Cleaning Helpers ===
def _strip_code_fences(text: str) -> str:
    """Remove common markdown code fences and leading/trailing whitespace."""
    text = re.sub(r"```(?:json)?\n(.*?)```", r"\1", text, flags=re.S)
    text = re.sub(r"^```|```$", "", text)
    return text.strip()


def _remove_trailing_commas(text: str) -> str:
    """Remove common trailing commas in JSON-like text to help json.loads succeed."""
    return re.sub(r",\s*(\}|\])", r"\1", text)


def _extract_json_by_balancing(text: str) -> Optional[str]:
    """Extract the first JSON object/array by balancing braces/brackets."""
    start = None
    stack = []
    in_string = False
    escape = False

    for i, ch in enumerate(text):
        if ch == '"' and not escape:
            in_string = not in_string
        if in_string and ch == "\\" and not escape:
            escape = True
            continue
        else:
            escape = False

        if not in_string:
            if ch in "{[":
                if start is None:
                    start = i
                stack.append(ch)
            elif ch in "}]":
                if not stack:
                    continue
                opening = stack.pop()
                if (opening == "{" and ch != "}") or (opening == "[" and ch != "]"):
                    return None
                if not stack and start is not None:
                    return text[start:i + 1]
    return None


def _request_json_fix(client: OpenAI, previous_output: str) -> Optional[str]:
    """Ask the model to reformat previous_output as a strict JSON object."""
    try:
        prompt = (
            "The previous response contained a recipe but was not valid JSON. "
            "Please reformat ONLY the recipe as valid JSON (no surrounding text) using the same keys. "
            "Here is the original output:\n\n" + previous_output
        )
        resp = client.responses.create(model="gpt-4o-mini", input=prompt)
        return (resp.output_text or "").strip()
    except Exception:
        logger.exception("Error while requesting AI to fix JSON formatting")
        return None


# === FastAPI Endpoint ===
router = APIRouter()


@router.post("/generate-recipe-ai")
async def generate_recipe_ai(prompt: str = Body(..., embed=True)):
    try:
        recipe_obj = create_recipe_from_ai(prompt)
        if recipe_obj is None:
            raise HTTPException(status_code=500, detail="AI did not return a valid recipe")

        recipe_dict = recipe_obj.to_dict() if hasattr(recipe_obj, "to_dict") else recipe_obj.__dict__
        return recipe_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
