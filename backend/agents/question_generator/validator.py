# Yeh file Question Generator agent ke output ka Pydantic schema define karti hai.
# QuestionItem har sawal ko validate karta hai — text, difficulty, category sab check hote hain.
# total_count aur difficulty_distribution auto-compute hote hain — LLM pe bharosa nahi karte.

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class DifficultyLevel(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuestionItem(BaseModel):
    """Ek single interview question — validated aur categorized."""

    text: str = Field(..., min_length=10, description="Interview question text")
    difficulty: DifficultyLevel = Field(..., description="easy / medium / hard")
    category: str = Field(..., description="behavioral / technical / role_specific")
    skill_tag: str = Field(default="", description="Primary skill this question tests")
    follow_up: str = Field(default="", description="Optional follow-up probing question")

    @field_validator("text", mode="before")
    @classmethod
    def _clean_text(cls, v: Any) -> str:
        if not v:
            raise ValueError("Question text cannot be empty")
        return str(v).strip()

    @field_validator("difficulty", mode="before")
    @classmethod
    def _normalise_difficulty(cls, v: Any) -> str:
        """Case-insensitive aur whitespace-tolerant."""
        return str(v).strip().lower() if v else "medium"

    @field_validator("category", mode="before")
    @classmethod
    def _normalise_category(cls, v: Any) -> str:
        return str(v).strip().lower() if v else "behavioral"

    @field_validator("skill_tag", "follow_up", mode="before")
    @classmethod
    def _coerce_optional_str(cls, v: Any) -> str:
        return str(v).strip() if v else ""


class QuestionGeneratorOutput(BaseModel):
    """Question Generator agent ka pura validated output."""

    behavioral: list[QuestionItem] = Field(
        ..., min_length=3, description="Behavioral questions — min 3"
    )
    technical: list[QuestionItem] = Field(
        ..., min_length=4, description="Technical questions — min 4"
    )
    role_specific: list[QuestionItem] = Field(
        ..., min_length=2, description="Role-specific questions — min 2"
    )
    # These two are auto-computed — LLM values ignored and overwritten
    total_count: int = Field(default=0)
    difficulty_distribution: dict[str, int] = Field(default_factory=dict)

    @field_validator("behavioral", "technical", "role_specific", mode="before")
    @classmethod
    def _coerce_question_list(cls, v: Any) -> list:
        """None ya non-list aaye toh empty list do — Pydantic will fail min_length check."""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return []

    @model_validator(mode="after")
    def _compute_derived_fields(self) -> "QuestionGeneratorOutput":
        """total_count aur difficulty_distribution LLM pe chhod ke khud compute karo."""
        all_q = self.behavioral + self.technical + self.role_specific
        self.total_count = len(all_q)
        dist: dict[str, int] = {"easy": 0, "medium": 0, "hard": 0}
        for q in all_q:
            dist[q.difficulty.value] += 1
        self.difficulty_distribution = dist
        return self


# ---------------------------------------------------------------------------
# Helper used by agent.py
# ---------------------------------------------------------------------------

def _attach_category(
    raw_list: list[dict[str, Any]],
    category: str,
) -> list[dict[str, Any]]:
    """LLM returned list mein category field inject karo."""
    out = []
    for item in raw_list:
        if isinstance(item, dict):
            out.append({**item, "category": category})
    return out


def validate_question_output(
    raw: dict[str, Any],
) -> tuple[bool, Optional[str], Optional[QuestionGeneratorOutput]]:
    """
    Raw dict ko validate karo.

    Returns:
        (True, None, QuestionGeneratorOutput)  — on success
        (False, error_message, None)           — on failure
    """
    try:
        result = QuestionGeneratorOutput.model_validate(raw)
        return True, None, result
    except Exception as exc:
        return False, str(exc), None
