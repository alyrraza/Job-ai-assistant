# Yeh Agent 2 hai — CV Analysis ka output lo, personalized interview questions banao.
# RAG se similar questions retrieve karo context ke liye, phir Groq LLM se generate karo.
# BaseAgent se inherit — self-healing, MLflow logging, critique injection sab free milta hai.

from __future__ import annotations

import json
import re
from typing import Any, Optional

from langchain_groq import ChatGroq

from backend.agents.base_agent import BaseAgent
from backend.agents.question_generator.prompts import (
    BEHAVIORAL_PROMPT,
    TECHNICAL_PROMPT,
    ROLE_SPECIFIC_PROMPT,
    build_critique_section,
    build_rag_context,
    format_list,
)
from backend.agents.question_generator.validator import (
    _attach_category,
    validate_question_output,
)
from backend.rag.retriever import retrieve_similar_questions, format_chunks_for_prompt
from backend.utils.config import get_settings
from backend.utils.logger import logger

settings = get_settings()

# Target counts per category — change here if spec changes
_BEHAVIORAL_COUNT = 3
_TECHNICAL_COUNT = 4
_ROLE_SPECIFIC_COUNT = 2


class QuestionGeneratorAgent(BaseAgent):
    """
    Agent 2 — Interview Question Generator.

    Expected input_data keys (come directly from CVAnalyzerAgent.data):
        match_score       (int)
        strengths         (list[str])
        gaps              (list[str])
        required_skills   (list[str])
        candidate_skills  (list[str])
        top_missing_skill (str)
        _jd_parsed        (dict)  — job_title, responsibilities, tech_stack, seniority_level
        _cv_parsed        (dict)  — optional context

    Output (AgentResult.data) keys: see QuestionGeneratorOutput schema.
    """

    name: str = "question_generator"

    def __init__(self, session_id: Optional[str] = None) -> None:
        super().__init__(session_id=session_id)
        self._llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0.4,   # Slightly higher — we want varied, creative questions
            max_retries=2,
        )
        logger.info(f"[{self.name}] LLM ready: {settings.groq_model}")

    # ------------------------------------------------------------------
    # execute() — called by BaseAgent self-healing loop
    # ------------------------------------------------------------------

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Pipeline:
          1. Extract context from CV analysis output
          2. RAG retrieve similar question examples
          3. Generate 3 behavioral + 4 technical + 2 role-specific questions
          4. Merge into validated-ready output dict
        """
        # ---- 1. Extract context ----
        strengths: list[str] = input_data.get("strengths", [])
        gaps: list[str] = input_data.get("gaps", [])
        required_skills: list[str] = input_data.get("required_skills", [])
        candidate_skills: list[str] = input_data.get("candidate_skills", [])
        match_score: int = input_data.get("match_score", 50)
        top_missing_skill: str = input_data.get("top_missing_skill", "")
        critique: Optional[str] = input_data.get("_critique")

        jd_parsed: dict = input_data.get("_jd_parsed", {})
        job_title: str = jd_parsed.get("job_title", "Software Engineer")
        responsibilities: list[str] = jd_parsed.get("responsibilities", [])
        tech_stack: list[str] = jd_parsed.get("tech_stack", required_skills[:5])
        seniority_level: str = jd_parsed.get("seniority_level", "mid")

        if not strengths and not gaps and not required_skills:
            raise ValueError(
                "Input data has no strengths/gaps/required_skills — "
                "pass CVAnalyzerAgent output directly to QuestionGeneratorAgent"
            )

        # ---- 2. RAG context ----
        rag_query = f"{job_title} interview questions {' '.join((gaps + strengths)[:5])}"
        rag_chunks = retrieve_similar_questions(rag_query, n_results=5)
        rag_text = format_chunks_for_prompt(rag_chunks, max_chars=1500)
        rag_ctx = build_rag_context(rag_text)
        critique_ctx = build_critique_section(critique)

        # ---- 3a. Behavioral questions ----
        logger.debug(f"[{self.name}] Generating {_BEHAVIORAL_COUNT} behavioral questions")
        raw_behavioral = self._call_llm_json_list(
            BEHAVIORAL_PROMPT,
            {
                "strengths": format_list(strengths),
                "gaps": format_list(gaps),
                "job_title": job_title,
                "match_score": str(match_score),
                "rag_context": rag_ctx,
                "critique_section": critique_ctx,
            },
        )
        behavioral = _attach_category(raw_behavioral[:_BEHAVIORAL_COUNT], "behavioral")

        # ---- 3b. Technical questions ----
        logger.debug(f"[{self.name}] Generating {_TECHNICAL_COUNT} technical questions")
        raw_technical = self._call_llm_json_list(
            TECHNICAL_PROMPT,
            {
                "required_skills": format_list(required_skills),
                "candidate_skills": format_list(candidate_skills),
                "gaps": format_list(gaps),
                "strengths": format_list(strengths),
                "job_title": job_title,
                "rag_context": rag_ctx,
                "critique_section": critique_ctx,
            },
        )
        technical = _attach_category(raw_technical[:_TECHNICAL_COUNT], "technical")

        # ---- 3c. Role-specific questions ----
        logger.debug(f"[{self.name}] Generating {_ROLE_SPECIFIC_COUNT} role-specific questions")
        raw_role = self._call_llm_json_list(
            ROLE_SPECIFIC_PROMPT,
            {
                "job_title": job_title,
                "responsibilities": format_list(responsibilities[:6]),
                "top_missing_skill": top_missing_skill or format_list(gaps[:1]),
                "seniority_level": seniority_level,
                "tech_stack": format_list(tech_stack[:8]),
                "rag_context": rag_ctx,
                "critique_section": critique_ctx,
            },
        )
        role_specific = _attach_category(raw_role[:_ROLE_SPECIFIC_COUNT], "role_specific")

        # ---- 4. Assemble output ----
        return {
            "behavioral": behavioral,
            "technical": technical,
            "role_specific": role_specific,
            # total_count and difficulty_distribution auto-computed by validator
            "total_count": 0,
            "difficulty_distribution": {},
        }

    # ------------------------------------------------------------------
    # validate() — called by BaseAgent after execute()
    # ------------------------------------------------------------------

    def validate(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Pydantic schema se output validate karo."""
        is_valid, error, _ = validate_question_output(output)
        return is_valid, error

    # ------------------------------------------------------------------
    # self_critique() — targeted error hints for retry
    # ------------------------------------------------------------------

    def self_critique(
        self,
        input_data: dict[str, Any],
        failed_output: dict[str, Any],
        error: Optional[str],
    ) -> str:
        behavioral_count = len(failed_output.get("behavioral", []))
        technical_count = len(failed_output.get("technical", []))
        role_count = len(failed_output.get("role_specific", []))
        return (
            f"Validation error: {error}\n"
            f"Current counts — behavioral: {behavioral_count} (need 3), "
            f"technical: {technical_count} (need 4), "
            f"role_specific: {role_count} (need 2).\n"
            f"Each question MUST have: text (str), difficulty (easy/medium/hard), "
            f"skill_tag (str), follow_up (str). "
            f"Return a JSON array per category — not a JSON object."
        )

    # ------------------------------------------------------------------
    # Internal LLM helper
    # ------------------------------------------------------------------

    def _call_llm_json_list(
        self,
        prompt_template: Any,
        variables: dict[str, str],
    ) -> list[dict[str, Any]]:
        """
        Prompt render karo, LLM call karo, JSON array parse karo.
        List nahi mila toh ValueError — self-healing loop handle karega.
        """
        messages = prompt_template.format_messages(**variables)
        response = self._llm.invoke(messages)
        raw_text: str = response.content.strip()

        # Strip markdown fences
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM returned non-JSON. Error: {exc}. "
                f"Raw (300 chars): {raw_text[:300]}"
            ) from exc

        if not isinstance(parsed, list):
            # LLM returned an object — try to unwrap common wrapper keys
            for key in ("questions", "items", "results", "data"):
                if isinstance(parsed, dict) and key in parsed:
                    parsed = parsed[key]
                    break
            if not isinstance(parsed, list):
                raise ValueError(
                    f"Expected a JSON array, got {type(parsed).__name__}. "
                    f"Wrap questions in a top-level array."
                )

        return parsed
