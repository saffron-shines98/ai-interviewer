from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---- API request/response schemas ----

class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    error_message: Optional[str] = None
    extracted_skills: Optional[dict] = None
    session_id: Optional[int] = None
    question_count: Optional[int] = None


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    skill: Optional[str] = None
    difficulty: Optional[str] = None
    order: int


class AnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    status: str
    error_message: Optional[str] = None
    transcript: Optional[str] = None
    scores: Optional[dict] = None
    feedback: Optional[str] = None


# ---- LLM structured-output schemas ----
# These define exactly what we force the model to return via tool use,
# then validate the response against before trusting/storing it.

class SkillExtractionResult(BaseModel):
    skills: List[str]
    experience_years: Optional[float] = None
    projects: List[str] = Field(default_factory=list)
    summary: Optional[str] = None


class GeneratedQuestion(BaseModel):
    text: str
    skill: str
    difficulty: str  # easy / medium / hard
    key_points: List[str]  # the rubric - what a strong answer should cover


class QuestionGenerationResult(BaseModel):
    questions: List[GeneratedQuestion]


class EvaluationResult(BaseModel):
    correctness: int = Field(ge=1, le=10)
    completeness: int = Field(ge=1, le=10)
    clarity: int = Field(ge=1, le=10)
    feedback: str
