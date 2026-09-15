import json
from collections import defaultdict
from pathlib import Path

PRICES = {
    x["ingredient"].lower(): x["unit_price"]
    for x in json.loads((Path(__file__).resolve().parent / "data" / "prices.json").read_text())
}


def build(meals, pantry, people):
    pantry_map = {x["ingredient"].lower(): float(x["quantity"]) for x in pantry}
    need = defaultdict(float)
    units = {}

    for meal in meals:
        recipe = meal["recipe"]
        for item in recipe.get("ingredients", []):
            key = item["ingredient"].lower()
            need[key] += float(item["quantity"]) * people / 2
            units[key] = item.get("unit", "unit")

    shopping = []
    total = 0.0
    for key, quantity in need.items():
        remaining = max(0.0, quantity - pantry_map.get(key, 0.0))
        if remaining <= 0:
            continue
        cost = round(remaining * PRICES.get(key, 50), 2)
        total += cost
        shopping.append({
            "ingredient": key.title(),
            "quantity": round(remaining, 2),
            "unit": units[key],
            "estimated_cost": cost,
        })
    return shopping, round(total, 2)


def status(total: float, budget: float) -> str:
    if total <= budget * 0.9:
        return "UNDER"
    if total <= budget:
        return "NEAR"
    return "OVER"
