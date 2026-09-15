import os
from collections import defaultdict

import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

API = os.getenv(
    "MEALMATE_API_URL",
    "http://localhost:8000"
)

st.set_page_config(
    page_title="MealMate POC",
    page_icon="🍲",
    layout="wide"
)


# ============================================================
# HEADER
# ============================================================

st.title("🍲 MealMate — AI Meal Planner POC")

st.caption(
    "FastAPI + LangGraph + ChromaDB + Groq"
)


# ============================================================
# SESSION STATE
# ============================================================

if "token" not in st.session_state:
    st.session_state.token = None

if "user" not in st.session_state:
    st.session_state.user = None

if "plan" not in st.session_state:
    st.session_state.plan = None


# ============================================================
# API HELPER
# ============================================================

def api(
    path,
    method="GET",
    payload=None
):
    """
    Call the FastAPI backend.
    """

    headers = {
        "Content-Type": "application/json"
    }

    if st.session_state.token:
        headers["Authorization"] = (
            f"Bearer {st.session_state.token}"
        )

    try:

        response = requests.request(
            method,
            API + path,
            json=payload,
            headers=headers,
            timeout=180
        )

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            f"Cannot connect to backend: {API}"
        )

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "Backend request timed out."
        )

    if not response.ok:

        try:

            data = response.json()

            detail = data.get(
                "detail",
                response.text
            )

        except Exception:

            detail = response.text

        raise RuntimeError(
            f"{response.status_code}: {detail}"
        )

    try:

        return response.json()

    except Exception:

        raise RuntimeError(
            "Backend returned an invalid JSON response."
        )


# ============================================================
# LOGIN / REGISTER
# ============================================================

if not st.session_state.token:

    tab1, tab2 = st.tabs(
        [
            "Sign in",
            "Create account"
        ]
    )

    # --------------------------------------------------------
    # SIGN IN
    # --------------------------------------------------------

    with tab1:

        st.subheader("Welcome back")

        login_email = st.text_input(
            "Email",
            key="login_email"
        )

        login_password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button(
            "Sign in",
            type="primary",
            use_container_width=True
        ):

            if not login_email or not login_password:

                st.warning(
                    "Please enter email and password."
                )

            else:

                try:

                    data = api(
                        "/api/auth/login",
                        "POST",
                        {
                            "email": login_email,
                            "password": login_password
                        }
                    )

                    st.session_state.token = (
                        data["access_token"]
                    )

                    st.session_state.user = (
                        data["user"]
                    )

                    st.rerun()

                except Exception as e:

                    st.error(str(e))

    # --------------------------------------------------------
    # CREATE ACCOUNT
    # --------------------------------------------------------

    with tab2:

        st.subheader("Create your MealMate account")

        reg_name = st.text_input(
            "Full name",
            key="reg_name"
        )

        reg_email = st.text_input(
            "Email",
            key="reg_email"
        )

        reg_password = st.text_input(
            "Password (8+ characters)",
            type="password",
            key="reg_password"
        )

        if st.button(
            "Create account",
            type="primary",
            use_container_width=True
        ):

            if (
                not reg_name
                or not reg_email
                or not reg_password
            ):

                st.warning(
                    "Please fill all fields."
                )

            elif len(reg_password) < 8:

                st.warning(
                    "Password must contain at least 8 characters."
                )

            else:

                try:

                    data = api(
                        "/api/auth/register",
                        "POST",
                        {
                            "name": reg_name,
                            "email": reg_email,
                            "password": reg_password
                        }
                    )

                    st.session_state.token = (
                        data["access_token"]
                    )

                    st.session_state.user = (
                        data["user"]
                    )

                    st.rerun()

                except Exception as e:

                    st.error(str(e))

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("🍲 MealMate")

    if st.session_state.user:

        st.write(
            f"**{st.session_state.user.get('name', 'User')}**"
        )

        st.caption(
            st.session_state.user.get(
                "email",
                ""
            )
        )

    # --------------------------------------------------------
    # LOGOUT
    # --------------------------------------------------------

    if st.button(
        "Logout",
        use_container_width=True
    ):

        st.session_state.clear()

        st.rerun()

    st.divider()

    # --------------------------------------------------------
    # RAG STATUS
    # --------------------------------------------------------

    st.subheader("RAG Status")

    try:

        rag = api(
            "/api/rag/status"
        )

        st.success(
            "RAG Online"
        )

        st.caption(
            "Vector DB: ChromaDB"
        )

        st.caption(
            f"Catalog recipes: "
            f"{rag.get('catalog_recipes', 0)}"
        )

        st.caption(
            f"Recipes indexed: "
            f"{rag.get('chroma_recipes', 0)}"
        )

        st.caption(
            f"Collection: "
            f"{rag.get('collection', 'N/A')}"
        )

        st.caption(
            f"Embedding: "
            f"{rag.get('embedding_model', 'N/A')}"
        )

    except Exception as e:

        st.error(
            f"RAG status unavailable: {e}"
        )


