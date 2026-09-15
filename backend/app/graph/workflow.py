import json
from typing import Any, TypedDict

from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.core.config import settings
from app.rag.service import retrieve, get_recipe


class MealSelection(BaseModel):
    day: int
    meal_type: str
    recipe_title: str
    reason: str = ""


class MealSelectionList(BaseModel):
    meals: list[MealSelection] = Field(
        default_factory=list
    )


class PlanState(TypedDict, total=False):
    request: dict[str, Any]
    pantry: list[dict[str, Any]]
    retrieved: list[dict[str, Any]]
    meals: list[dict[str, Any]]
    errors: list[str]
    final_meals: list[dict[str, Any]]


MEAL_TYPES = [
    "Breakfast",
    "Lunch",
    "Dinner",
]


def _query(
    request: dict[str, Any],
    pantry: list[dict[str, Any]]
) -> str:

    pantry_text = ", ".join(
        x.get("ingredient", "")
        for x in pantry
    )

    return (
        f"{request.get('days', 3)} day meal plan "
        f"for {request.get('household_size', 2)} people. "

        f"Diet: {request.get('diet', '')}. "

        f"Cuisine: {request.get('cuisine', '')}. "

        f"Cooking time: "
        f"{request.get('cooking_time', 30)} minutes. "

        f"Likes: {request.get('likes', '')}. "

        f"Dislikes: "
        f"{request.get('dislikes', '')}. "

        f"Allergies: "
        f"{request.get('allergies', '')}. "

        f"Pantry ingredients: {pantry_text}"
    )


def retrieve_agent(
    state: PlanState
) -> PlanState:

    request = state["request"]

    pantry = state.get(
        "pantry",
        []
    )

    diet = str(
        request.get(
            "diet",
            ""
        )
    ).strip().lower()

    cuisine = str(
        request.get(
            "cuisine",
            ""
        )
    ).strip()

    max_time = int(
        request.get(
            "cooking_time",
            180
        )
    )

    docs = retrieve(
        _query(
            request,
            pantry
        ),
        k=30,
        cuisine=cuisine,
        diet=diet,
        max_cooking_time=max_time,
    )

    recipes: list[
        dict[str, Any]
    ] = []

    seen: set[str] = set()

    allergy_text = str(
        request.get(
            "allergies",
            ""
        )
    ).lower()

    allergies = {
        x.strip()
        for x in allergy_text
        .replace(";", ",")
        .split(",")
        if x.strip()
    }

    dislikes_text = str(
        request.get(
            "dislikes",
            ""
        )
    ).lower()

    dislikes = {
        x.strip()
        for x in dislikes_text
        .replace(";", ",")
        .split(",")
        if x.strip()
    }

    for doc in docs:

        title = str(
            doc.metadata.get(
                "title",
                ""
            )
        )

        recipe = get_recipe(title)

        if not recipe:
            continue

        title_key = title.lower()

        if title_key in seen:
            continue

        ingredients = " ".join(
            str(
                x.get(
                    "ingredient",
                    ""
                )
            )
            for x in recipe.get(
                "ingredients",
                []
            )
            if isinstance(x, dict)
        ).lower()

        recipe_diet = str(
            recipe.get(
                "diet",
                ""
            )
        ).lower()

        # Diet

        diet_ok = (
            not diet
            or diet in (
                "any",
                "all"
            )
            or diet in recipe_diet
            or recipe_diet in (
                "any",
                "all"
            )
        )

        # Allergies

        allergy_ok = not any(
            allergy in ingredients
            or allergy in title.lower()
            for allergy in allergies
        )

        # Dislikes

        dislike_ok = not any(
            dislike in ingredients
            or dislike in title.lower()
            for dislike in dislikes
        )

        # Cooking time

        try:
            recipe_time = int(
                recipe.get(
                    "cooking_time",
                    999
                )
            )
        except (
            TypeError,
            ValueError
        ):
            recipe_time = 999

        time_ok = (
            recipe_time <= max_time
        )

        if (
            diet_ok
            and allergy_ok
            and dislike_ok
            and time_ok
        ):

            recipes.append(recipe)
            seen.add(title_key)

    # If strict filtering returns too few recipes,
    # use semantic results while still respecting allergies.

    minimum_pool = max(
        9,
        request.get("days", 3) * 3
    )

    if len(recipes) < minimum_pool:

        for doc in docs:

            title = str(
                doc.metadata.get(
                    "title",
                    ""
                )
            )

            recipe = get_recipe(title)

            if not recipe:
                continue

            title_key = title.lower()

            if title_key in seen:
                continue

            ingredients = " ".join(
                str(
                    x.get(
                        "ingredient",
                        ""
                    )
                )
                for x in recipe.get(
                    "ingredients",
                    []
                )
                if isinstance(x, dict)
            ).lower()

            allergy_ok = not any(
                allergy in ingredients
                or allergy in title.lower()
                for allergy in allergies
            )

            if allergy_ok:

                recipes.append(recipe)
                seen.add(title_key)

            if len(recipes) >= minimum_pool:
                break

    return {
        "retrieved": recipes,
        "errors": []
    }


