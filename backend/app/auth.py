from datetime import datetime,timedelta,timezone
from fastapi import Depends,HTTPException
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from jose import jwt,JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db import get_db
from app.models import User
pwd=CryptContext(schemes=["bcrypt"],deprecated="auto"); bearer=HTTPBearer()
def hash_password(x): return pwd.hash(x)
def verify_password(x,y): return pwd.verify(x,y)
def token(u): return jwt.encode({"sub":str(u.id),"role":u.role,"exp":datetime.now(timezone.utc)+timedelta(minutes=settings.access_token_expire_minutes)},settings.jwt_secret,algorithm="HS256")
def current_user(c:HTTPAuthorizationCredentials=Depends(bearer),db:Session=Depends(get_db)):
    try: uid=int(jwt.decode(c.credentials,settings.jwt_secret,algorithms=["HS256"])["sub"])
    except (JWTError,KeyError,ValueError): raise HTTPException(401,"Invalid or expired token")
    u=db.get(User,uid)
    if not u or not u.is_active: raise HTTPException(401,"User unavailable")
    return u
def admin_user(u=Depends(current_user)):
    if u.role!="admin": raise HTTPException(403,"Admin authorization required")
    return u
