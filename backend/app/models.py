from datetime import datetime,timezone
from sqlalchemy import String,Integer,Float,Boolean,DateTime,ForeignKey,Text
from sqlalchemy.orm import Mapped,mapped_column,relationship
from app.db import Base
def now(): return datetime.now(timezone.utc)
class User(Base):
    __tablename__="users"; id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(120)); email:Mapped[str]=mapped_column(String(255),unique=True,index=True); password_hash:Mapped[str]=mapped_column(String(255)); role:Mapped[str]=mapped_column(String(20),default="user"); is_active:Mapped[bool]=mapped_column(Boolean,default=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=now)
    profile:Mapped["Profile"]=relationship(back_populates="user",uselist=False,cascade="all,delete-orphan")
    pantry:Mapped[list["PantryItem"]]=relationship(back_populates="user",cascade="all,delete-orphan")
    plans:Mapped[list["MealPlan"]]=relationship(back_populates="user",cascade="all,delete-orphan")
class Profile(Base):
    __tablename__="profiles"; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id"),unique=True); location:Mapped[str]=mapped_column(String(255),default=""); household_size:Mapped[int]=mapped_column(Integer,default=2); budget:Mapped[float]=mapped_column(Float,default=1500); diet:Mapped[str]=mapped_column(String(100),default="Vegetarian"); cuisine:Mapped[str]=mapped_column(String(100),default="Indian"); cooking_time:Mapped[int]=mapped_column(Integer,default=30); likes:Mapped[str]=mapped_column(Text,default=""); dislikes:Mapped[str]=mapped_column(Text,default=""); allergies:Mapped[str]=mapped_column(Text,default="")
    user:Mapped["User"]=relationship(back_populates="profile")
class PantryItem(Base):
    __tablename__="pantry"; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id")); ingredient:Mapped[str]=mapped_column(String(120)); quantity:Mapped[float]=mapped_column(Float); unit:Mapped[str]=mapped_column(String(30),default="unit"); user:Mapped["User"]=relationship(back_populates="pantry")
class MealPlan(Base):
    __tablename__="meal_plans"; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id")); days:Mapped[int]=mapped_column(Integer); estimated_cost:Mapped[float]=mapped_column(Float); budget_status:Mapped[str]=mapped_column(String(20)); plan_json:Mapped[str]=mapped_column(Text); shopping_json:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime,default=now); user:Mapped["User"]=relationship(back_populates="plans")
class Feedback(Base):
    __tablename__="feedback"; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id")); meal_plan_id:Mapped[int]=mapped_column(ForeignKey("meal_plans.id")); rating:Mapped[int]=mapped_column(Integer); reason:Mapped[str]=mapped_column(String(500),default=""); created_at:Mapped[datetime]=mapped_column(DateTime,default=now)
class Recipe(Base):
    __tablename__="recipes"; id:Mapped[int]=mapped_column(primary_key=True); title:Mapped[str]=mapped_column(String(180),unique=True); meal_type:Mapped[str]=mapped_column(String(50)); cuisine:Mapped[str]=mapped_column(String(80)); diet:Mapped[str]=mapped_column(String(80)); cooking_time:Mapped[int]=mapped_column(Integer); calories:Mapped[int]=mapped_column(Integer,default=0); ingredients_json:Mapped[str]=mapped_column(Text); instructions:Mapped[str]=mapped_column(Text); active:Mapped[bool]=mapped_column(Boolean,default=True)
