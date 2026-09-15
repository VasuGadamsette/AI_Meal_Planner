from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.api.rag import router as rag_router
from app.db import Base, SessionLocal, engine
from app.seed import seed

app = FastAPI(
    title="MealMate AI Meal Planner POC",
    version="2.0.0",
    description="POC: FastAPI + LangGraph + LangChain + Groq + ChromaDB RAG",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed(db)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(admin_router)
app.include_router(rag_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "mealmate-backend"}

