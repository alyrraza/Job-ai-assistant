# Yeh Agent 3 hai — real-time voice interview conduct karta hai.
# Question bolta hai (TTS) → user ka jawab sunta hai (STT) → LLM se evaluate karta hai.
# BaseAgent se inherit — self-healing, MLflow logging, retry sab automatic.

from __future__ import annotations

import json
import re
from typing import Any, Optional

from langchain_groq import ChatGroq

from backend.agents.base_agent import BaseAgent
from backend.agents.voice_interview.prompts import (
    EVAL_PROMPT,
    FEEDBACK_PROMPT,
    build_critique_section,
    build_qa_summary,
    build_score_breakdown,
)
from backend.agents.voice_interview.validator import (
    AnswerEval,
    validate_answer_eval,
    validate_session_report,
)
from backend.utils.config import get_settings
from backend.utils.logger import logger

settings = get_settings()

# Score threshold below which a follow-up question is triggered
_FOLLOW_UP_SCORE_THRESHOLD = 5


class VoiceInterviewAgent(BaseAgent):
    """
    Agent 3 — Voice Interview Conductor.

    Expected input_data keys (from QuestionGeneratorAgent.data):
        behavioral    (list[dict])  — behavioral questions
        technical     (list[dict])  — technical questions
        role_specific (list[dict])  — role-specific questions

    Output (AgentResult.data): SessionReport as dict
    """

    name: str = "voice_interview"

    def __init__(self, session_id: Optional[str] = None) -> None:
        super().__init__(session_id=session_id)

        # Two LLM temperatures: low for scoring (consistent), higher for feedback
        self._eval_llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0.1,
            max_retries=2,
        )
        self._feedback_llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0.4,
            max_retries=2,
        )

        # Voice modules — lazy imports so missing packages don't break other agents
        self._tts = None
        self._stt = None
        self._livekit: Any = None

        logger.info(f"[{self.name}] Initialized | session={self.session_id}")

    # ------------------------------------------------------------------
    # execute() — called by BaseAgent self-healing loop
    # ------------------------------------------------------------------

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Full interview session loop:
          1. Flatten questions (behavioral + technical + role_specific)
          2. Init voice modules (TTS, STT, LiveKit)
          3. Per-question: speak → listen → transcribe → evaluate
          4. If score low → ask follow-up
          5. Build and return SessionReport dict
        """
        # ---- 1. Flatten questions ----
        all_questions = (
            input_data.get("behavioral", [])
            + input_data.get("technical", [])
            + input_data.get("role_specific", [])
        )
        if not all_questions:
            raise ValueError(
                "No questions found in input_data. "
                "Pass QuestionGeneratorAgent.data as input."
            )

        total = len(all_questions)
        logger.info(f"[{self.name}] Starting interview: {total} questions | session={self.session_id}")

        # ---- 2. Init voice modules ----
        self._init_voice_modules()

        # ---- 3. Q&A loop ----
        raw_evaluations: list[dict[str, Any]] = []
        critique: Optional[str] = input_data.get("_critique")

        for idx, question in enumerate(all_questions):
            q_text: str = question.get("text", "")
            q_difficulty: str = question.get("difficulty", "medium")
            q_skill: str = question.get("skill_tag", "")
            q_category: str = question.get("category", "general")

            if not q_text.strip():
                logger.warning(f"[{self.name}] Skipping empty question at index {idx}")
                continue

            logger.info(
                f"[{self.name}] Q{idx + 1}/{total}: [{q_category}/{q_difficulty}] "
                f"skill={q_skill} | {q_text[:60]}..."
            )

            # ---- 3a. TTS: speak the question ----
            tts_path = self._speak_question(q_text, idx + 1, total)

            # ---- 3b. LiveKit: broadcast to user ----
            self._livekit.publish_audio(tts_path)

            # ---- 3c. LiveKit: record user's answer ----
            answer_audio = self._livekit.receive_audio(
                timeout_sec=settings.agent_timeout_seconds
            )

            # ---- 3d. STT: transcribe ----
            answer_text = self._transcribe_answer(answer_audio)
            logger.debug(f"[{self.name}] Answer transcribed: '{answer_text[:80]}'")

            # ---- 3e. LLM: evaluate answer ----
            eval_dict = self._evaluate_answer(
                question_text=q_text,
                difficulty=q_difficulty,
                skill_tag=q_skill,
                category=q_category,
                answer_text=answer_text,
                critique=critique,
            )

            # Attach context fields (not from LLM — set by agent)
            eval_dict.update({
                "question_index": idx,
                "question_text": q_text,
                "answer_text": answer_text,
                "category": q_category,
                "skill_tag": q_skill,
                "difficulty": q_difficulty,
            })
            raw_evaluations.append(eval_dict)

            # ---- 3f. Follow-up if score is low ----
            score = eval_dict.get("score", 10)
            follow_up_q = eval_dict.get("follow_up", "")
            if score <= _FOLLOW_UP_SCORE_THRESHOLD and follow_up_q.strip():
                logger.info(f"[{self.name}] Score={score} ≤ {_FOLLOW_UP_SCORE_THRESHOLD} — asking follow-up")
                follow_up_audio = self._speak_follow_up(follow_up_q)
                self._livekit.publish_audio(follow_up_audio)
                # Record follow-up answer and append to original eval's answer text
                fu_audio = self._livekit.receive_audio(timeout_sec=settings.agent_timeout_seconds)
                fu_answer = self._transcribe_answer(fu_audio)
                if fu_answer.strip():
                    raw_evaluations[-1]["answer_text"] += f" [Follow-up]: {fu_answer}"

        # ---- 4. Session feedback via LLM ----
        feedback_dict = self._generate_session_feedback(raw_evaluations)

        # ---- 5. Assemble output ----
        report = {
            "answers": raw_evaluations,
            "overall_feedback": feedback_dict.get("overall_feedback", ""),
            "weak_areas": feedback_dict.get("weak_areas", []),
            "strong_areas": feedback_dict.get("strong_areas", []),
            "top_improvement_tips": feedback_dict.get("top_improvement_tips", []),
            "recommendation": feedback_dict.get("recommendation", "consider"),
        }
        return report

    # ------------------------------------------------------------------
    # validate() — called by BaseAgent after execute()
    # ------------------------------------------------------------------

    def validate(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """SessionReport schema se output validate karo."""
        is_valid, error, _ = validate_session_report(output)
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
        answer_count = len(failed_output.get("answers", []))
        return (
            f"Session report validation failed: {error}\n"
            f"answers list has {answer_count} items.\n"
            "Required fields: answers (list, min 1), overall_feedback (str 20+ chars), "
            "weak_areas (list), strong_areas (list), recommendation (hire/consider/reject).\n"
            "Each answer needs: score (0-10), feedback (str), strong_points (list), "
            "weak_points (list), follow_up (str)."
        )

    # ------------------------------------------------------------------
    # Voice module helpers
    # ------------------------------------------------------------------

    def _init_voice_modules(self) -> None:
        """TTS, STT, LiveKit lazy init karo — ek baar, baar baar nahi."""
        if self._tts is None:
            from backend.voice.tts import speak, speak_question_intro, speak_follow_up
            self._tts = speak
            self._tts_intro = speak_question_intro
            self._tts_follow = speak_follow_up

        if self._stt is None:
            from backend.voice.stt import transcribe, is_silent
            self._stt = transcribe
            self._stt_silent = is_silent

        if self._livekit is None:
            from backend.voice.livekit_manager import LiveKitManager
            self._livekit = LiveKitManager(session_id=self.session_id)

    def _speak_question(self, question_text: str, number: int, total: int) -> str:
        """Question TTS audio banao aur path return karo."""
        return self._tts_intro(question_text, number, total)

    def _speak_follow_up(self, follow_up_text: str) -> str:
        """Follow-up question TTS audio banao."""
        return self._tts_follow(follow_up_text)

    def _transcribe_answer(self, audio_path: str) -> str:
        """Audio file ko text mein convert karo. Silent hai toh empty string."""
        if self._stt_silent(audio_path):
            logger.debug(f"[{self.name}] Silent audio detected — returning empty answer")
            return ""
        return self._stt(audio_path)

    # ------------------------------------------------------------------
    # LLM evaluation helpers
    # ------------------------------------------------------------------

    def _evaluate_answer(
        self,
        question_text: str,
        difficulty: str,
        skill_tag: str,
        category: str,
        answer_text: str,
        critique: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Ek question-answer pair evaluate karo.
        Empty answer → immediate 0 without LLM call.
        """
        if not answer_text.strip():
            logger.debug(f"[{self.name}] Empty answer — assigning score 0")
            return {
                "score": 0,
                "feedback": "No answer was provided for this question.",
                "strong_points": [],
                "weak_points": ["No answer given"],
                "follow_up": "",
            }

        raw = self._call_llm_json(
            self._eval_llm,
            EVAL_PROMPT,
            {
                "question_text": question_text,
                "difficulty": difficulty,
                "skill_tag": skill_tag or "general",
                "category": category,
                "answer_text": answer_text[:800],  # stay within token budget
                "critique_section": build_critique_section(critique),
            },
        )

        # Validate the eval dict loosely — agent already has self-healing for full output
        is_valid, err, _ = validate_answer_eval(raw)
        if not is_valid:
            logger.warning(f"[{self.name}] Answer eval schema mismatch: {err} — using defaults")
            raw.setdefault("score", 5)
            raw.setdefault("feedback", "Evaluation incomplete.")
            raw.setdefault("strong_points", [])
            raw.setdefault("weak_points", [])
            raw.setdefault("follow_up", "")

        return raw

    def _generate_session_feedback(
        self, evaluations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Poore session ka summary feedback banao.
        Empty session → safe defaults return karo.
        """
        if not evaluations:
            return {
                "overall_feedback": "No answers were recorded in this session.",
                "weak_areas": [],
                "strong_areas": [],
                "top_improvement_tips": [],
                "recommendation": "consider",
            }

        scores = [e.get("score", 0) for e in evaluations]
        avg = round(sum(scores) / len(scores), 2)

        raw = self._call_llm_json(
            self._feedback_llm,
            FEEDBACK_PROMPT,
            {
                "total_questions": str(len(evaluations)),
                "avg_score": str(avg),
                "score_breakdown": build_score_breakdown(evaluations),
                "qa_summary": build_qa_summary(evaluations),
                "critique_section": "",
            },
        )

        # Guarantee required keys
        raw.setdefault("overall_feedback", f"Session average: {avg}/10.")
        raw.setdefault("weak_areas", [])
        raw.setdefault("strong_areas", [])
        raw.setdefault("top_improvement_tips", [])
        raw.setdefault("recommendation", "hire" if avg >= 7 else "consider" if avg >= 5 else "reject")
        return raw

    # ------------------------------------------------------------------
    # LLM JSON call helper (shared with eval + feedback LLMs)
    # ------------------------------------------------------------------

    def _call_llm_json(
        self,
        llm: ChatGroq,
        prompt_template: Any,
        variables: dict[str, str],
    ) -> dict[str, Any]:
        """
        Prompt render karo, LLM call karo, JSON parse karo.
        JSON parse fail ho → ValueError raise → self-healing loop handle karega.
        """
        messages = prompt_template.format_messages(**variables)
        response = llm.invoke(messages)
        raw_text: str = response.content.strip()

        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM returned non-JSON. Error: {exc}. "
                f"Raw (300 chars): {raw_text[:300]}"
            ) from exc
