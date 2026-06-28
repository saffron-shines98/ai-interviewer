import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import SessionLocal
from app.models import InterviewSession, Question, Answer

router = APIRouter()

POLL_INTERVAL_SECONDS = 1.5


@router.websocket("/ws/{session_id}")
async def session_status_socket(websocket: WebSocket, session_id: int):
    """
    Pushes question/answer status for a session whenever it changes.
    This polls the DB internally rather than subscribing to real events -
    simple and fine at low volume. If this ever needs to scale to many
    concurrent sessions, swap to Celery publishing on Redis pub/sub and
    have this subscribe instead of polling.
    """
    await websocket.accept()
    last_snapshot = None

    try:
        while True:
            async with SessionLocal() as db:
                session = await db.get(InterviewSession, session_id)
                if session is None:
                    await websocket.send_json({"error": "session not found"})
                    break

                result = await db.execute(
                    select(Question, Answer)
                    .outerjoin(Answer, Answer.question_id == Question.id)
                    .where(Question.session_id == session_id)
                    .order_by(Question.order)
                )
                rows = result.all()

            snapshot = [
                {
                    "question_id": q.id,
                    "order": q.order,
                    "answer_status": a.status if a else "not_submitted",
                }
                for q, a in rows
            ]

            if snapshot != last_snapshot:
                await websocket.send_json({"questions": snapshot})
                last_snapshot = snapshot

            if snapshot and all(item["answer_status"] == "evaluated" for item in snapshot):
                await websocket.send_json({"event": "session_complete"})
                break

            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    except WebSocketDisconnect:
        pass