from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app import llm
from app.models import InterviewSession, Question, Resume
from app.schemas import QuestionOut, ResumeOut

router = APIRouter()


@router.post("/", response_model=ResumeOut)
async def create_session(resume_id: int, db: AsyncSession = Depends(get_db)):
    resume = await db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(404, "Resume not found")
    if not resume.raw_text or not resume.extracted_skills:
        raise HTTPException(400, "Resume must be processed before creating a session")

    skills = resume.extracted_skills.get("skills", [])
    questions_result = llm.generate_questions(skills, resume.raw_text)

    session = InterviewSession(resume_id=resume.id, status="ready")
    db.add(session)
    await db.flush()

    for order, question in enumerate(questions_result.questions):
        db.add(
            Question(
                session_id=session.id,
                text=question.text,
                skill=question.skill,
                difficulty=question.difficulty,
                rubric={"key_points": question.key_points},
                order=order,
            )
        )

    await db.commit()
    await db.refresh(session)

    return ResumeOut(
        id=resume.id,
        status=resume.status,
        error_message=resume.error_message,
        extracted_skills=resume.extracted_skills,
        session_id=session.id,
        question_count=len(questions_result.questions),
    )


@router.get("/{session_id}/questions", response_model=List[QuestionOut])
async def get_questions(session_id: int, db: AsyncSession = Depends(get_db)):
    session = await db.get(InterviewSession, session_id)
    if session is None:
        raise HTTPException(404, "Session not found")

    result = await db.execute(
        select(Question).where(Question.session_id == session_id).order_by(Question.order)
    )
    return result.scalars().all()
