from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    raw_text = Column(Text, nullable=True)
    extracted_skills = Column(JSON, nullable=True)
    status = Column(String, default="uploaded")
    # uploaded -> parsing -> extracting_skills -> generating_questions -> ready -> failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("InterviewSession", back_populates="resume")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    status = Column(String, default="ready")  # ready -> in_progress -> completed
    created_at = Column(DateTime, default=datetime.utcnow)

    resume = relationship("Resume", back_populates="sessions")
    questions = relationship("Question", back_populates="session", order_by="Question.order")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    text = Column(Text, nullable=False)
    skill = Column(String, nullable=True)
    difficulty = Column(String, nullable=True)  # easy / medium / hard
    rubric = Column(JSON, nullable=True)  # {"key_points": [...]}
    order = Column(Integer, default=0)

    session = relationship("InterviewSession", back_populates="questions")
    answer = relationship("Answer", back_populates="question", uselist=False)


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, unique=True)
    audio_path = Column(String, nullable=True)
    transcript = Column(Text, nullable=True)
    status = Column(String, default="recorded")
    # recorded -> transcribing -> transcribed -> evaluating -> evaluated -> failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    question = relationship("Question", back_populates="answer")
    evaluation = relationship("Evaluation", back_populates="answer", uselist=False)


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True)
    answer_id = Column(Integer, ForeignKey("answers.id"), nullable=False, unique=True)
    scores = Column(JSON, nullable=True)  # {"correctness": 7, "completeness": 6, "clarity": 8}
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    answer = relationship("Answer", back_populates="evaluation")