# ============================================================
# LOAD PROFILE
# ============================================================

try:

    profile = api(
        "/api/profile"
    )

except Exception as e:

    st.error(
        f"Backend unavailable: {e}"
    )

    st.stop()


# ============================================================
# GENERATE PLAN FORM
# ============================================================

st.subheader(
    "🍽️ Generate personalized meal plan"
)

st.write(
    "Choose your preferences and MealMate will retrieve "
    "recipes from ChromaDB and build a meal plan."
)


col1, col2, col3 = st.columns(3)


# ============================================================
# COLUMN 1
# ============================================================

with col1:

    days = st.number_input(
        "Planning period (days)",
        min_value=1,
        max_value=7,
        value=3,
        step=1
    )

    household = st.number_input(
        "Household size",
        min_value=1,
        max_value=20,
        value=int(
            profile.get(
                "household_size",
                2
            )
        ),
        step=1
    )

    budget = st.number_input(
        "Budget (₹)",
        min_value=0.0,
        max_value=100000.0,
        value=float(
            profile.get(
                "budget",
                1500
            )
        ),
        step=100.0
    )


# ============================================================
# COLUMN 2
# ============================================================

with col2:

    diet = st.text_input(
        "Diet",
        value=profile.get(
            "diet",
            "Vegetarian"
        )
    )

    cuisine = st.text_input(
        "Cuisine",
        value=profile.get(
            "cuisine",
            "Indian"
        )
    )

    cooking_time = st.number_input(
        "Max cooking time (min)",
        min_value=5,
        max_value=180,
        value=int(
            profile.get(
                "cooking_time",
                30
            )
        ),
        step=5
    )


# ============================================================
# COLUMN 3
# ============================================================

with col3:

    likes = st.text_input(
        "Likes",
        value=profile.get(
            "likes",
            ""
        )
    )

    dislikes = st.text_input(
        "Foods to avoid",
        value=profile.get(
            "dislikes",
            ""
        )
    )

    allergies = st.text_input(
        "Allergies",
        value=profile.get(
            "allergies",
            ""
        )
    )


# ============================================================
# PANTRY
# ============================================================

st.subheader(
    "🥫 Pantry"
)

pantry_text = st.text_input(
    "Pantry ingredients",
    value="rice, onion, tomato",
    help="Enter ingredients separated by commas."
)


pantry = []

for item in pantry_text.split(","):

    item = item.strip()

    if item:

        pantry.append(
            {
                "ingredient": item,
                "quantity": 1,
                "unit": "unit"
            }
        )


# ============================================================
# GENERATE PLAN
# ============================================================

