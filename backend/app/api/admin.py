from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User,Recipe,MealPlan,Feedback
from app.auth import admin_user
router=APIRouter(prefix="/api/admin",tags=["admin"])
@router.get("/overview")
def overview(a=Depends(admin_user),db:Session=Depends(get_db)): return {"users":db.query(User).count(),"active_users":db.query(User).filter_by(is_active=True).count(),"plans":db.query(MealPlan).count(),"recipes":db.query(Recipe).count(),"feedback":db.query(Feedback).count()}
@router.get("/users")
def users(a=Depends(admin_user),db:Session=Depends(get_db)): return [{"id":u.id,"name":u.name,"email":u.email,"role":u.role,"active":u.is_active} for u in db.query(User).all()]
@router.get("/recipes")
def recipes(a=Depends(admin_user),db:Session=Depends(get_db)): return [{"id":r.id,"title":r.title,"meal_type":r.meal_type,"cuisine":r.cuisine,"active":r.active} for r in db.query(Recipe).all()]
@router.patch("/users/{uid}/active")
def toggle(uid:int,active:bool,a=Depends(admin_user),db:Session=Depends(get_db)):
    u=db.get(User,uid)
    if not u: raise HTTPException(404,"User not found")
    u.is_active=active; db.commit(); return {"ok":True}
