import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, HTTPException, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.models import Resume, InterviewSession, Question
from app.schemas import ResumeOut
from app.tasks import _process_resume, process_resume_task

router = APIRouter()

UPLOAD_DIR = Path("media/resumes")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@router.post("/", response_model=ResumeOut)
async def upload_resume(file: UploadFile, db: AsyncSession = Depends(get_db)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type {suffix}. Use PDF or DOCX.")

    saved_name = f"{uuid.uuid4().hex}{suffix}"
    saved_path = UPLOAD_DIR / saved_name

    with saved_path.open("wb") as out_file:
        shutil.copyfileobj(file.file, out_file)

    resume = Resume(file_path=str(saved_path), status="uploaded")
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    if settings.process_tasks_inline:
        await _process_resume(resume.id)
        await db.refresh(resume)
    else:
        process_resume_task.delay(resume.id)

    return await _build_resume_out(db, resume.id)


@router.get("/{resume_id}", response_model=ResumeOut)
async def get_resume_status(resume_id: int, db: AsyncSession = Depends(get_db)):
    return await _build_resume_out(db, resume_id)


async def _build_resume_out(db: AsyncSession, resume_id: int) -> ResumeOut:
    resume = await db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(404, "Resume not found")

    session_id = None
    question_count = None

    result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.resume_id == resume.id)
        .order_by(InterviewSession.id.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()
    if session is not None:
        session_id = session.id
        count_result = await db.execute(
            select(func.count(Question.id)).where(Question.session_id == session.id)
        )
        question_count = count_result.scalar_one()

    return ResumeOut(
        id=resume.id,
        status=resume.status,
        error_message=resume.error_message,
        extracted_skills=resume.extracted_skills,
        session_id=session_id,
        question_count=question_count,
    )
