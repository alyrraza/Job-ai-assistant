# Yeh CV Analyzer agent hai — pehla aur sabse important agent.
# CV text aur JD text lo, Groq LLM se teen step mein process karo, validated JSON wapas do.
# BaseAgent se inherit kiya — self-healing, MLflow logging sab automatic milta hai.

from __future__ import annotations

import json
import re
from typing import Any, Optional

from langchain_groq import ChatGroq

from backend.agents.base_agent import BaseAgent, AgentResult
from backend.agents.cv_analyzer.prompts import (
    CV_PARSE_PROMPT,
    JD_PARSE_PROMPT,
    COMPARISON_PROMPT,
    build_critique_section,
)
from backend.agents.cv_analyzer.validator import validate_cv_analysis
from backend.utils.config import get_settings
from backend.utils.logger import logger

settings = get_settings()


class CVAnalyzerAgent(BaseAgent):
    """
    Agent 1 — CV + JD Analyzer.

    Input dict expected keys:
        cv_text  (str) — raw CV/resume text
        jd_text  (str) — raw job description text

    Output (AgentResult.data) keys: see CVAnalysisOutput schema.
    """

    name: str = "cv_analyzer"

    def __init__(self, session_id: Optional[str] = None) -> None:
        super().__init__(session_id=session_id)
        self._llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0.1,
            max_retries=2,
        )
        logger.info(f"[{self.name}] LLM ready: {settings.groq_model}")

    # ------------------------------------------------------------------
    # execute() — called by BaseAgent self-healing loop
    # ------------------------------------------------------------------

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Three-step pipeline: parse CV → parse JD → compare.
        Returns raw dict that will be validated next.
        """
        cv_text: str = input_data.get("cv_text", "")
        jd_text: str = input_data.get("jd_text", "")
        critique: Optional[str] = input_data.get("_critique")

        if not cv_text.strip():
            raise ValueError("cv_text is empty — cannot analyze")
        if not jd_text.strip():
            raise ValueError("jd_text is empty — cannot analyze")

        logger.debug(f"[{self.name}] Step 1: Parsing CV ({len(cv_text)} chars)")
        cv_parsed = self._call_llm_json(CV_PARSE_PROMPT, {"cv_text": cv_text})

        logger.debug(f"[{self.name}] Step 2: Parsing JD ({len(jd_text)} chars)")
        jd_parsed = self._call_llm_json(JD_PARSE_PROMPT, {"jd_text": jd_text})

        logger.debug(f"[{self.name}] Step 3: Comparing CV vs JD")
        comparison = self._call_llm_json(
            COMPARISON_PROMPT,
            {
                "cv_parsed": json.dumps(cv_parsed, indent=2),
                "jd_parsed": json.dumps(jd_parsed, indent=2),
                "critique_section": build_critique_section(critique),
            },
        )

        # Attach intermediate parsed data so downstream agents can use them
        comparison["_cv_parsed"] = cv_parsed
        comparison["_jd_parsed"] = jd_parsed
        return comparison

    # ------------------------------------------------------------------
    # validate() — called by BaseAgent after execute()
    # ------------------------------------------------------------------

    def validate(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Pydantic schema se output validate karo."""
        # Strip internal keys before schema validation
        public_output = {k: v for k, v in output.items() if not k.startswith("_")}
        is_valid, error, _ = validate_cv_analysis(public_output)
        return is_valid, error

    # ------------------------------------------------------------------
    # self_critique() — LLM-powered correction hint
    # ------------------------------------------------------------------

    def self_critique(
        self,
        input_data: dict[str, Any],
        failed_output: dict[str, Any],
        error: Optional[str],
    ) -> str:
        """Groq se critiquer prompt chalaao — next attempt ke liye hint banao."""
        present_keys = list(failed_output.keys())
        critique_prompt = (
            f"The CV analysis JSON output was invalid.\n"
            f"Validation error: {error}\n"
            f"Keys present in output: {present_keys}\n"
            f"Fix the output so it strictly follows the required JSON schema with fields: "
            f"match_score (int 0-100), strengths (list), gaps (list), "
            f"required_skills (list), candidate_skills (list), summary (str 20+ chars), "
            f"experience_match (bool), education_match (bool), top_missing_skill (str)."
        )
        logger.debug(f"[{self.name}] Self-critique hint generated")
        return critique_prompt

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _call_llm_json(self, prompt_template, variables: dict[str, str]) -> dict[str, Any]:
        """
        Prompt render karo, LLM call karo, JSON parse karo.
        JSON parse fail ho toh ValueError raise karo — self-healing loop catch karega.
        """
        messages = prompt_template.format_messages(**variables)
        response = self._llm.invoke(messages)
        raw_text: str = response.content.strip()

        # Strip markdown fences if LLM disobeyed instructions
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM returned non-JSON response. "
                f"Parse error: {exc}. "
                f"Raw (first 300 chars): {raw_text[:300]}"
            ) from exc
