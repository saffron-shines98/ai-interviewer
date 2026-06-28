# AI Interviewer

AI-powered mock interview backend. Upload a resume → get tailored interview questions → answer out loud → get transcribed and scored against a rubric.

Stack: FastAPI, PostgreSQL, Celery + Redis, Claude (Anthropic API), Whisper.

## Architecture

```
Candidate (browser)
       |
       v
   FastAPI  ----------------------->  PostgreSQL
       |
       v
   Redis queue
       |
       v
  Celery workers  ------>  Claude (skills, questions, scoring)
       |
       v
  Whisper (transcription)
```

Anything slow (parsing, AI calls, transcription) runs in Celery — the API never blocks on them.

## Project Structure

```
app/
├── main.py          # app instance, routes, table creation on startup
├── config.py        # env vars
├── database.py      # SQLAlchemy engine/session
├── models.py         # Resume, InterviewSession, Question, Answer, Evaluation
├── schemas.py        # API + LLM structured-output schemas
├── routes/
│   ├── resumes.py    # POST /resumes/, GET /resumes/{id}
│   ├── sessions.py   # GET /sessions/{id}/questions
│   ├── answers.py    # POST /answers/{question_id}, GET /answers/{id}
│   └── ws.py          # live session status
├── services.py       # resume parsing, audio transcription
├── tasks.py           # Celery tasks
├── celery_app.py
└── llm.py            # Claude calls: extract_skills, generate_questions, evaluate_answer
```

## Environment Variables

| Variable | Purpose |
|---|---|
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME` | PostgreSQL connection |
| `REDIS_URL` | Celery broker, e.g. `redis://localhost:6379/0` |
| `ANTHROPIC_API_KEY` | Required when `USE_MOCK_AI=False` |
| `OPENAI_API_KEY` | Whisper, for real transcription |
| `USE_MOCK_AI` | `True` = skip Claude, use local mock logic (no key/cost needed) |
| `PROCESS_TASKS_INLINE` | `True` = run tasks synchronously in-request, skip Celery/Redis |

Copy `.env.example` → `.env`, fill in real values. Never commit `.env`.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Tables auto-create on startup — no migration step yet.

## Running

**Terminal 1**
```powershell
redis-server
```

**Terminal 2**
```powershell
.\venv\Scripts\activate
celery -A app.celery_app.celery_app worker --loglevel=info --pool=solo
```

**Terminal 3**
```powershell
.\venv\Scripts\activate
$env:PROCESS_TASKS_INLINE="False"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs`.

Port 8000 busy? `Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess` → `Stop-Process -Id <id> -Force`, or just use `--port 8001`.

## Testing the Flow

1. `POST /resumes/` with a PDF/DOCX → note `id`
2. Poll `GET /resumes/{id}` until `status: "ready"` → gives `session_id`, `question_count`
3. `GET /sessions/{session_id}/questions` → pick a `question_id`
4. `POST /answers/{question_id}` with an audio file (`.mp3`/`.wav`/`.m4a`/`.webm`/`.ogg`)
5. Poll `GET /answers/{answer_id}` until `status: "evaluated"` → `transcript`, `scores`, `feedback`

Optional: `ws://127.0.0.1:8000/ws/{session_id}` for live status instead of polling.

Anything failed? Check `error_message` on the row first.

## Status

**Working:** full resume pipeline, full answer pipeline, status tracking + error capture at every stage, live WebSocket status, mock-AI and inline-task modes for dependency-free testing.

**Not built:** frontend, auth, real migrations (schema auto-creates), retry-on-failure (a retried task restarts from scratch, doesn't resume).

**Known gaps:** no idempotency (retries can duplicate sessions/questions), WebSocket polls the DB rather than true push, one answer per question (no re-record).
