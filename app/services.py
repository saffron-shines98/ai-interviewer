from pathlib import Path

import pdfplumber
import docx

from app.config import settings


def parse_resume_file(file_path: str) -> str:
    """Extract raw text from a PDF or DOCX resume."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts).strip()

    if suffix == ".docx":
        document = docx.Document(path)
        return "\n".join(p.text for p in document.paragraphs).strip()

    raise ValueError(f"Unsupported resume file type: {suffix}")


def transcribe_audio(audio_path: str) -> str:
    """Transcribe a recorded answer using the OpenAI Whisper API."""
    if settings.use_mock_ai:
        return "Mock transcript: I would explain the concept with a concrete project example and discuss tradeoffs."

    from openai import OpenAI

    openai_client = OpenAI(api_key=settings.openai_api_key)
    with open(audio_path, "rb") as audio_file:
        result = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
    return result.text
