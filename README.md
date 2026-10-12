# CV Interview Coach 🎯

> Paste your CV + job description → AI scores the match → lists your gaps → runs a voice mock interview

---

## What Is This?

You paste your CV and a job description. The AI does the rest:
- Compares the CV and JD — match score + skill gaps
- Generates personalized interview questions for that specific role
- Conducts a real-time voice interview, like a real interviewer
- Produces a performance report — where you are strong and where to improve

---

## Architecture

```
User (Next.js Frontend)
        ↓
FastAPI Backend
        ↓
Supervisor MCP Server (Brain — dynamic routing)
        ↓
┌─────────────────────────────────────┐
│  Agent 1: CV + JD Analyzer          │
│  Score + Gaps + Strengths           │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│  Agent 2: Question Generator        │
│  Behavioral + Technical + Role      │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│  Agent 3: Voice Interview           │
│  LiveKit + Whisper STT + Coqui TTS  │
└─────────────────────────────────────┘
        ↓
Results Dashboard (Next.js)
```

---

## Self-Healing System

Every agent has built-in automatic error recovery:
```
Output → Validator → Pass ✅ → Done
                  → Fail ❌ → Self-Critique → Retry (max 3) → Escalate
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Groq API — Llama 3.1 8B |
| Agents | LangChain + LangGraph |
| RAG | LlamaIndex + ChromaDB |
| Voice | LiveKit + Whisper + Coqui TTS |
| Backend | FastAPI + Uvicorn |
| Frontend | Next.js 14 + TypeScript + Tailwind |
| MLOps | MLflow (experiment tracking) |
| Deployment | Render + Vercel |

---

## Setup

```bash
# Clone
git clone https://github.com/alyrraza/Job-ai-assistant.git
cd Job-ai-assistant

# Python env
python -m venv venv
venv\Scripts\activate  # Windows

# Backend deps
pip install -r requirements.txt

# Frontend deps
cd frontend
npm install

# Environment
cp .env.example .env
# Add your GROQ_API_KEY to .env

# Run the backend
cd ..
python backend/main.py

