import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import current_user
from app.ai import generate
from app.db import get_db
from app.models import Feedback, MealPlan, PantryItem, Profile
from app.planner import build, status
from app.schemas import FeedbackIn, PantryIn, PlanRequest, ProfileIn

router = APIRouter(prefix="/api", tags=["user"])


def profile_dict(p):
    return {k: v for k, v in p.__dict__.items() if not k.startswith("_")}


@router.get("/profile")
def profile(u=Depends(current_user), db: Session = Depends(get_db)):
    p = u.profile or Profile(user_id=u.id)
    db.add(p)
    db.commit()
    db.refresh(p)
    return profile_dict(p)


@router.put("/profile")
def update_profile(x: ProfileIn, u=Depends(current_user), db: Session = Depends(get_db)):
    p = u.profile or Profile(user_id=u.id)
    for k, v in x.model_dump().items():
        setattr(p, k, v)
    db.add(p)
    db.commit()
    db.refresh(p)
    return profile_dict(p)


@router.get("/pantry")
def pantry(u=Depends(current_user)):
    return [{"id": x.id, "ingredient": x.ingredient, "quantity": x.quantity, "unit": x.unit} for x in u.pantry]


@router.post("/pantry")
def add_pantry(x: PantryIn, u=Depends(current_user), db: Session = Depends(get_db)):
    p = PantryItem(user_id=u.id, **x.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, **x.model_dump()}


@router.delete("/pantry/{item_id}")
def remove_pantry(item_id: int, u=Depends(current_user), db: Session = Depends(get_db)):
    p = db.query(PantryItem).filter_by(id=item_id, user_id=u.id).first()
    if not p:
        raise HTTPException(404, "Pantry item not found")
    db.delete(p)
    db.commit()
    return {"ok": True}


@router.post("/plans/generate")
def generate_plan(x: PlanRequest, u=Depends(current_user), db: Session = Depends(get_db)):
    try:
        pantry_items = [
            {"ingredient": p.ingredient, "quantity": p.quantity, "unit": p.unit}
            for p in u.pantry
        ]
        meals, warnings = generate(x, pantry_items)
        if not meals:
            raise HTTPException(422, "No meal plan could be generated.")

        shopping, total = build(meals, pantry_items, x.household_size)
        budget_status = status(total, x.budget)
        payload = {
            "days": x.days,
            "household_size": x.household_size,
            "budget": x.budget,
            "meals": meals,
            "rag": {
                "source": "ChromaDB",
                "retrieved_recipes": len({m["recipe"]["title"] for m in meals}),
            },
            "warnings": warnings,
        }
        row = MealPlan(
            user_id=u.id,
            days=x.days,
            estimated_cost=total,
            budget_status=budget_status,
            plan_json=json.dumps(payload, ensure_ascii=False),
            shopping_json=json.dumps(shopping, ensure_ascii=False),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {
            "id": row.id,
            "plan": payload,
            "shopping": shopping,
            "estimated_cost": total,
            "budget_status": budget_status,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Meal plan generation failed: {e}")


@router.get("/plans")
def plans(u=Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(MealPlan).filter_by(user_id=u.id).order_by(MealPlan.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "days": r.days,
            "estimated_cost": r.estimated_cost,
            "budget_status": r.budget_status,
            "created_at": r.created_at.isoformat(),
            "plan": json.loads(r.plan_json),
            "shopping": json.loads(r.shopping_json),
        }
        for r in rows
    ]


@router.get("/plans/{plan_id}")
def get_plan(plan_id: int, u=Depends(current_user), db: Session = Depends(get_db)):
    row = db.query(MealPlan).filter_by(id=plan_id, user_id=u.id).first()
    if not row:
        raise HTTPException(404, "Plan not found")
    return {
        "id": row.id,
        "days": row.days,
        "estimated_cost": row.estimated_cost,
        "budget_status": row.budget_status,
        "plan": json.loads(row.plan_json),
        "shopping": json.loads(row.shopping_json),
        "created_at": row.created_at.isoformat(),
    }


@router.get("/recipes")
def recipes():
    from app.rag.service import all_recipes
    return all_recipes()


@router.get("/recipes/search")
def recipe_search(q: str, k: int = 8):
    from app.rag.service import retrieve
    docs = retrieve(q, max(1, min(k, 20)))
    return [{"title": d.metadata.get("title"), "content": d.page_content} for d in docs]


@router.get("/recipes/{title}")
def recipe_detail(title: str):
    from app.rag.service import get_recipe
    recipe = get_recipe(title)
    if not recipe:
        raise HTTPException(404, "Recipe not found")
    return recipe


@router.post("/feedback")
def feedback(x: FeedbackIn, u=Depends(current_user), db: Session = Depends(get_db)):
    p = db.query(MealPlan).filter_by(id=x.meal_plan_id, user_id=u.id).first()
    if not p:
        raise HTTPException(404, "Plan not found")
    db.add(Feedback(user_id=u.id, **x.model_dump()))
    db.commit()
    return {"ok": True}
