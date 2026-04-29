# Yeh file CV Analyzer agent ke teeno LLM prompts define karti hai.
# CV parse karo, JD parse karo, phir dono compare karo — teen alag prompts hain.
# Prompts ko yahan centralize kiya taake agent.py clean rahe aur prompts easily tune ho sakein.

from __future__ import annotations

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

# ---------------------------------------------------------------------------
# Prompt 1 — CV Parser
# ---------------------------------------------------------------------------

CV_PARSE_SYSTEM = """You are an expert CV parser. Extract structured information from the given CV/resume text.
Return ONLY valid JSON — no markdown fences, no explanation, no extra text before or after the JSON object.

Required JSON structure:
{{
  "name": "candidate full name or empty string",
  "contact": {{"email": "", "phone": "", "linkedin": ""}},
  "summary": "professional summary in 2-3 sentences",
  "total_experience_years": 0,
  "skills": ["skill1", "skill2"],
  "education": [{{"degree": "", "institution": "", "year": 0}}],
  "work_experience": [{{"title": "", "company": "", "duration": "", "responsibilities": []}}],
  "certifications": [],
  "languages": []
}}"""

CV_PARSE_HUMAN = """Parse this CV text and return structured JSON:

{cv_text}"""

CV_PARSE_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(CV_PARSE_SYSTEM),
    HumanMessagePromptTemplate.from_template(CV_PARSE_HUMAN),
])

# ---------------------------------------------------------------------------
# Prompt 2 — JD Parser
# ---------------------------------------------------------------------------

JD_PARSE_SYSTEM = """You are an expert job description analyzer. Extract structured requirements from the job description.
Return ONLY valid JSON — no markdown fences, no explanation, no extra text before or after the JSON object.

Required JSON structure:
{{
  "job_title": "",
  "company": "",
  "required_skills": ["skill1", "skill2"],
  "preferred_skills": [],
  "required_experience_years": 0,
  "education_requirement": "",
  "responsibilities": [],
  "tech_stack": [],
  "soft_skills": [],
  "seniority_level": "junior|mid|senior|lead"
}}"""

JD_PARSE_HUMAN = """Parse this job description and return structured JSON:

{jd_text}"""

JD_PARSE_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(JD_PARSE_SYSTEM),
    HumanMessagePromptTemplate.from_template(JD_PARSE_HUMAN),
])

# ---------------------------------------------------------------------------
# Prompt 3 — CV vs JD Comparison
# ---------------------------------------------------------------------------

COMPARISON_SYSTEM = """You are an expert career coach and technical recruiter.
Compare the candidate's parsed CV data against the parsed job description data.
Return ONLY valid JSON — no markdown fences, no explanation, no extra text before or after the JSON object.

Scoring rules:
- match_score: integer 0-100. 70+ strong match, 40-69 partial, below 40 weak.
- strengths: skills/experience the candidate clearly has that match JD requirements.
- gaps: required skills/experience the candidate is missing or lacks.
- required_skills: all distinct skills the JD requires.
- candidate_skills: all distinct skills the candidate has.
- summary: 3-4 honest sentences assessing overall fit.

Required JSON structure:
{{
  "match_score": 75,
  "strengths": ["strength1", "strength2"],
  "gaps": ["gap1", "gap2"],
  "required_skills": ["skill1", "skill2"],
  "candidate_skills": ["skillA", "skillB"],
  "summary": "overall assessment paragraph",
  "experience_match": true,
  "education_match": true,
  "top_missing_skill": "most critical missing skill or empty string"
}}"""

COMPARISON_HUMAN = """Parsed CV data:
{cv_parsed}

Parsed JD data:
{jd_parsed}
{critique_section}
Compare and return structured JSON:"""

COMPARISON_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(COMPARISON_SYSTEM),
    HumanMessagePromptTemplate.from_template(COMPARISON_HUMAN),
])


def build_critique_section(critique: str | None) -> str:
    """Previous attempt ka critique inject karo agar available ho."""
    if not critique:
        return ""
    return f"\nPREVIOUS ATTEMPT FAILED — please fix these issues:\n{critique}\n"