if st.button(
    "✨ Generate personalized plan",
    type="primary",
    use_container_width=True
):

    request = {

        "days": int(days),

        "household_size": int(
            household
        ),

        "budget": float(
            budget
        ),

        "diet": diet,

        "cuisine": cuisine,

        "cooking_time": int(
            cooking_time
        ),

        "likes": likes,

        "dislikes": dislikes,

        "allergies": allergies,

        "location": ""
    }

    try:

        with st.spinner(
            "Retrieving recipes → "
            "planning with Groq → "
            "validating → "
            "enriching recipes..."
        ):

            # ------------------------------------------------
            # Save profile
            # ------------------------------------------------

            profile_payload = {
                k: request[k]
                for k in request
                if k != "days"
            }

            api(
                "/api/profile",
                "PUT",
                profile_payload
            )

            # ------------------------------------------------
            # Save pantry
            # ------------------------------------------------

            try:

                existing = api(
                    "/api/pantry"
                )

                existing_names = {
                    str(
                        x.get(
                            "ingredient",
                            ""
                        )
                    ).strip().lower()
                    for x in existing
                }

            except Exception:

                existing_names = set()

            for item in pantry:

                ingredient_name = (
                    item["ingredient"]
                    .strip()
                    .lower()
                )

                if (
                    ingredient_name
                    not in existing_names
                ):

                    try:

                        api(
                            "/api/pantry",
                            "POST",
                            item
                        )

                    except Exception:
                        pass

            # ------------------------------------------------
            # Generate plan
            # ------------------------------------------------

            result = api(
                "/api/plans/generate",
                "POST",
                request
            )

            st.session_state.plan = result

        st.success(
            "✅ Meal plan generated successfully!"
        )

    except Exception as e:

        st.error(
            f"Meal plan generation failed: {e}"
        )


# ============================================================
# DISPLAY PLAN
# ============================================================

plan_response = st.session_state.plan


