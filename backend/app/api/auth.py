from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User,Profile
from app.schemas import Register,Login
from app.auth import hash_password,verify_password,token,current_user
router=APIRouter(prefix="/api/auth",tags=["auth"])
def out(u): return {"id":u.id,"name":u.name,"email":u.email,"role":u.role}
@router.post("/register")
def register(x:Register,db:Session=Depends(get_db)):
    if db.query(User).filter(User.email==x.email.lower()).first(): raise HTTPException(409,"Email already registered")
    u=User(name=x.name,email=x.email.lower(),password_hash=hash_password(x.password)); db.add(u); db.flush(); db.add(Profile(user_id=u.id)); db.commit()
    return {"access_token":token(u),"token_type":"bearer","user":out(u)}
@router.post("/login")
def login(x:Login,db:Session=Depends(get_db)):
    u=db.query(User).filter(User.email==x.email.lower()).first()
    if not u or not verify_password(x.password,u.password_hash): raise HTTPException(401,"Invalid email or password")
    return {"access_token":token(u),"token_type":"bearer","user":out(u)}
@router.get("/me")
def me(u=Depends(current_user)): return out(u)