# Run the frontend (in a new terminal)
cd frontend
npm run dev
```

---

## Screens

| Screen | URL | Purpose |
|---|---|---|
| Upload | / | Upload CV + JD |
| Results | /results | Score + gaps + questions |
| Interview | /interview | Voice mock interview |

---

## Agents Overview

### Agent 1 — CV + JD Analyzer
**What it does:** Compares the CV and JD, gives a 0-100 match score, and identifies strengths and gaps. It is the foundation for the other two agents.
**Tech:** LangChain + LangGraph + Groq LLM
**Design notes:** A LangChain chain parses the CV and JD into structured JSON, then the LLM performs a semantic comparison — meaning-based analysis rather than simple keyword matching.

### Agent 2 — Question Generator
**What it does:** Builds personalized interview questions from Agent 1's output. Hard questions on gaps, medium on strengths — targeted preparation.
**Tech:** LangChain + RAG (LlamaIndex + ChromaDB)
**Design notes:** RAG retrieves industry-specific question patterns. Question templates are stored in ChromaDB and retrieved semantically through LlamaIndex.

### Agent 3 — Voice Interview Agent
**What it does:** Conducts the interview in real-time voice. You speak, Whisper transcribes, the AI evaluates, and TTS delivers feedback — like a real interviewer.
**Tech:** LiveKit + Whisper STT + Coqui TTS + LangGraph
**Design notes:** A WebRTC-based real-time voice pipeline built on LiveKit. Whisper runs speech-to-text locally, the LLM evaluates the answer, and Coqui TTS produces audio feedback — end-to-end latency is about 1-2 seconds.

---

## MLOps

Every agent run is tracked with MLflow:
- Quality score per run
- Retry count
- Latency
- Token usage

---

## Development Progress

| Phase | Scope | Status |
|---|---|---|
| Phase 1 | Foundation + Structure | ✅ Done |
| Phase 2 | CV Analyzer + RAG Pipeline | ✅ Done |
| Phase 3 | Question Generator + Supervisor MCP | ✅ Done |
| Phase 4 | Voice Interview Agent | ✅ Done |
| Phase 5 | Backend API + Next.js Frontend | ✅ Done |

---

## Phase 2 — CV Analyzer Agent + RAG Pipeline (Complete)

### 1. CV Analyzer Agent (`backend/agents/cv_analyzer/`)

**What it does:**
Takes CV text and JD text and processes them with the Groq LLM (Llama 3.1 8B) in three steps — parse the CV, parse the JD, then run a semantic comparison of the two. The output is validated JSON containing the match score, strengths, gaps, and a summary.

**Tech used:** LangChain ChatPromptTemplate + ChatGroq + Pydantic v2 validation

**Design notes:**
A three-step LLM pipeline: CV parser → JD parser → comparison engine. Each step's output is validated against a JSON schema with Pydantic. If the LLM returns a malformed format, the self-healing loop retries automatically with a critique injected into the prompt — this behavior is inherited from `BaseAgent`.

**Workflow:**
1. `CVAnalyzerAgent.run({"cv_text": ..., "jd_text": ...})` is called
2. `execute()` → `CV_PARSE_PROMPT` → Groq → JSON parse
3. `execute()` → `JD_PARSE_PROMPT` → Groq → JSON parse
4. `execute()` → `COMPARISON_PROMPT` → Groq → JSON parse
5. `validate()` → `CVAnalysisOutput` Pydantic schema check
6. PASS: return `AgentResult` | FAIL: `self_critique()` → retry (max 3) → escalate
7. The run is logged to MLflow automatically

---

### 2. Pydantic Validator (`backend/agents/cv_analyzer/validator.py`)

**What it does:**
Checks whatever JSON the LLM returns against a strict schema. The match score range (0-100), non-empty lists, and summary length are all validated. Type coercion is built in (float score → int, string → list).

**Tech used:** Pydantic v2 BaseModel, field_validator, model_validate

**Design notes:**
LLM output is unreliable — sometimes a float arrives instead of an int, sometimes there are markdown fences. The Pydantic v2 validators coerce these edge cases and raise meaningful errors that the self-critique loop can use.

---

### 3. RAG Pipeline — Vector Store (`backend/rag/vector_store.py`)

**What it does:**
Sets up a local ChromaDB vector database with two collections: `cv_patterns` (successful CV-JD matches) and `interview_questions` (past interview questions). Semantic search uses cosine similarity.

**Tech used:** ChromaDB PersistentClient, cosine HNSW index

**Design notes:**
ChromaDB is configured with local persistence — no cloud needed. A singleton pattern ensures the app has a single DB connection. Cosine similarity was chosen because for text embeddings the direction matters, not the magnitude.

**Workflow:**
1. App start → `VectorStore.get_instance()` → open PersistentClient
2. `add_cv_pattern(id, text, embedding, metadata)` → add to the collection
3. `query_cv_patterns(embedding, n=3)` → return similar chunks

---

### 4. RAG Pipeline — Ingestion (`backend/rag/ingestion.py`)

**What it does:**
Takes a PDF or plain text, splits it into chunks with LlamaIndex (512 tokens, 64 overlap), embeds them with SentenceTransformer, and saves them to ChromaDB. Duplicates are detected via an MD5 hash.

**Tech used:** LlamaIndex SimpleDirectoryReader + SentenceSplitter, SentenceTransformer `all-MiniLM-L6-v2`

**Design notes:**
A local embedding model (MiniLM) means no paid API is needed for embeddings. The chunking strategy — 512 tokens with 64 overlap — balances context window size against retrieval precision.

**Workflow:**
1. `ingest_pdf(path)` → LlamaIndex load → SentenceSplitter → nodes
2. Each node → `embed_text()` → MiniLM vector
3. `store.add_cv_pattern(id, text, embedding, metadata)`
4. Duplicate: MD5 hash check → silently skip

---

### 5. RAG Pipeline — Retriever (`backend/rag/retriever.py`)

**What it does:**
Takes query text, builds a MiniLM embedding, fetches the top-3 similar chunks from ChromaDB, and returns a clean list. Scores are converted to a 0-1 scale (from ChromaDB cosine distance). The Question Generator agent uses this.

**Tech used:** ChromaDB query, cosine distance → similarity conversion

**Design notes:**
ChromaDB cosine distance lies on a 0-2 scale, which is converted to a 0-1 similarity with `1 - (dist/2)`. A `min_score` threshold filters out noisy results. The `format_chunks_for_prompt()` helper respects the token budget.

**Workflow:**
1. `retrieve_similar_cv_patterns(query, n=3)` is called
2. Embed the query with MiniLM
3. ChromaDB HNSW index search
4. Convert distance → similarity, sort, return a list of `RetrievedChunk`

---

## Contributors
- Ali Raza ([@alyrraza](https://github.com/alyrraza))

---

## Phase 3 — Question Generator Agent + Supervisor MCP Server (Complete)

### 1. Question Generator Agent (`backend/agents/question_generator/`)

**What it does:**
Takes the CV Analyzer's output — gaps, strengths, job title — and uses the Groq LLM to create personalized interview questions in three categories. Gaps get hard difficulty, strengths get medium. Similar question examples are retrieved via RAG for context.

**Tech used:** LangChain ChatPromptTemplate + ChatGroq + RAG retriever + Pydantic v2 model_validator

**Design notes:**
Agent 2 uses RAG-augmented generation — similar interview questions are first retrieved from ChromaDB (semantic search), then injected into the LLM prompt as examples. Difficulty calibration is automatic: gaps → hard, strengths → medium. A Pydantic model_validator auto-computes total_count and difficulty_distribution, so the pipeline never relies on the LLM to count.

**Workflow:**
1. Input: `CVAnalyzerAgent.data` dict (strengths, gaps, required_skills, _jd_parsed)
2. RAG: `retrieve_similar_questions(query)` → top-5 examples from ChromaDB
3. `BEHAVIORAL_PROMPT` → Groq → JSON array of 3 behavioral questions
4. `TECHNICAL_PROMPT` → Groq → JSON array of 4 technical questions
5. `ROLE_SPECIFIC_PROMPT` → Groq → JSON array of 2 role-specific questions
6. Merge → `QuestionGeneratorOutput.model_validate()` → auto-compute counts
7. PASS: return 9 questions | FAIL: self_critique() → retry (max 3)

---

### 2. Prompts — Difficulty Calibration (`backend/agents/question_generator/prompts.py`)

**What it does:**
Three category prompts — Behavioral, Technical, Role-Specific. Each prompt embeds difficulty rules: skills in the gaps list → hard, skills in the strengths list → medium. Both RAG context and critique injection are supported.

**Design notes:**
Difficulty calibration is hard-coded into the LLM instructions — the prompt explicitly says "if a skill is in GAPS, assign hard". This rule-based approach is more reliable than letting the LLM choose arbitrarily. For self-healing, a critique section is injected dynamically when the previous attempt failed.

---

### 3. Supervisor MCP Server (`backend/supervisor/mcp_server.py`)

**What it does:**
The orchestrator of the whole pipeline. It tracks each session's state, runs agents in the background, and auto-advances: Agent 1 done → Agent 2 starts automatically. It is mounted on FastAPI under the `/supervisor` prefix. The session store is in-memory and could be replaced with Redis in production.

**Tech used:** FastAPI BackgroundTasks + asyncio.Lock + asyncio.to_thread + Pydantic v2

**Design notes:**
The MCP server is an event-driven state machine. `asyncio.to_thread` runs blocking LLM calls in a separate thread so the async event loop (and FastAPI) is not blocked. `asyncio.Lock` prevents race conditions on concurrent requests. The Agent 1 → Agent 2 auto-advance uses `asyncio.ensure_future` — a push-based transition, not polling.

**Workflow:**
1. `POST /dispatch` → create new session → background task → run Agent 1
2. Agent 1 complete → state: `AGENT1_DONE` → auto-advance → run Agent 2
3. Agent 2 complete → state: `AGENT3_READY` → wait for the user
4. `GET /status` → the frontend checks progress
5. `POST /escalate` → max retries hit → state: `FAILED`

**State Machine:**
```
IDLE → AGENT1_RUNNING → AGENT1_DONE → AGENT2_RUNNING → AGENT2_DONE
     → AGENT3_READY → AGENT3_RUNNING → COMPLETED
     (any failure) → FAILED
