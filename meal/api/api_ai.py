from urllib import response
import os
import logging
from openai import OpenAI
from meal.domain.Recipe import Recipe
from meal.infra.Recipe_Repository import reading_from_recipes
from meal.utilities.constants import PRROMPT_TEMPLATE, RECIPE_JSON_FORMAT
import json
import re
from json import JSONDecodeError
from typing import Optional

logger = logging.getLogger(__name__)


def _get_openai_client():
    """Return an OpenAI client if OPENAI_API_KEY is set, otherwise None."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def de_test():
    """Try to call the OpenAI responses API if API key is configured.

    If no API key is present this function logs a warning and returns None so
    tests and local runs don't crash.
    """
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

def create_recipe_from_ai(prompt: str='') -> Recipe | None:
    """Create a Recipe object from an AI-generated response based on the prompt.

    If no API key is present this function logs a warning and returns None.
    """
    client = _get_openai_client()
    if client is None:
        logger.warning("OPENAI_API_KEY not set — cannot create recipe from AI.")
        return None

    if not prompt:
        try:
            recipes = reading_from_recipes()
            items = recipes.values() if isinstance(recipes, dict) else (
            recipes if isinstance(recipes, (list, tuple)) else ([recipes] if recipes is not None else [])
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
            prompt = prompt + " Make a different recipe that is not listed here."
        except Exception:
            logger.exception("Failed to build recipe names string from repository")
            prompt = ""

    response = client.responses.create(
        model="gpt-4o-mini",
        input= prompt + PRROMPT_TEMPLATE + RECIPE_JSON_FORMAT,
    )

    recipe_data = (response.output_text or "").strip()
    if not recipe_data:
        logger.warning("AI returned empty recipe data")
        return None

    # Try direct JSON parse first
    try:
        parsed = json.loads(recipe_data)
        return Recipe.from_dict(parsed)
    except JSONDecodeError:
        # Strip code fences and try to extract the first JSON object/array from the text
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
                # Dump the raw problematic output for debugging
                try:
                    with open(os.path.join(os.path.dirname(__file__), '..', 'data', 'ai_last_raw.txt'), 'w', encoding='utf-8') as f:
                        f.write(recipe_data)
                except Exception:
                    logger.exception("Failed to write ai_last_raw.txt")

                # As a last resort, attempt to ask the model to reformat the output as strict JSON
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

                return None

        logger.exception("AI output is not valid JSON and no JSON substring found")
        return None


def _strip_code_fences(text: str) -> str:
    """Remove common markdown code fences and leading/trailing whitespace."""
    # remove ```json ... ``` or ``` ... ```
    text = re.sub(r"```(?:json)?\n(.*?)```", r"\1", text, flags=re.S)
    # remove single-line fences like `...`
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return text.strip()


def _remove_trailing_commas(text: str) -> str:
    """Remove common trailing commas in JSON-like text to help json.loads succeed.

    This uses regex to remove commas before closing } or ]. It's not a full JSON
    sanitizer but helps for typical model mistakes.
    """
    # remove trailing commas like ,\n}  or ,\n]
    text = re.sub(r",\s*(\}|\])", r"\1", text)
    return text


def _extract_json_by_balancing(text: str) -> Optional[str]:
    """Extract the first JSON object/array by balancing braces/brackets.

    This scans the text and returns a substring that starts with '{' or '[' and
    ends with the matching closing brace/bracket, taking care to ignore
    braces inside JSON strings.
    """
    start = None
    stack = []
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if ch == '"' and not escape:
            in_string = not in_string
        if in_string and ch == '\\' and not escape:
            escape = True
            continue
        else:
            escape = False

        if not in_string:
            if ch == '{' or ch == '[':
                if start is None:
                    start = i
                stack.append(ch)
            elif ch == '}' or ch == ']':
                if not stack:
                    continue
                opening = stack.pop()
                if ((opening == '{' and ch != '}') or
                        (opening == '[' and ch != ']')):
                    # mismatched pair; abort
                    return None
                if not stack and start is not None:
                    return text[start:i+1]
    return None


def _request_json_fix(client: OpenAI, previous_output: str) -> Optional[str]:
    """Ask the model to reformat previous_output as a strict JSON object.

    Returns the model's output text if provided, otherwise None.
    """
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
