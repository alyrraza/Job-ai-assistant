# Yeh file Voice Interview agent ke teen prompt templates define karti hai.
# Answer evaluate karo (0-10 score), improvement feedback do, follow-up question banao.
# Har prompt sirf ek cheez karta hai — single responsibility, easy to tune.

from __future__ import annotations

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

# ---------------------------------------------------------------------------
# Prompt 1 — Answer Evaluation (score 0-10 + detailed breakdown)
# ---------------------------------------------------------------------------

EVAL_SYSTEM = """You are an experienced technical interviewer evaluating a candidate's answer.
Score the answer honestly and give actionable feedback.
Return ONLY valid JSON — no markdown fences, no explanation outside the JSON object.

Scoring rubric:
0-2  : No answer or completely wrong / irrelevant
3-4  : Partial understanding, major gaps
5-6  : Adequate answer, some depth missing
7-8  : Good answer with clear understanding
9-10 : Excellent, concise, with real-world examples

Required JSON structure:
{{
  "score": 7,
  "feedback": "2-3 sentence honest evaluation of the answer",
  "strong_points": ["what was done well — specific points"],
  "weak_points": ["what was missing or incorrect — specific points"],
  "follow_up": "one natural follow-up probing question, or empty string if answer was complete"
}}"""

EVAL_HUMAN = """Interview Question: {question_text}
Difficulty: {difficulty}
Skill being tested: {skill_tag}
Category: {category}

Candidate's Answer:
{answer_text}

{critique_section}

Evaluate and return JSON:"""

EVAL_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(EVAL_SYSTEM),
    HumanMessagePromptTemplate.from_template(EVAL_HUMAN),
])

# ---------------------------------------------------------------------------
# Prompt 2 — Improvement Feedback (end-of-session tips)
# ---------------------------------------------------------------------------

FEEDBACK_SYSTEM = """You are a career coach summarizing a mock interview session.
Review all the candidate's question scores and generate an actionable improvement report.
Return ONLY valid JSON — no markdown fences, no explanation outside the JSON object.

Required JSON structure:
{{
  "overall_feedback": "3-4 sentence honest overall assessment",
  "weak_areas": ["skill areas needing most improvement — from lowest scored questions"],
  "strong_areas": ["skill areas where candidate performed well"],
  "top_improvement_tips": ["specific, actionable tip 1", "tip 2", "tip 3"],
  "recommendation": "hire|consider|reject"
}}

Recommendation rules:
- avg_score >= 7.0  → "hire"
- avg_score 5.0-6.9 → "consider"
- avg_score < 5.0   → "reject"
"""

FEEDBACK_HUMAN = """Session Summary:
Total questions: {total_questions}
Average score: {avg_score}/10
Score breakdown: {score_breakdown}

Questions and scores:
{qa_summary}

{critique_section}

Generate improvement report as JSON:"""

FEEDBACK_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(FEEDBACK_SYSTEM),
    HumanMessagePromptTemplate.from_template(FEEDBACK_HUMAN),
])

# ---------------------------------------------------------------------------
# Prompt 3 — Follow-up Question Generation
# ---------------------------------------------------------------------------

FOLLOW_UP_SYSTEM = """You are a technical interviewer generating a targeted follow-up question.
The candidate gave an incomplete or surface-level answer. Probe deeper.
Return ONLY valid JSON — no markdown fences, no explanation outside the JSON object.

Required JSON structure:
{{
  "follow_up_question": "specific follow-up question targeting the gap in the answer"
}}"""

FOLLOW_UP_HUMAN = """Original Question: {original_question}
Candidate's Answer: {candidate_answer}
Weak Points Identified: {weak_points}

Generate one targeted follow-up question as JSON:"""

FOLLOW_UP_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(FOLLOW_UP_SYSTEM),
    HumanMessagePromptTemplate.from_template(FOLLOW_UP_HUMAN),
])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_critique_section(critique: str | None) -> str:
    """Self-healing critique inject karo agar previous attempt fail hua ho."""
    if not critique:
        return ""
    return f"\nPREVIOUS ATTEMPT FAILED — fix these issues:\n{critique}\n"


def build_qa_summary(evaluations: list[dict]) -> str:
    """Session ke saare Q&A ko LLM-readable format mein format karo."""
    lines = []
    for i, ev in enumerate(evaluations, 1):
        lines.append(
            f"Q{i} [{ev.get('category', '?')} | {ev.get('difficulty', '?')} | "
            f"skill: {ev.get('skill_tag', '?')}]: "
            f"{ev.get('question_text', '')[:80]}\n"
            f"  Score: {ev.get('score', 0)}/10\n"
            f"  Answer snippet: {str(ev.get('answer_text', ''))[:100]}"
        )
    return "\n\n".join(lines)


def build_score_breakdown(evaluations: list[dict]) -> str:
    """Score distribution string banao — e.g. 'Q1:7 Q2:4 Q3:9'."""
    return " | ".join(
        f"Q{i + 1}:{ev.get('score', 0)}" for i, ev in enumerate(evaluations)
    )
