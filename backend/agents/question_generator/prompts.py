# Yeh file Question Generator agent ke teen prompt templates define karti hai.
# Behavioral, Technical, aur Role-Specific — har category ke liye alag prompt hai.
# Difficulty calibration bhi yahan hoti hai: gaps → hard, strengths → medium.

from __future__ import annotations

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

# ---------------------------------------------------------------------------
# Shared difficulty calibration instruction — teeno prompts mein inject hoti hai
# ---------------------------------------------------------------------------

_DIFFICULTY_RULE = """Difficulty assignment rules (strictly follow):
- If the question targets a skill listed in GAPS → difficulty: "hard"
- If the question targets a skill listed in STRENGTHS → difficulty: "medium"
- General situational or behavioural questions → difficulty: "medium"
- Basic warm-up questions → difficulty: "easy"
"""

_OUTPUT_RULE = """Return ONLY a valid JSON array — no markdown fences, no explanation, no text outside the array.
Each element must have exactly these keys: "text", "difficulty", "skill_tag", "follow_up"
- text: the interview question string (min 15 chars)
- difficulty: one of "easy", "medium", "hard"
- skill_tag: the primary skill or topic this question tests (short string)
- follow_up: one short follow-up probing question, or empty string ""
"""

# ---------------------------------------------------------------------------
# Prompt 1 — Behavioral Questions (generate exactly 3)
# ---------------------------------------------------------------------------

BEHAVIORAL_SYSTEM = f"""You are a senior technical interviewer specialising in behavioral interview questions.
Generate exactly 3 behavioral interview questions tailored to the candidate's profile.
Focus on STAR-method scenarios (Situation, Task, Action, Result).
Use the candidate's actual strengths and gaps to make questions specific and relevant.

{_DIFFICULTY_RULE}
{_OUTPUT_RULE}"""

BEHAVIORAL_HUMAN = """Candidate Profile:
- Strengths: {strengths}
- Gaps: {gaps}
- Role applying for: {job_title}
- Experience level inferred from match score {match_score}/100

{rag_context}

{critique_section}

Generate exactly 3 behavioral questions as a JSON array:"""

BEHAVIORAL_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(BEHAVIORAL_SYSTEM),
    HumanMessagePromptTemplate.from_template(BEHAVIORAL_HUMAN),
])

# ---------------------------------------------------------------------------
# Prompt 2 — Technical Questions (generate exactly 4)
# ---------------------------------------------------------------------------

TECHNICAL_SYSTEM = f"""You are a senior software engineer conducting a technical screening interview.
Generate exactly 4 technical interview questions based on the required skills and candidate's gaps.
Questions should be practical and assess real-world problem-solving ability.
Prioritise questions on GAP skills (assign hard difficulty) — these are what the candidate needs to prove.

{_DIFFICULTY_RULE}
{_OUTPUT_RULE}"""

TECHNICAL_HUMAN = """Technical Context:
- Required skills from JD: {required_skills}
- Candidate's existing skills: {candidate_skills}
- Critical gaps (ask hard questions here): {gaps}
- Verified strengths (ask medium questions here): {strengths}
- Role: {job_title}

{rag_context}

{critique_section}

Generate exactly 4 technical questions as a JSON array:"""

TECHNICAL_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(TECHNICAL_SYSTEM),
    HumanMessagePromptTemplate.from_template(TECHNICAL_HUMAN),
])

# ---------------------------------------------------------------------------
# Prompt 3 — Role-Specific Questions (generate exactly 2)
# ---------------------------------------------------------------------------

ROLE_SPECIFIC_SYSTEM = f"""You are a hiring manager for a specific role conducting a role-fit interview.
Generate exactly 2 role-specific questions that assess domain knowledge and situational judgement
for the exact position described. These should be questions only someone who understands
the day-to-day responsibilities of this role could answer well.

{_DIFFICULTY_RULE}
{_OUTPUT_RULE}"""

ROLE_SPECIFIC_HUMAN = """Role Details:
- Job title: {job_title}
- Key responsibilities: {responsibilities}
- Top missing skill the candidate must address: {top_missing_skill}
- Seniority level: {seniority_level}
- Tech stack required: {tech_stack}

{rag_context}

{critique_section}

Generate exactly 2 role-specific questions as a JSON array:"""

ROLE_SPECIFIC_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(ROLE_SPECIFIC_SYSTEM),
    HumanMessagePromptTemplate.from_template(ROLE_SPECIFIC_HUMAN),
])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_critique_section(critique: str | None) -> str:
    """Self-healing loop ka critique next attempt mein inject karo."""
    if not critique:
        return ""
    return f"\nPREVIOUS ATTEMPT FAILED — fix these issues:\n{critique}\n"


def build_rag_context(chunks_text: str) -> str:
    """RAG se mile examples ko prompt mein inject karo."""
    if not chunks_text.strip():
        return ""
    return f"\nSimilar interview question examples for reference:\n{chunks_text}\n"


def format_list(items: list[str]) -> str:
    """List ko comma-separated string mein convert karo."""
    return ", ".join(items) if items else "none specified"
