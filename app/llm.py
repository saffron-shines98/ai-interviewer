import re

from app.config import settings
from app.schemas import EvaluationResult, GeneratedQuestion, QuestionGenerationResult, SkillExtractionResult

MODEL = "claude-sonnet-4-6"


def extract_skills(resume_text: str) -> SkillExtractionResult:
    """Extract structured resume facts. Defaults to a deterministic local mock."""
    if settings.use_mock_ai:
        return _mock_extract_skills(resume_text)

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    tool = {
        "name": "record_skills",
        "description": "Record the skills, experience, and projects extracted from a resume.",
        "input_schema": {
            "type": "object",
            "properties": {
                "skills": {"type": "array", "items": {"type": "string"}},
                "experience_years": {"type": "number"},
                "projects": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string"},
            },
            "required": ["skills"],
        },
    }

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[tool],
        tool_choice={"type": "tool", "name": "record_skills"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract the technical skills, total years of experience, and "
                    "notable projects from this resume text. Only include skills "
                    "actually mentioned in the text.\n\n"
                    f"Resume:\n{resume_text}"
                ),
            }
        ],
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    return SkillExtractionResult(**tool_use.input)


def generate_questions(skills: list[str], resume_text: str, num_questions: int = 6) -> QuestionGenerationResult:
    """Generate interview questions and rubrics. Defaults to a deterministic local mock."""
    if settings.use_mock_ai:
        return _mock_generate_questions(skills, resume_text, num_questions)

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    tool = {
        "name": "record_questions",
        "description": "Record the generated interview questions with their rubric.",
        "input_schema": {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "skill": {"type": "string"},
                            "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                            "key_points": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["text", "skill", "difficulty", "key_points"],
                    },
                }
            },
            "required": ["questions"],
        },
    }

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        tools=[tool],
        tool_choice={"type": "tool", "name": "record_questions"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Generate {num_questions} interview questions for a candidate "
                    f"with these skills: {', '.join(skills)}.\n\n"
                    "Mix technical/conceptual, scenario-based, and project-specific "
                    "questions. Include key_points for scoring.\n\n"
                    f"Resume:\n{resume_text}"
                ),
            }
        ],
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    return QuestionGenerationResult(**tool_use.input)


def evaluate_answer(question_text: str, key_points: list[str], transcript: str) -> EvaluationResult:
    """Score a transcribed answer. Defaults to a deterministic local mock."""
    if settings.use_mock_ai:
        return EvaluationResult(
            correctness=7,
            completeness=6,
            clarity=8,
            feedback=(
                "Mock evaluation: the answer is understandable and covers part of the rubric. "
                "Add more concrete examples and mention the missing key points."
            ),
        )

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    tool = {
        "name": "record_evaluation",
        "description": "Record the evaluation scores and feedback for a candidate's answer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "correctness": {"type": "integer", "minimum": 1, "maximum": 10},
                "completeness": {"type": "integer", "minimum": 1, "maximum": 10},
                "clarity": {"type": "integer", "minimum": 1, "maximum": 10},
                "feedback": {"type": "string"},
            },
            "required": ["correctness", "completeness", "clarity", "feedback"],
        },
    }

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[tool],
        tool_choice={"type": "tool", "name": "record_evaluation"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Question: {question_text}\n\n"
                    f"Key points: {', '.join(key_points)}\n\n"
                    f"Candidate answer:\n{transcript}\n\n"
                    "Score correctness, completeness, and clarity from 1-10."
                ),
            }
        ],
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    return EvaluationResult(**tool_use.input)


def _mock_extract_skills(resume_text: str) -> SkillExtractionResult:
    text = resume_text.lower()
    known_skills = [
        "Python",
        "FastAPI",
        "PostgreSQL",
        "Redis",
        "Celery",
        "SQLAlchemy",
        "Docker",
        "React",
        "JavaScript",
        "TypeScript",
        "Machine Learning",
        "AWS",
    ]
    skills = [skill for skill in known_skills if skill.lower() in text]
    if not skills:
        skills = ["Python", "FastAPI", "SQL"]

    projects = _extract_project_lines(resume_text)
    years_match = re.search(r"(\d+(?:\.\d+)?)\+?\s+years?", text)
    experience_years = float(years_match.group(1)) if years_match else None

    return SkillExtractionResult(
        skills=skills,
        experience_years=experience_years,
        projects=projects,
        summary="Mock extraction generated from the uploaded resume text.",
    )


def _mock_generate_questions(skills: list[str], resume_text: str, num_questions: int) -> QuestionGenerationResult:
    selected_skills = skills or ["Python", "FastAPI", "SQL"]
    questions = []

    for index in range(num_questions):
        skill = selected_skills[index % len(selected_skills)]
        difficulty = ["easy", "medium", "hard"][index % 3]
        questions.append(
            GeneratedQuestion(
                text=(
                    f"Explain how you have used {skill} in a real project. "
                    "What design decisions did you make and what tradeoffs did you consider?"
                ),
                skill=skill,
                difficulty=difficulty,
                key_points=[
                    f"Shows practical understanding of {skill}",
                    "Mentions a concrete project or implementation detail",
                    "Explains tradeoffs, failures, or lessons learned",
                ],
            )
        )

    return QuestionGenerationResult(questions=questions)


def _extract_project_lines(resume_text: str) -> list[str]:
    projects = []
    for line in resume_text.splitlines():
        clean_line = line.strip(" -\t")
        if not clean_line:
            continue
        if "project" in clean_line.lower() or "built" in clean_line.lower():
            projects.append(clean_line[:160])
    return projects[:5]