def planning_agent(
    state: PlanState
) -> PlanState:

    request = state["request"]

    pool = state.get(
        "retrieved",
        []
    )

    days = int(
        request.get(
            "days",
            3
        )
    )

    target = days * 3

    if not pool:

        return {
            "meals": [],
            "errors": [
                "No recipes were retrieved from ChromaDB."
            ]
        }

    if not settings.groq_api_key:

        return {
            "meals": _deterministic_plan(
                pool,
                days
            ),
            "errors": [
                "GROQ_API_KEY is not configured; "
                "used deterministic POC fallback."
            ]
        }

    llm = ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0.2,
    ).with_structured_output(
        MealSelectionList,
        method="json_schema"
    )

    prompt = f"""
You are the meal planning agent in a RAG POC.

Select ONLY recipe titles from the retrieved
recipe pool below.

Create exactly {target} meal slots.

Every day must contain:

Breakfast
Lunch
Dinner

Respect:

- diet
- allergies
- dislikes
- cooking time
- cuisine

Prefer:

- variety
- ingredient reuse
- pantry usage

Do not invent recipes.

Do not invent ingredients.

Do not invent nutrition.

Do not invent instructions.

USER REQUIREMENTS:

{json.dumps(
    request,
    ensure_ascii=False
)}

RETRIEVED RECIPE POOL:

{json.dumps(
    pool,
    ensure_ascii=False
)}
"""

    try:

        result = llm.invoke(prompt)

        meals = [
            m.model_dump()
            for m in result.meals
        ]

        allowed = {
            r["title"].lower()
            for r in pool
        }

        meals = [
            m
            for m in meals
            if m["recipe_title"].lower()
            in allowed
        ]

        if len(meals) != target:

            return {
                "meals": _deterministic_plan(
                    pool,
                    days
                ),
                "errors": [
                    "LLM output failed slot validation; "
                    "used deterministic fallback."
                ]
            }

        return {
            "meals": meals,
            "errors": []
        }

    except Exception as exc:

        return {
            "meals": _deterministic_plan(
                pool,
                days
            ),
            "errors": [
                f"Groq planning fallback: {exc}"
            ]
        }


def validate_agent(
    state: PlanState
) -> PlanState:

    request = state["request"]

    meals = state.get(
        "meals",
        []
    )

    pool_titles = {
        r["title"].lower()
        for r in state.get(
            "retrieved",
            []
        )
    }

    expected = (
        request.get(
            "days",
            3
        ) * 3
    )

    errors = list(
        state.get(
            "errors",
            []
        )
    )

    if len(meals) != expected:

        errors.append(
            f"Expected {expected} meals "
            f"but received {len(meals)}."
        )

    for meal in meals:

        if (
            meal["recipe_title"].lower()
            not in pool_titles
        ):

            errors.append(
                "Recipe not grounded in "
                f"retrieved pool: "
                f"{meal['recipe_title']}"
            )

    return {
        "errors": errors
    }


def enrich_agent(
    state: PlanState
) -> PlanState:

    recipes = {
        r["title"].lower(): r
        for r in state.get(
            "retrieved",
            []
        )
    }

    enriched = []

    for meal in state.get(
        "meals",
        []
    ):

        recipe = recipes.get(
            meal["recipe_title"].lower()
        )

        if not recipe:
            continue

        enriched.append(
            {
                "day": meal["day"],
                "meal_type": meal["meal_type"],
                "recipe": recipe,
                "reason": meal.get(
                    "reason",
                    "RAG-grounded recipe selected "
                    "for the meal plan."
                ),
            }
        )

    return {
        "final_meals": enriched
    }


def _deterministic_plan(
    pool: list[dict[str, Any]],
    days: int
) -> list[dict[str, Any]]:

    result = []

    for day in range(
        1,
        days + 1
    ):

        for index, meal_type in enumerate(
            MEAL_TYPES
        ):

            recipe = pool[
                (day - 1 + index)
                % len(pool)
            ]

            result.append(
                {
                    "day": day,
                    "meal_type": meal_type,
                    "recipe_title": recipe["title"],
                    "reason": (
                        "Selected from the "
                        "retrieved recipe pool."
                    ),
                }
            )

    return result


def build_graph():

    graph = StateGraph(
        PlanState
    )

    graph.add_node(
        "recipe_retrieval_agent",
        retrieve_agent
    )

    graph.add_node(
        "meal_planning_agent",
        planning_agent
    )

    graph.add_node(
        "validation_agent",
        validate_agent
    )

    graph.add_node(
        "recipe_enrichment_agent",
        enrich_agent
    )

    graph.add_edge(
        START,
        "recipe_retrieval_agent"
    )

    graph.add_edge(
        "recipe_retrieval_agent",
        "meal_planning_agent"
    )

    graph.add_edge(
        "meal_planning_agent",
        "validation_agent"
    )

    graph.add_edge(
        "validation_agent",
        "recipe_enrichment_agent"
    )

    graph.add_edge(
        "recipe_enrichment_agent",
        END
    )

    return graph.compile()


GRAPH = build_graph()


def generate_plan(
    request: dict[str, Any],
    pantry: list[dict[str, Any]]
) -> dict[str, Any]:

    state = GRAPH.invoke(
        {
            "request": request,
            "pantry": pantry
        }
    )

    return {
        "meals": state.get(
            "final_meals",
            []
        ),

        "retrieved_count": len(
            state.get(
                "retrieved",
                []
            )
        ),

        "errors": state.get(
            "errors",
            []
        ),
    }