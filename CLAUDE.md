# CV Interview Coach — Claude Code Master Context

## Ek Line Summary
Ek multi-agent AI system: CV + JD lo → score do → gaps batao → voice-based mock interview lo. Supervisor LLM decide karta hai kaunsa agent kab chale. Self-healing har agent mein built-in hai.

---

## GitHub Repo
https://github.com/alyrraza/Job-ai-assistant.git

---

## Environment
- Python: 3.11.4
- Node: v22.17.0
- npm: 10.9.2
- OS: Windows (PowerShell)
- Venv: d:\MLOps\ai-job-assistant\venv

---

## Tech Stack — Sirf Yahi Use Karo

```
LLM          → Groq API (free) — llama-3.1-8b-instant
Agents       → LangChain + LangGraph
RAG          → LlamaIndex + ChromaDB (local)
Voice STT    → openai-whisper (local, free)
Voice TTS    → Coqui TTS (local, free)
Voice RT     → LiveKit (open source)
Backend      → FastAPI + Uvicorn
Frontend     → Next.js 14 + React + TypeScript + Tailwind CSS
MCP Server   → Custom FastAPI-based Supervisor
MLOps        → MLflow (local logging)
Vector DB    → ChromaDB (local)
Metadata DB  → SQLite
Deploy       → Render (backend) + Vercel (frontend)
```

---

## 3 Agents — Final

### Agent 1 — CV + JD Analyzer
- CV aur JD lo, compare karo
- Match score 0-100
- Strengths + Gaps identify karo
- Output: structured JSON

### Agent 2 — Interview Question Generator
- Agent 1 output lo
- Personalized questions banao (Behavioral + Technical + Role-specific)
- Gaps pe hard, strengths pe medium difficulty
- Output: categorized question list JSON

### Agent 3 — Voice Interview Agent
- Agent 2 questions use karo
- LiveKit real-time voice
- Whisper STT + Coqui TTS
- Per-question scoring
- Final performance report

---

## Supervisor MCP Server
```
Location: backend/supervisor/mcp_server.py

Endpoints:
POST /dispatch   → agent ko task do
POST /report     → agent result wapas de
GET  /status     → current state dekho
POST /escalate   → max retry hit
```
Dynamic routing — sequential nahi. State dekh ke decide karta hai.

---

## Self-Healing Loop (Har Agent Mein)
```
Execute → Validate → PASS → Report to Supervisor
                  → FAIL → Self-Critique → Retry (max 3) → Escalate
```

---

## Folder Structure

```
ai-job-assistant/
├── CLAUDE.md
├── README.md
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── backend/
│   ├── main.py
│   ├── supervisor/
│   │   ├── __init__.py
│   │   ├── mcp_server.py
│   │   └── router.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py        ← SABSE IMPORTANT
│   │   ├── cv_analyzer/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── prompts.py
│   │   │   └── validator.py
│   │   ├── question_generator/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── prompts.py
│   │   │   └── validator.py
│   │   └── voice_interview/
│   │       ├── __init__.py
│   │       ├── agent.py
│   │       ├── prompts.py
│   │       └── validator.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── vector_store.py
│   │   ├── ingestion.py
│   │   └── retriever.py
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── stt.py
│   │   ├── tts.py
│   │   └── livekit_manager.py
│   ├── mlops/
│   │   ├── __init__.py
│   │   └── mlflow_logger.py
│   ├── database/
│   │   ├── __init__.py
│   │   └── models.py
│   └── utils/
│       ├── __init__.py
│       ├── config.py
│       └── logger.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── src/
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── page.tsx              ← Upload CV + JD
│       │   ├── results/
│       │   │   └── page.tsx          ← Score + gaps + questions
│       │   └── interview/
│       │       └── page.tsx          ← Voice interview
│       ├── components/
│       │   ├── CVUploader.tsx
│       │   ├── ScoreCard.tsx
│       │   ├── QuestionList.tsx
│       │   ├── VoiceInterface.tsx
│       │   └── ProgressTracker.tsx
│       └── lib/
│           └── api.ts
├── tests/
│   ├── test_phase1.py
│   ├── test_phase2.py
│   ├── test_phase3.py
│   └── FINAL_INTEGRATION_TEST.py
└── docs/
    └── SKILLS_NOTES.md

---

## README Update Rule — MANDATORY
Jab bhi koi cheez complete ho, README mein add karo:
1. Feature name
2. Roman Urdu mein kya kaam karta hai (2-3 lines)
3. Konsi skill use hui
4. Interview mein kaise explain karein
5. Workflow step by step

---

## Coding Rules
1. Har agent base_agent.py se inherit kare
2. Har output JSON schema validated ho
3. Self-healing mandatory — skip nahi
4. MLflow log karo har run pe
5. Type hints — Python + TypeScript dono
6. Docstrings har function pe
7. .env se keys — hardcode nahi
8. Loguru use karo print ki jagah

---

## Current Phase
PHASE 1 — Foundation
Status: STARTING NOW
