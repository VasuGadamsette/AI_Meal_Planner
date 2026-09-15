import json
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "app" / "data"

DATA = DATA_DIR / "recipes_catalog.json"
FALLBACK_DATA = DATA_DIR / "recipes.json"

CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION = "mealmate_recipes"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _load_rows() -> list[dict[str, Any]]:
    path = DATA if DATA.exists() else FALLBACK_DATA

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def _get_calories(row: dict[str, Any]) -> float:
    """
    Get calories from the recipe.

    Supports:
    - calories
    - nutrition.calories
    """

    calories = row.get("calories")

    try:
        if calories is not None and float(calories) > 0:
            return float(calories)
    except (TypeError, ValueError):
        pass

    nutrition = row.get("nutrition", {})

    if isinstance(nutrition, dict):
        calories = nutrition.get("calories")

        try:
            if calories is not None and float(calories) > 0:
                return float(calories)
        except (TypeError, ValueError):
            pass

    return 0.0


def _normalise_recipe(row: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize recipe data before it is used by the application.
    """

    recipe = dict(row)

    recipe["calories"] = _get_calories(row)

    if "ingredients" not in recipe:
        recipe["ingredients"] = []

    if "instructions" not in recipe:
        recipe["instructions"] = ""

    if "meal_type" not in recipe:
        recipe["meal_type"] = "Main"

    if "cuisine" not in recipe:
        recipe["cuisine"] = ""

    if "diet" not in recipe:
        recipe["diet"] = "Any"

    try:
        recipe["cooking_time"] = int(
            recipe.get("cooking_time", 0) or 0
        )
    except (TypeError, ValueError):
        recipe["cooking_time"] = 0

    return recipe


@lru_cache(maxsize=1)
def embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def _recipe_text(row: dict[str, Any]) -> str:

    recipe = _normalise_recipe(row)

    ingredients = recipe.get("ingredients", [])

    ingredient_text = []

    for item in ingredients:

        if isinstance(item, dict):

            ingredient_text.append(
                f"{item.get('ingredient', '')} "
                f"{item.get('quantity', '')} "
                f"{item.get('unit', '')}"
            )

        else:

            ingredient_text.append(str(item))

    return (
        f"Title: {recipe.get('title', '')}\n"
        f"Meal type: {recipe.get('meal_type', '')}\n"
        f"Cuisine: {recipe.get('cuisine', '')}\n"
        f"Diet: {recipe.get('diet', '')}\n"
        f"Cooking time: {recipe.get('cooking_time', '')} minutes\n"
        f"Calories: {recipe.get('calories', 0)}\n"
        f"Ingredients: {', '.join(ingredient_text)}\n"
        f"Instructions: {recipe.get('instructions', '')}"
    )


def _documents(
    rows: list[dict[str, Any]]
) -> list[Document]:

    docs: list[Document] = []

    for idx, row in enumerate(rows):

        recipe = _normalise_recipe(row)

        title = str(
            recipe.get(
                "title",
                f"Recipe {idx}"
            )
        )

        docs.append(
            Document(
                page_content=_recipe_text(recipe),

                metadata={
                    "recipe_id": str(
                        recipe.get("id", idx)
                    ),

                    "title": title,

                    "meal_type": str(
                        recipe.get(
                            "meal_type",
                            ""
                        )
                    ),

                    "cuisine": str(
                        recipe.get(
                            "cuisine",
                            ""
                        )
                    ),

                    "diet": str(
                        recipe.get(
                            "diet",
                            ""
                        )
                    ),

                    "cooking_time": int(
                        recipe.get(
                            "cooking_time",
                            0
                        ) or 0
                    ),

                    "calories": float(
                        recipe.get(
                            "calories",
                            0
                        ) or 0
                    ),

                    "source": str(
                        recipe.get(
                            "source",
                            "local"
                        )
                    ),
                },
            )
        )

    return docs


@lru_cache(maxsize=1)
def store() -> Chroma:

    CHROMA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    db = Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings(),
        persist_directory=str(CHROMA_DIR),
    )

    if db._collection.count() == 0:

        rows = _load_rows()

        docs = _documents(rows)

        if docs:

            db.add_documents(
                docs,
                ids=[
                    f"recipe-{i}"
                    for i in range(len(docs))
                ],
            )

    return db


def rebuild() -> int:

    store.cache_clear()
    embeddings.cache_clear()

    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)

    CHROMA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    db = Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings(),
        persist_directory=str(CHROMA_DIR),
    )

    rows = _load_rows()

    docs = _documents(rows)

    if docs:

        db.add_documents(
            docs,
            ids=[
                f"recipe-{i}"
                for i in range(len(docs))
            ],
        )

    store.cache_clear()

    return len(docs)


def retrieve(
    query: str,
    k: int = 12,
    cuisine: str | None = None,
    diet: str | None = None,
    max_cooking_time: int | None = None,
    meal_type: str | None = None,
) -> list[Document]:

    fetch_k = min(
        max(k * 5, 30),
        100
    )

    docs = store().similarity_search(
        query,
        k=fetch_k,
    )

    cuisine_value = (
        cuisine or ""
    ).strip().lower()

    diet_value = (
        diet or ""
    ).strip().lower()

    meal_type_value = (
        meal_type or ""
    ).strip().lower()

    filtered: list[Document] = []

    for doc in docs:

        metadata = doc.metadata

        doc_cuisine = str(
            metadata.get(
                "cuisine",
                ""
            )
        ).lower()

        doc_diet = str(
            metadata.get(
                "diet",
                ""
            )
        ).lower()

        doc_meal_type = str(
            metadata.get(
                "meal_type",
                ""
            )
        ).lower()

        try:

            cooking_time = int(
                metadata.get(
                    "cooking_time",
                    999
                )
            )

        except (
            TypeError,
            ValueError
        ):

            cooking_time = 999

        # Cuisine filter

        if cuisine_value:

            cuisine_ok = (
                cuisine_value in doc_cuisine
                or doc_cuisine in cuisine_value
            )

            if not cuisine_ok:
                continue

        # Diet filter

        if diet_value and diet_value not in (
            "any",
            "all"
        ):

            diet_ok = (
                diet_value in doc_diet
                or doc_diet in (
                    "any",
                    "all",
                    ""
                )
            )

            if not diet_ok:
                continue

        # Cooking time filter

        if max_cooking_time is not None:

            if cooking_time > max_cooking_time:
                continue

        # Meal type

        if meal_type_value:

            if (
                meal_type_value not in doc_meal_type
                and doc_meal_type not in (
                    "main",
                    ""
                )
            ):
                continue

        filtered.append(doc)

        if len(filtered) >= k:
            break

    return filtered


def all_recipes() -> list[dict[str, Any]]:

    return [
        _normalise_recipe(row)
        for row in _load_rows()
    ]


def get_recipe(
    title: str
) -> dict[str, Any] | None:

    wanted = title.strip().lower()

    for row in _load_rows():

        recipe = _normalise_recipe(row)

        if (
            str(
                recipe.get(
                    "title",
                    ""
                )
            ).strip().lower()
            == wanted
        ):
            return recipe

    return None


def catalog_status() -> dict[str, Any]:

    rows = _load_rows()

    return {
        "catalog_file": (
            DATA.name
            if DATA.exists()
            else FALLBACK_DATA.name
        ),

        "catalog_recipes": len(rows),

        "chroma_recipes": (
            store()
            ._collection
            .count()
        ),

        "embedding_model": EMBEDDING_MODEL,

        "collection": COLLECTION,
    }