if plan_response:

    st.divider()

    # ========================================================
    # BACKEND ERRORS / WARNINGS
    # ========================================================

    errors = plan_response.get(
        "errors",
        []
    )

    if errors:

        with st.expander(
            "⚠️ Generation information",
            expanded=False
        ):

            for error in errors:

                st.warning(
                    error
                )

    # ========================================================
    # PLAN OBJECT
    # ========================================================

    plan = plan_response.get(
        "plan",
        {}
    )

    if not plan:

        st.error(
            "Backend returned a response without a plan."
        )

        st.json(
            plan_response
        )

        st.stop()

    # ========================================================
    # PLAN SUMMARY
    # ========================================================

    st.subheader(
        "🍽️ Meal List"
    )

    days_value = plan.get(
        "days",
        days
    )

    household_value = plan.get(
        "household_size",
        household
    )

    estimated_cost = plan_response.get(
        "estimated_cost",
        0
    )

    budget_status = plan_response.get(
        "budget_status",
        ""
    )

    st.write(
        f"**{days_value}-day plan** "
        f"• {household_value} people "
        f"• ₹{estimated_cost:.2f} "
        f"• **{budget_status}**"
    )

    # ========================================================
    # RETRIEVAL COUNT
    # ========================================================

    retrieved_count = plan_response.get(
        "retrieved_count"
    )

    if retrieved_count is not None:

        st.caption(
            f"🔎 RAG retrieved "
            f"{retrieved_count} recipe candidates"
        )

    # ========================================================
    # GROUP MEALS BY DAY
    # ========================================================

    meals = plan.get(
        "meals",
        []
    )

    by_day = defaultdict(list)

    for meal in meals:

        by_day[
            meal.get(
                "day",
                1
            )
        ].append(meal)

    # ========================================================
    # DISPLAY EACH DAY
    # ========================================================

    for day in sorted(
        by_day.keys()
    ):

        st.markdown(
            f"## 📅 Day {day}"
        )

        day_meals = by_day[day]

        for meal in day_meals:

            meal_type = meal.get(
                "meal_type",
                "Meal"
            )

            recipe = meal.get(
                "recipe",
                {}
            )

            recipe_title = recipe.get(
                "title",
                "Unknown Recipe"
            )

            with st.expander(
                f"{meal_type} — {recipe_title}",
                expanded=True
            ):

                # ------------------------------------------------
                # Recipe metrics
                # ------------------------------------------------

                c1, c2, c3, c4 = st.columns(4)

                cooking_value = recipe.get(
                    "cooking_time",
                    0
                )

                calories_value = recipe.get(
                    "calories",
                    0
                )

                cuisine_value = recipe.get(
                    "cuisine",
                    ""
                )

                diet_value = recipe.get(
                    "diet",
                    ""
                )

                c1.metric(
                    "Cooking time",
                    f"{cooking_value} min"
                )

                if calories_value:

                    c2.metric(
                        "Calories",
                        f"{calories_value:g}"
                    )

                else:

                    c2.metric(
                        "Calories",
                        "N/A"
                    )

                c3.metric(
                    "Cuisine",
                    cuisine_value
                )

                c4.metric(
                    "Diet",
                    diet_value
                )

                # ------------------------------------------------
                # Recipe information
                # ------------------------------------------------

                st.write(
                    f"**Meal type:** "
                    f"{recipe.get('meal_type', meal_type)}"
                )

                # ------------------------------------------------
                # Ingredients
                # ------------------------------------------------

                st.markdown(
                    "### 🥗 Ingredients"
                )

                ingredients = recipe.get(
                    "ingredients",
                    []
                )

                if ingredients:

                    for ingredient in ingredients:

                        # New catalog format:
                        #
                        # {
                        #   "ingredient": "...",
                        #   "quantity": 1,
                        #   "unit": "item",
                        #   "raw": "..."
                        # }

                        if isinstance(
                            ingredient,
                            dict
                        ):

                            name = ingredient.get(
                                "ingredient",
                                ""
                            )

                            quantity = ingredient.get(
                                "quantity",
                                ""
                            )

                            unit = ingredient.get(
                                "unit",
                                ""
                            )

                            raw = ingredient.get(
                                "raw",
                                ""
                            )

                            if raw:

                                st.write(
                                    f"• {raw}"
                                )

                            else:

                                st.write(
                                    f"• {name} "
                                    f"— {quantity} {unit}"
                                )

                        else:

                            st.write(
                                f"• {ingredient}"
                            )

                else:

                    st.write(
                        "No ingredient information available."
                    )

                # ------------------------------------------------
                # Instructions
                # ------------------------------------------------

                st.markdown(
                    "### 👨‍🍳 Instructions"
                )

                instructions = recipe.get(
                    "instructions",
                    ""
                )

                if isinstance(
                    instructions,
                    list
                ):

                    for index, instruction in enumerate(
                        instructions,
                        start=1
                    ):

                        st.write(
                            f"**{index}.** {instruction}"
                        )

                elif instructions:

                    st.write(
                        instructions
                    )

                else:

                    st.write(
                        "No instructions available."
                    )

                # ------------------------------------------------
                # Source
                # ------------------------------------------------

                source = recipe.get(
                    "source",
                    ""
                )

                source_url = recipe.get(
                    "source_url",
                    ""
                )

                if source:

                    st.caption(
                        f"Source: {source}"
                    )

                if source_url:

                    st.caption(
                        f"Recipe source: {source_url}"
                    )

                # ------------------------------------------------
                # AI Reason
                # ------------------------------------------------

                reason = meal.get(
                    "reason",
                    ""
                )

                if reason:

                    st.info(
                        f"💡 {reason}"
                    )

    # ========================================================
    # SHOPPING LIST
    # ========================================================

    shopping = plan_response.get(
        "shopping",
        []
    )

    if shopping:

        st.divider()

        st.subheader(
            "🛒 Consolidated Shopping List"
        )

        total_cost = 0.0

        for item in shopping:

            ingredient = item.get(
                "ingredient",
                ""
            )

            quantity = item.get(
                "quantity",
                ""
            )

            unit = item.get(
                "unit",
                ""
            )

            estimated_cost = item.get(
                "estimated_cost",
                0
            )

            try:

                estimated_cost_float = float(
                    estimated_cost
                )

            except (
                TypeError,
                ValueError
            ):

                estimated_cost_float = 0.0

            total_cost += (
                estimated_cost_float
            )

            st.write(
                f"• **{ingredient}** "
                f"— {quantity} {unit} "
                f"— ₹{estimated_cost_float:.2f}"
            )

        st.write(
            f"### 💰 Estimated shopping cost: "
            f"₹{total_cost:.2f}"
        )

    # ========================================================
    # DEBUG INFORMATION
    # ========================================================

    with st.expander(
        "🔧 Developer details"
    ):

        st.write(
            f"Retrieved recipes: "
            f"{plan_response.get('retrieved_count', 'N/A')}"
        )

        st.write(
            f"Generated meals: "
            f"{len(meals)}"
        )

        st.json(
            plan_response
        )