```

---

### 4. Router — Dynamic Routing (`backend/supervisor/router.py`)

**What it does:**
The state machine transition table is defined here. The next agent is decided by looking at the current state. The agent factory also lives here — a class is instantiated from an agent name. Agent imports are here rather than in mcp_server.py to avoid circular imports.

**Design notes:**
The router is deliberately separate from mcp_server — separation of concerns: mcp_server handles the HTTP layer, the router handles business logic. Routing is declarative through the `_STATE_TO_AGENT` dict, so adding a new agent is a one-line change. `detect_parallel_ready()` is a future extension point for parallel agent execution.

**Workflow:**
1. `get_next_agent_name(state)` → transition table lookup
2. `build_agent(name, session_id)` → instantiate the correct agent class
3. `run_agent(name, session_id, input_data)` → `agent.run()` synchronously
4. The result goes back to `mcp_server.py`, which updates the state

---

## Phase 4 — Voice Interview Agent (Complete)

### 1. Speech-to-Text — `backend/voice/stt.py`

**What it does:**
Converts an audio file to text with the local Whisper "base" model — no API, no cost. Loading is lazy: the model is downloaded on the first call only and cached afterwards. The `is_silent()` helper detects empty answers so no LLM call is wasted on them.

**Tech used:** openai-whisper (local), wave module, lazy singleton pattern

**Design notes:**
The Whisper "base" model runs on CPU, has 74M parameters, and reaches roughly 95% English accuracy. Lazy loading solves the cold-start problem: the model loads only when the first audio arrives. `is_silent()` uses an RMS dB threshold to detect empty audio, saving the LLM from unnecessary zero-score calls.

**Workflow:** `transcribe(audio_path)` → load model (first time only) → Whisper inference → return clean text

---

### 2. Text-to-Speech — `backend/voice/tts.py`

**What it does:**
Converts text to a WAV audio file with Coqui TTS — entirely local. `speak_question_intro()` speaks a question along with its number, and `speak_follow_up()` handles follow-ups. Generated files are saved to `data/audio/tts/` with UUID names.

**Tech used:** Coqui TTS (tts_models/en/ljspeech/tacotron2-DDC), lazy loading

**Design notes:**
Coqui TTS is a production-quality open-source TTS. The tacotron2-DDC model runs at a reasonable speed even on CPU. Text is truncated at 500 characters because TTS quality degrades on long inputs. File names are UUID-based so concurrent sessions do not conflict.

**Workflow:** `speak(text)` → load TTS model (first time) → WAV synthesis → save `data/audio/tts/tts_XXXX.wav` → return path

---

### 3. LiveKit Manager — `backend/voice/livekit_manager.py`

**What it does:**
Manages the LiveKit WebRTC room — the agent publishes question audio and receives the user's answer audio. JWT token generation, WAV↔PCM conversion, and async/sync bridging are implemented here. If LiveKit is not configured there is a graceful fallback, so local testing is possible.

**Tech used:** LiveKit Python SDK (livekit.rtc + livekit.api), asyncio, wave, JWT tokens

**Design notes:**
LiveKit provides WebRTC for real-time voice — direct audio streaming, no HTTP polling. On the agent side, `publish_audio()` injects WAV frames into an AudioSource. `receive_audio()` consumes an AudioStream on the `track_subscribed` event and saves it as WAV. A sync wrapper built with `asyncio.run()` lets it work inside BaseAgent's synchronous `execute()`.

**Workflow:**
1. `generate_room_token()` → JWT with VideoGrants
2. `publish_audio(path)` → WAV→PCM chunks → LiveKit AudioFrames → broadcast
3. `receive_audio(timeout)` → track_subscribed → consume AudioStream → save PCM→WAV → return path

---

### 4. Voice Interview Agent — `backend/agents/voice_interview/agent.py`

**What it does:**
Agent 3 conducts the entire interview. For each question: it speaks via TTS, broadcasts on LiveKit, records the user's answer, transcribes with Whisper, and evaluates with the Groq LLM. If the score is 5 or lower, it also asks a follow-up question. At the end it generates a SessionReport.

**Tech used:** BaseAgent inheritance, ChatGroq (2 temperatures), TTS+STT+LiveKit integration, Pydantic v2

**Design notes:**
The voice agent uses two LLM instances — temperature=0.1 for evaluation (consistent scoring) and temperature=0.4 for feedback (varied suggestions). Empty-answer detection saves LLM calls. Follow-up logic: if score ≤ 5 AND the follow_up field is non-empty, a follow-up is asked automatically. Voice modules are lazily initialized, so import errors do not propagate at agent startup.

**Workflow:**
1. Input: `QuestionGeneratorAgent.data` (behavioral + technical + role_specific lists)
2. Flatten → ordered question list
3. Init voice modules (TTS, STT, LiveKitManager)
4. Per-question loop:
   - `speak_question_intro(text, n, total)` → WAV path
   - `livekit.publish_audio(path)` → user hears the question
   - `livekit.receive_audio(timeout=60)` → user's answer WAV
   - `transcribe(answer_wav)` → answer text
   - `_evaluate_answer()` → Groq → `AnswerEval` dict
   - Score ≤ 5 → follow-up question cycle
5. `_generate_session_feedback()` → Groq → overall feedback + recommendation
6. `validate()` → `SessionReport.model_validate()` → avg_score auto-computed
7. PASS → `AgentResult(success=True)` | FAIL → `self_critique()` → retry

---

### 5. Prompts — `backend/agents/voice_interview/prompts.py`

**What it does:**
Three prompt templates: EVAL_PROMPT (score an answer 0-10), FEEDBACK_PROMPT (overall assessment of the session), FOLLOW_UP_PROMPT (generate a targeted follow-up question). Each prompt ships with a scoring rubric.

**Design notes:**
The evaluation prompt embeds an explicit scoring rubric — 0-2: no answer, 3-4: partial, and so on. This anchors the LLM so scores stay consistent across questions. The feedback prompt also includes recommendation rules: avg >= 7 → hire, 5-6.9 → consider, < 5 → reject. These rule-based thresholds are more reliable than arbitrary LLM judgements.

---

### 6. Validators — `backend/agents/voice_interview/validator.py`

**What it does:**
`AnswerEval` (schema for a single answer) and `SessionReport` (schema for the full session) are Pydantic v2 models. `model_validator(mode='after')` auto-computes `avg_score`, `total_questions`, and `passed` — the pipeline never trusts the LLM to calculate an average.

**Design notes:**
SessionReport uses a model_validator for derived fields — avg_score = mean(answers.score) is computed directly, and whatever value the LLM provided is overwritten. A recommendation enum guarantees type safety — nothing other than 'hire/consider/reject' is accepted.

---

*Skill notes: `docs/SKILLS_NOTES.md`*

---

## Phase 5 — Backend API + Next.js Frontend (Complete)

### 1. Backend REST API + WebSocket — `backend/main.py`

**What it does:**
A FastAPI application exposing all the endpoints the frontend needs. Start a CV+JD analysis, check pipeline status, fetch results, start the interview — all over HTTP + WebSocket. `WebSocketManager` broadcasts real-time progress, so the frontend receives every state change immediately without polling.

**Tech used:** FastAPI lifespan, BackgroundTasks, WebSocket, asyncio polling, CORS middleware

**Design notes:**
The backend has a WebSocket-based real-time notification system. The WS handler checks state every 500ms and broadcasts only when the state changes, so no bandwidth is wasted. The `_strip_internal()` helper keeps internal LLM keys (such as `_cv_parsed`, `_critique`) from reaching the frontend — a clean API contract. `asyncio.to_thread()` runs blocking agent calls inside the async context.

**Endpoints:**
```
POST /api/analyze              → submit CV + JD, returns session_id
GET  /api/status/{session_id}  → current pipeline state
GET  /api/results/{session_id} → full analysis output + questions + report
POST /api/interview/start/{id} → generate LiveKit token, start Agent 3
WS   /ws/{session_id}          → real-time state updates (JSON)
```

**Workflow:**
1. `POST /api/analyze` → create `_PipelineSession` → BackgroundTask → dispatch Agent 1
2. WS client connects → 500ms poll loop → broadcast `{"state": "agent1_running"}` on state change
3. Agent 1 done → auto-advance → Agent 2 → broadcast `agent2_done`
4. `GET /api/results` → `_strip_internal()` → return clean JSON
5. `POST /api/interview/start` → generate LiveKit token → start Agent 3 in the background
6. COMPLETED/FAILED → the WS closes

---

### 2. TypeScript API Client — `frontend/src/lib/api.ts`

**What it does:**
All frontend-to-backend communication goes through here. TypeScript interfaces are defined for every API response — type safety end to end. `createWebSocket()` does not auto-reconnect (by design — an interview session is one-shot). `pollUntil()` is a fallback helper for slow networks.

**Tech used:** TypeScript generics, fetch API, WebSocket, type-safe interfaces

**Design notes:**
The API layer keeps a single responsibility — only HTTP/WS calls, no business logic. TypeScript interfaces such as `AnalysisResult`, `Questions`, and `InterviewReport` mirror the backend Pydantic models, with no type assertions (`as any`). `pollUntil()` does not use exponential backoff because WebSocket is the primary channel — it is only an edge-case fallback.

**Key types:**
```typescript
AnalysisResult    → match_score, strengths, gaps, required_skills
Questions         → behavioral[], technical[], role_specific[]
InterviewReport   → avg_score, recommendation, strong_areas, weak_areas
WsStateUpdate     → state: string
```

---

### 3. Upload Page — `frontend/src/app/page.tsx`

**What it does:**
The main page for pasting the CV and JD. It has two `CVUploader` components — one for the CV, one for the JD. A sample-data button loads demo content. On submit, validation runs (CV min 50 chars, JD min 30 chars), then `analyzeCV()` is called and the user is redirected to `/results`.

**Tech used:** Next.js App Router, React hooks (useState, useRouter), form validation

**Design notes:**
The upload page is deliberately simple — no file upload, just a textarea. This is better for UX because copy-paste matches how job seekers actually work. Client-side validation avoids unnecessary API calls, and a loading state prevents double-submit.

**Workflow:** Paste CV → Paste JD → Validate → `analyzeCV(cv, jd)` → session_id → `/results?session_id=...`

---

### 4. Results Page — `frontend/src/app/results/page.tsx`

**What it does:**
A live dashboard for the pipeline. Real-time updates arrive over WebSocket — `ProgressTracker` shows each agent's status. When Agent 1 finishes, the `ScoreCard` (match score) and strengths/gaps badges appear. When Agent 2 completes, the `QuestionList` is shown. A "Start Interview" button leads to Agent 3.

**Tech used:** Next.js useSearchParams, WebSocket client, conditional rendering, React state

**Design notes:**
The results page uses progressive disclosure — data appears as it becomes available. WebSocket is the primary channel, and the polling fallback activates only if the WS fails. The session_id is stored in the URL via `useSearchParams()`, so state recovers even after a page refresh.

**Workflow:**
1. Read `session_id` from the URL
2. WS connect → state updates
3. `agent1_done` → `getResults()` → render ScoreCard + gaps
4. `agent2_done` → render QuestionList
5. "Start Interview" → `/interview?session_id=...`

---

### 5. ScoreCard Component — `frontend/src/components/ScoreCard.tsx`

**What it does:**
Displays the 0-100 match score as an SVG circular progress bar. The color changes with the score: green (≥70 strong match), amber (40-69 partial), red (<40 weak). A `stroke-dashoffset` CSS transition gives a smooth animation.

**Tech used:** SVG rendering, CSS animations, computed geometry (circumference math)

**Design notes:**
SVG path animation: `stroke-dasharray` = circumference, `stroke-dashoffset` = fill amount, which gives a smooth counter-animation with a CSS transition. The score thresholds follow business rules: 70+ strong match, 40-69 consider, below 40 rethink. Inline `style` props are used only for dynamic values — everything else is Tailwind.

---

### 6. VoiceInterface Component — `frontend/src/components/VoiceInterface.tsx`

**What it does:**
The complete UI for the voice interview. It shows the current question card, a phase indicator (waiting/asking/recording/evaluating), and per-question scores. Agent state changes are reflected over WebSocket. When the interview completes, a `FinalReport` sub-component shows the avg score, recommendation badge, strong/weak areas, improvement tips, and a per-question breakdown.

**Tech used:** React phase state machine, WebSocket integration, dynamic SVG/CSS, conditional rendering

**Design notes:**
VoiceInterface is a frontend state machine — the `InterviewPhase` type defines the possible states, and the `PhaseIndicator` component renders a different icon/animation for each. `FinalReport` is extracted into a separate component for separation of concerns. When a LiveKit token is present a real-time indicator is shown; when absent, a graceful fallback message appears.

**Phase states:** `waiting → asking → recording → evaluating → next → completed`

**FinalReport sections:**
- Hero card: avg_score + total_questions + recommendation badge (hire/consider/reject)
- Overall feedback paragraph
- Strong areas + Weak areas grid
- Top improvement tips (numbered list)
- Per-question score breakdown with `ScorePill`

---

### 7. Supporting Frontend Infrastructure

**`frontend/src/app/globals.css`** — Custom Tailwind component classes: `.card`, `.btn-primary`, `.btn-secondary`, `.textarea-field`, `.badge-hard/.badge-medium/.badge-easy`

**`frontend/src/components/ProgressTracker.tsx`** — 4-step pipeline tracker: CV+JD Uploaded → CV Analysis → Questions Generated → Voice Interview. done/running/pending states with animated connectors.

**`frontend/src/components/QuestionList.tsx`** — An accordion per category (behavioral/technical/role_specific). Each QuestionCard has a difficulty badge, skill_tag, and a collapsible follow-up.

**`frontend/src/components/CVUploader.tsx`** — A reusable textarea with character count, min-length validation, a red border when too short, and a clear button.

**Design notes:**
The frontend follows a component-driven architecture, with each component having a single responsibility. Semantic component classes (`.card`, `.btn-primary`) sit on top of Tailwind utilities, which keeps things consistent without a full design system. TypeScript strict mode catches prop type errors at build time rather than at runtime.
