import asyncio

from app.celery_app import celery_app
from app.database import SessionLocal
from app import services, llm
from app.models import Resume, InterviewSession, Question, Answer, Evaluation


@celery_app.task(bind=True, max_retries=2)
def process_resume_task(self, resume_id: int):
    """
    Full pipeline for a freshly uploaded resume:
    parse text -> extract skills (LLM) -> generate questions (LLM)
    -> create a session + questions -> mark resume ready.
    """
    asyncio.run(_process_resume(resume_id))


async def _process_resume(resume_id: int):
    async with SessionLocal() as db:
        resume = await db.get(Resume, resume_id)
        if resume is None:
            return

        try:
            resume.status = "parsing"
            await db.commit()

            raw_text = services.parse_resume_file(resume.file_path)
            resume.raw_text = raw_text

            resume.status = "extracting_skills"
            await db.commit()

            skills_result = llm.extract_skills(raw_text)
            resume.extracted_skills = skills_result.model_dump()

            resume.status = "generating_questions"
            await db.commit()

            questions_result = llm.generate_questions(skills_result.skills, raw_text)

            session = InterviewSession(resume_id=resume.id, status="ready")
            db.add(session)
            await db.flush()  # need session.id before attaching questions

            for order, q in enumerate(questions_result.questions):
                db.add(
                    Question(
                        session_id=session.id,
                        text=q.text,
                        skill=q.skill,
                        difficulty=q.difficulty,
                        rubric={"key_points": q.key_points},
                        order=order,
                    )
                )

            resume.status = "ready"
            await db.commit()

        except Exception as exc:
            resume.status = "failed"
            resume.error_message = str(exc)
            await db.commit()
            raise


@celery_app.task(bind=True, max_retries=2)
def process_answer_task(self, answer_id: int):
    """
    Full pipeline for a freshly submitted answer:
    transcribe audio (Whisper) -> evaluate against the question's rubric (LLM)
    -> save the evaluation -> mark answer evaluated.
    """
    asyncio.run(_process_answer(answer_id))


async def _process_answer(answer_id: int):
    async with SessionLocal() as db:
        answer = await db.get(Answer, answer_id)
        if answer is None:
            return

        try:
            answer.status = "transcribing"
            await db.commit()

            transcript = services.transcribe_audio(answer.audio_path)
            answer.transcript = transcript
            answer.status = "transcribed"
            await db.commit()

            answer.status = "evaluating"
            await db.commit()

            question = await db.get(Question, answer.question_id)
            key_points = (question.rubric or {}).get("key_points", [])

            eval_result = llm.evaluate_answer(question.text, key_points, transcript)

            evaluation = Evaluation(
                answer_id=answer.id,
                scores={
                    "correctness": eval_result.correctness,
                    "completeness": eval_result.completeness,
                    "clarity": eval_result.clarity,
                },
                feedback=eval_result.feedback,
            )
            db.add(evaluation)

            answer.status = "evaluated"
            await db.commit()

        except Exception as exc:
            answer.status = "failed"
            answer.error_message = str(exc)
            await db.commit()
            raise