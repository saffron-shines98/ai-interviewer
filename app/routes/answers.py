import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.models import Question, Answer, Evaluation
from app.schemas import AnswerOut
from app.tasks import _process_answer, process_answer_task

router = APIRouter()

UPLOAD_DIR = Path("media/answers")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".webm", ".ogg"}


@router.post("/{question_id}", response_model=AnswerOut)
async def submit_answer(
    question_id: int, audio: UploadFile, db: AsyncSession = Depends(get_db)
):
    question = await db.get(Question, question_id)
    if question is None:
        raise HTTPException(404, "Question not found")

    existing = await db.execute(select(Answer).where(Answer.question_id == question_id))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(400, "This question already has a submitted answer")

    suffix = Path(audio.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported audio type {suffix}")

    saved_name = f"{uuid.uuid4().hex}{suffix}"
    saved_path = UPLOAD_DIR / saved_name

    with saved_path.open("wb") as out_file:
        shutil.copyfileobj(audio.file, out_file)

    answer = Answer(question_id=question_id, audio_path=str(saved_path), status="recorded")
    db.add(answer)
    await db.commit()
    await db.refresh(answer)

    if settings.process_tasks_inline:
        await _process_answer(answer.id)
        await db.refresh(answer)
    else:
        process_answer_task.delay(answer.id)

    evaluation = None
    if settings.process_tasks_inline:
        result = await db.execute(select(Evaluation).where(Evaluation.answer_id == answer.id))
        evaluation = result.scalar_one_or_none()

    return AnswerOut(
        id=answer.id,
        question_id=answer.question_id,
        status=answer.status,
        transcript=answer.transcript,
        scores=evaluation.scores if evaluation else None,
        feedback=evaluation.feedback if evaluation else None,
    )


@router.get("/{answer_id}", response_model=AnswerOut)
async def get_answer_status(answer_id: int, db: AsyncSession = Depends(get_db)):
    answer = await db.get(Answer, answer_id)
    if answer is None:
        raise HTTPException(404, "Answer not found")

    result = await db.execute(select(Evaluation).where(Evaluation.answer_id == answer_id))
    evaluation = result.scalar_one_or_none()

    return AnswerOut(
        id=answer.id,
        question_id=answer.question_id,
        status=answer.status,
        error_message=answer.error_message,
        transcript=answer.transcript,
        scores=evaluation.scores if evaluation else None,
        feedback=evaluation.feedback if evaluation else None,
    )   
