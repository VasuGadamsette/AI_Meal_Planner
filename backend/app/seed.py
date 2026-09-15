import json
from pathlib import Path
from app.models import User,Profile,Recipe
from app.auth import hash_password
from app.core.config import settings
DATA=Path(__file__).resolve().parents[1]/"data"/"recipes.json"
def seed(db):
    if not db.query(Recipe).first():
        for r in json.loads(DATA.read_text()):
                db.add(
                    Recipe(
                        title=r["title"],
                        meal_type=r["meal_type"],
                        cuisine=r["cuisine"],
                        diet=r["diet"],
                        cooking_time=r["cooking_time"],
                        calories=r["nutrition"]["calories"],
                        ingredients_json=json.dumps(r["ingredients"]),
                        instructions=json.dumps(r["instructions"]),
                    ))   
    if not db.query(User).filter_by(email=settings.admin_email.lower()).first():
        u=User(name="Administrator",email=settings.admin_email.lower(),password_hash=hash_password(settings.admin_password),role="admin"); db.add(u); db.flush(); db.add(Profile(user_id=u.id))
    db.commit()
