# Yeh file Voice Interview agent ke output schemas define karti hai.
# AnswerEval: har sawal ka score + feedback. SessionReport: poora session ka summary.
# avg_score aur recommendation auto-compute hote hain — LLM pe count karne ka bharosa nahi.

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Recommendation(str, Enum):
    hire = "hire"
    consider = "consider"
    reject = "reject"


class AnswerEval(BaseModel):
    """Ek single answer ka evaluation — score, feedback, follow-up."""

    score: int = Field(..., ge=0, le=10, description="Answer quality score 0-10")
    feedback: str = Field(..., min_length=10, description="Honest evaluation of the answer")
    strong_points: list[str] = Field(default_factory=list)
    weak_points: list[str] = Field(default_factory=list)
    follow_up: str = Field(default="", description="Follow-up question or empty string")

    # Runtime fields — set by agent, not LLM
    question_index: int = Field(default=0)
    question_text: str = Field(default="")
    answer_text: str = Field(default="")
    category: str = Field(default="")
    skill_tag: str = Field(default="")
    difficulty: str = Field(default="medium")

    @field_validator("score", mode="before")
    @classmethod
    def _coerce_score(cls, v: Any) -> int:
        try:
            return max(0, min(10, int(float(str(v)))))
        except (ValueError, TypeError):
            return 0

    @field_validator("feedback", mode="before")
    @classmethod
    def _coerce_feedback(cls, v: Any) -> str:
        return str(v).strip() if v else "No evaluation provided."

    @field_validator("strong_points", "weak_points", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return [str(x) for x in v]

    @field_validator("follow_up", mode="before")
    @classmethod
    def _coerce_follow_up(cls, v: Any) -> str:
        return str(v).strip() if v else ""


class SessionReport(BaseModel):
    """Poora voice interview session ka final report."""

    answers: list[AnswerEval] = Field(..., min_length=1)
    overall_feedback: str = Field(..., min_length=20)
    weak_areas: list[str] = Field(default_factory=list)
    strong_areas: list[str] = Field(default_factory=list)
    top_improvement_tips: list[str] = Field(default_factory=list)
    recommendation: Recommendation = Field(default=Recommendation.consider)

    # Auto-computed — never trust LLM values for these
    avg_score: float = Field(default=0.0)
    total_questions: int = Field(default=0)
    passed: bool = Field(default=False)

    @field_validator("overall_feedback", mode="before")
    @classmethod
    def _coerce_feedback(cls, v: Any) -> str:
        return str(v).strip() if v else "Session completed. No summary generated."

    @field_validator("recommendation", mode="before")
    @classmethod
    def _normalise_rec(cls, v: Any) -> str:
        val = str(v).strip().lower()
        if val not in ("hire", "consider", "reject"):
            return "consider"
        return val

    @field_validator("weak_areas", "strong_areas", "top_improvement_tips", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return [str(x) for x in v]

    @model_validator(mode="after")
    def _compute_derived(self) -> "SessionReport":
        """avg_score, total_questions, passed — khud calculate karo."""
        scores = [a.score for a in self.answers]
        self.total_questions = len(scores)
        self.avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        self.passed = self.avg_score >= 5.0
        return self


# ---------------------------------------------------------------------------
# Public validation helpers
# ---------------------------------------------------------------------------

def validate_answer_eval(
    raw: dict[str, Any],
) -> tuple[bool, Optional[str], Optional[AnswerEval]]:
    """
    LLM ke answer evaluation JSON ko validate karo.

    Returns:
        (True, None, AnswerEval) on success
        (False, error_message, None) on failure
    """
    try:
        result = AnswerEval.model_validate(raw)
        return True, None, result
    except Exception as exc:
        return False, str(exc), None


def validate_session_report(
    raw: dict[str, Any],
) -> tuple[bool, Optional[str], Optional[SessionReport]]:
    """
    Full session report dict ko validate karo.

    Returns:
        (True, None, SessionReport) on success
        (False, error_message, None) on failure
    """
    try:
        result = SessionReport.model_validate(raw)
        return True, None, result
    except Exception as exc:
        return False, str(exc), None
