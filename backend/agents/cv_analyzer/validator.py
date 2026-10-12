# Defines the Pydantic schema for the CV Analyzer agent's output.
# Validates the JSON returned by the LLM against this schema — rejects it if a field is missing.
# validate() is called directly from agent.py — guarantees type safety.

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class CVAnalysisOutput(BaseModel):
    """Validated output schema of the CV Analyzer agent."""

    match_score: int = Field(..., ge=0, le=100, description="CV-JD match percentage 0-100")
    strengths: list[str] = Field(..., min_length=1, description="Skills candidate clearly has")
    gaps: list[str] = Field(default_factory=list, description="Skills candidate is missing")
    required_skills: list[str] = Field(..., min_length=1, description="All skills JD requires")
    candidate_skills: list[str] = Field(..., min_length=1, description="All skills candidate has")
    summary: str = Field(..., min_length=20, description="Overall fit assessment paragraph")
    experience_match: bool = Field(default=False)
    education_match: bool = Field(default=False)
    top_missing_skill: str = Field(default="", description="Most critical missing skill")

    @field_validator("strengths", "gaps", "required_skills", "candidate_skills", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> list[str]:
        """Wrap a string or None in a list."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return [str(item) for item in v]

    @field_validator("summary", mode="before")
    @classmethod
    def _coerce_summary(cls, v: Any) -> str:
        if v is None:
            return "No summary provided."
        return str(v).strip()

    @field_validator("match_score", mode="before")
    @classmethod
    def _coerce_score(cls, v: Any) -> int:
        """Convert a float or string score to int."""
        try:
            score = int(float(str(v)))
            return max(0, min(100, score))
        except (ValueError, TypeError):
            return 0


def validate_cv_analysis(raw: dict[str, Any]) -> tuple[bool, Optional[str], Optional[CVAnalysisOutput]]:
    """
    Validate the raw LLM dict.

    Returns:
        (True, None, CVAnalysisOutput) on success
        (False, error_message, None) on failure
    """
    try:
        result = CVAnalysisOutput.model_validate(raw)
        return True, None, result
    except Exception as exc:
        return False, str(exc), None
