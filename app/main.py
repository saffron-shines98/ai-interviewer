from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401 - registers SQLAlchemy models for create_all
from app.database import engine, Base
from app.routes import resumes, sessions, answers, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="AI Interviewer", lifespan=lifespan)

app.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(answers.router, prefix="/answers", tags=["answers"])
app.include_router(ws.router, tags=["websocket"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
