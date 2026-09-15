"""Download a public Indian recipe dataset and prepare it for the MealMate RAG POC.

This is a POC ingestion script. Review dataset licensing before any commercial use.
"""
import argparse
import json
import re
from pathlib import Path

from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "data" / "recipes_catalog.json"


def clean(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def parse_ingredients(raw: str) -> list[dict]:
    items = []
    for part in clean(raw).split(","):
        part = clean(part)
        if not part:
            continue
        items.append({"ingredient": part, "quantity": 1, "unit": "item", "raw": part})
    return items


def normalize(row, idx):
    title = clean(row.get("TranslatedRecipeName") or row.get("RecipeName"))
    ingredients = row.get("TranslatedIngredients") or row.get("Ingredients") or ""
    instructions = clean(row.get("TranslatedInstructions") or row.get("Instructions"))
    cuisine = clean(row.get("Cuisine")) or "Indian"
    course = clean(row.get("Course"))
    diet = clean(row.get("Diet")) or "Any"
    total = int(row.get("TotalTimeInMins") or 0)
    if total <= 0:
        prep = int(row.get("PrepTimeInMins") or 0)
        cook = int(row.get("CookTimeInMins") or 0)
        total = prep + cook
    return {
        "id": f"hf-indian-{idx}",
        "title": title,
        "meal_type": course or "Main",
        "cuisine": cuisine,
        "diet": diet,
        "cooking_time": max(total, 1),
        "calories": 0,
        "ingredients": parse_ingredients(ingredients),
        "instructions": instructions,
        "source": "HuggingFace: Anupam007/Indian_recipe",
        "source_url": clean(row.get("URL")),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5000)
    args = parser.parse_args()

    print("Downloading recipe dataset from Hugging Face...")
    ds = load_dataset("Anupam007/Indian_recipe", split="train")
    rows = []
    seen = set()
    for idx, row in enumerate(ds):
        recipe = normalize(row, idx)
        if not recipe["title"] or not recipe["instructions"]:
            continue
        key = recipe["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        rows.append(recipe)
        if len(rows) >= args.limit:
            break

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(rows)} recipes to {OUT}")
    print("Next: python -m scripts.rebuild_chroma")


if __name__ == "__main__":
    main()
