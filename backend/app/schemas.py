from pydantic import BaseModel, EmailStr, Field


class Register(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)


class Login(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    location: str = ""
    household_size: int = Field(2, ge=1, le=20)
    budget: float = Field(1500, ge=0)
    diet: str = "Vegetarian"
    cuisine: str = "Indian"
    cooking_time: int = Field(30, ge=5, le=180)
    likes: str = ""
    dislikes: str = ""
    allergies: str = ""


class PantryIn(BaseModel):
    ingredient: str
    quantity: float = Field(1, gt=0)
    unit: str = "unit"


class PlanRequest(ProfileIn):
    days: int = Field(3, ge=1, le=7)


class FeedbackIn(BaseModel):
    meal_plan_id: int
    rating: int = Field(ge=1, le=5)
    reason: str = ""
