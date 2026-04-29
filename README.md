# CV Interview Coach 🎯

> CV + JD daalo → AI score karta hai → gaps batata hai → voice mock interview leta hai

---

## Kya Hai Yeh? (Roman Urdu)

Tum apna CV aur job description paste karte ho. Baaki sab AI karta hai:
- CV aur JD compare karta hai — match score + skill gaps
- Us specific role ke liye personalized interview questions generate karta hai  
- Real-time voice interview leta hai — bilkul real interviewer ki tarah
- Performance report deta hai — kahan strong ho, kahan improve karo

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

Har agent ke andar automatic error recovery:
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
cd ai-job-assistant

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
# .env mein GROQ_API_KEY daalo

# Backend run karo
cd ..
python backend/main.py

# Frontend run karo (naye terminal mein)
cd frontend
npm run dev
```

---

## Screens

| Screen | URL | Kaam |
|---|---|---|
| Upload | / | CV + JD upload |
| Results | /results | Score + gaps + questions |
| Interview | /interview | Voice mock interview |

---

## Agents Detail

### Agent 1 — CV + JD Analyzer
**Kaam (Roman Urdu):** CV aur JD ko compare karta hai, match score 0-100 deta hai, strengths aur gaps identify karta hai. Yeh baaki dono agents ki foundation hai.
**Skill:** LangChain + LangGraph + Groq LLM
**Interview mein bolna:** "Maine LangChain chain banaya jo CV aur JD ko structured JSON mein parse karta hai, phir LLM se semantic comparison karta hai — simple keyword matching nahi, meaning-based analysis hai."

### Agent 2 — Question Generator
**Kaam (Roman Urdu):** Agent 1 ke output ke basis pe personalized interview questions banata hai. Gaps pe hard questions, strengths pe medium — bilkul targeted preparation.
**Skill:** LangChain + RAG (LlamaIndex + ChromaDB)
**Interview mein bolna:** "RAG use kiya hai taake industry-specific question patterns retrieve kar sakein. ChromaDB mein question templates store hain, LlamaIndex se semantic retrieval hoti hai."

### Agent 3 — Voice Interview Agent
**Kaam (Roman Urdu):** Real-time voice mein interview leta hai. Tum bolte ho, Whisper sunta hai, AI evaluate karta hai, TTS se feedback deta hai. Bilkul real interviewer jaisa.
**Skill:** LiveKit + Whisper STT + Coqui TTS + LangGraph
**Interview mein bolna:** "WebRTC-based real-time voice pipeline banaya hai LiveKit se. Whisper local pe speech-to-text karta hai, LLM response evaluate karta hai, Coqui TTS se audio feedback aata hai — end-to-end latency 1-2 seconds hai."

---

## MLOps

MLflow se har agent run track hota hai:
- Quality score per run
- Retry count
- Latency
- Token usage

---

## Development Progress

| Phase | Kya | Status |
|---|---|---|
| Phase 1 | Foundation + Structure | ✅ Done |
| Phase 2 | CV Analyzer + RAG Pipeline | ✅ Done |
| Phase 3 | Question Generator + Supervisor MCP | ✅ Done |
| Phase 4 | Voice Interview Agent | ✅ Done |
| Phase 5 | Backend API + Next.js Frontend | ✅ Done |

---

## Phase 2 — CV Analyzer Agent + RAG Pipeline (Complete)

### 1. CV Analyzer Agent (`backend/agents/cv_analyzer/`)

**Kya kaam karta hai (Roman Urdu):**
CV text aur JD text lo, Groq LLM (Llama 3.1 8B) se teen step mein process karo — pehle CV parse karo, phir JD parse karo, phir dono ka semantic comparison karo. Output ek validated JSON hai jisme match score, strengths, gaps, aur summary hoti hai.

**Konsi skill use hui:** LangChain ChatPromptTemplate + ChatGroq + Pydantic v2 validation

**Interview mein kaise explain karein:**
"Maine teen-step LLM pipeline banaya: CV parser → JD parser → comparison engine. Har step ka output JSON schema se validate hota hai Pydantic se. Agar LLM galat format return kare toh self-healing loop automatically retry karta hai with critique injected in the prompt — yeh BaseAgent se inherit hota hai."

**Workflow step by step:**
1. `CVAnalyzerAgent.run({"cv_text": ..., "jd_text": ...})` call hota hai
2. `execute()` → `CV_PARSE_PROMPT` → Groq → JSON parse
3. `execute()` → `JD_PARSE_PROMPT` → Groq → JSON parse
4. `execute()` → `COMPARISON_PROMPT` → Groq → JSON parse
5. `validate()` → `CVAnalysisOutput` Pydantic schema check
6. PASS: `AgentResult` return | FAIL: `self_critique()` → retry (max 3) → escalate
7. MLflow mein run log hota hai automatically

---

### 2. Pydantic Validator (`backend/agents/cv_analyzer/validator.py`)

**Kya kaam karta hai (Roman Urdu):**
LLM jo bhi JSON return kare usse is strict schema se check karo. Match score range (0-100), non-empty lists, summary length — sab validate hota hai. Type coercion bhi built-in hai (float score → int, string → list).

**Konsi skill use hui:** Pydantic v2 BaseModel, field_validator, model_validate

**Interview mein kaise explain karein:**
"LLM output unreliable hota hai — kabhi float aata hai int ki jagah, kabhi markdown fences hoti hain. Maine Pydantic v2 validators likhe jo coerce karte hain ye edge cases aur meaningful errors dete hain jo self-critique loop use kar sake."

---

### 3. RAG Pipeline — Vector Store (`backend/rag/vector_store.py`)

**Kya kaam karta hai (Roman Urdu):**
ChromaDB local vector database setup karta hai. Do collections hain: `cv_patterns` (successful CV-JD matches) aur `interview_questions` (past interview questions). Cosine similarity se semantic search hoti hai.

**Konsi skill use hui:** ChromaDB PersistentClient, cosine HNSW index

**Interview mein kaise explain karein:**
"ChromaDB ko local persistence ke saath set kiya — koi cloud nahi chahiye. Singleton pattern use kiya taake app mein sirf ek DB connection ho. Cosine similarity space choose kiya kyunki text embeddings ke liye magnitude matter nahi karti, sirf direction matter karti hai."

**Workflow:**
1. App start → `VectorStore.get_instance()` → PersistentClient open karo
2. `add_cv_pattern(id, text, embedding, metadata)` → collection mein add
3. `query_cv_patterns(embedding, n=3)` → similar chunks return

---

### 4. RAG Pipeline — Ingestion (`backend/rag/ingestion.py`)

**Kya kaam karta hai (Roman Urdu):**
PDF ya plain text lo, LlamaIndex se chunks banao (512 tokens, 64 overlap), SentenceTransformer se embed karo, ChromaDB mein save karo. Duplicate detection MD5 hash se hoti hai.

**Konsi skill use hui:** LlamaIndex SimpleDirectoryReader + SentenceSplitter, SentenceTransformer `all-MiniLM-L6-v2`

**Interview mein kaise explain karein:**
"Local embedding model use kiya (MiniLM) taake Groq API calls save hoon — embeddings ke liye paid API zaroorat nahi. Chunking strategy: 512 tokens with 64 overlap — yeh context window aur retrieval precision ka balance hai."

**Workflow:**
1. `ingest_pdf(path)` → LlamaIndex load → SentenceSplitter → nodes
2. Har node → `embed_text()` → MiniLM vector
3. `store.add_cv_pattern(id, text, embedding, metadata)`
4. Duplicate: MD5 hash check → silently skip

---

### 5. RAG Pipeline — Retriever (`backend/rag/retriever.py`)

**Kya kaam karta hai (Roman Urdu):**
Query text do → MiniLM embedding banao → ChromaDB se top-3 similar chunks lo → clean list return karo. Score 0-1 scale pe convert hota hai (ChromaDB cosine distance se). Question Generator agent yeh use karega.

**Konsi skill use hui:** ChromaDB query, cosine distance → similarity conversion

**Interview mein kaise explain karein:**
"ChromaDB cosine distance 0-2 scale pe hota hai — maine isse 0-1 similarity mein convert kiya: `1 - (dist/2)`. `min_score` threshold se noisy results filter hote hain. `format_chunks_for_prompt()` helper token budget respect karta hai."

**Workflow:**
1. `retrieve_similar_cv_patterns(query, n=3)` call
2. Query embed karo MiniLM se
3. ChromaDB HNSW index search
4. Distance → similarity convert, sort, return `RetrievedChunk` list

---

## Contributors
- Ali Raza ([@alyrraza](https://github.com/alyrraza))

---

## Phase 3 — Question Generator Agent + Supervisor MCP Server (Complete)

### 1. Question Generator Agent (`backend/agents/question_generator/`)

**Kya kaam karta hai (Roman Urdu):**
CV Analyzer ka output lo — gaps, strengths, job title — aur Groq LLM se teen category mein personalized interview questions banao. Gaps pe hard difficulty assign hoti hai, strengths pe medium. RAG se similar question examples context ke liye retrieve hote hain.

**Konsi skill use hui:** LangChain ChatPromptTemplate + ChatGroq + RAG retriever + Pydantic v2 model_validator

**Interview mein kaise explain karein:**
"Agent 2 mein RAG-augmented generation use kiya — pehle ChromaDB se similar interview questions retrieve kiye (semantic search), phir un examples ko LLM prompt mein inject kiya. Difficulty calibration automatic hai: gaps → hard, strengths → medium. Pydantic model_validator se total_count aur difficulty_distribution auto-compute hote hain — LLM pe count karne ka bharosa nahi karte."

**Workflow step by step:**
1. Input: `CVAnalyzerAgent.data` dict (strengths, gaps, required_skills, _jd_parsed)
2. RAG: `retrieve_similar_questions(query)` → top-5 examples from ChromaDB
3. `BEHAVIORAL_PROMPT` → Groq → 3 behavioral questions JSON array
4. `TECHNICAL_PROMPT` → Groq → 4 technical questions JSON array
5. `ROLE_SPECIFIC_PROMPT` → Groq → 2 role-specific questions JSON array
6. Merge → `QuestionGeneratorOutput.model_validate()` → auto-compute counts
7. PASS: return 9 questions | FAIL: self_critique() → retry (max 3)

---

### 2. Prompts — Difficulty Calibration (`backend/agents/question_generator/prompts.py`)

**Kya kaam karta hai (Roman Urdu):**
Teen category ke prompts hain — Behavioral, Technical, Role-Specific. Har prompt mein difficulty rules embed hain: gaps list → hard, strengths list → medium. RAG context aur critique injection dono support karta hai.

**Interview mein kaise explain karein:**
"Difficulty calibration LLM instruction mein hard-coded hai — prompt mein clearly likha hai 'agar skill GAPS mein hai toh hard assign karo'. Ye rule-based approach LLM ke arbitrary choices se zyada reliable hai. Self-healing ke liye critique section dynamically inject hota hai agar previous attempt fail ho."

---

### 3. Supervisor MCP Server (`backend/supervisor/mcp_server.py`)

**Kya kaam karta hai (Roman Urdu):**
Poori pipeline ka orchestrator hai. Har session ka state track karta hai, agents background mein chalata hai, aur auto-advance karta hai: Agent 1 done → automatically Agent 2 start. FastAPI pe mount hua hai `/supervisor` prefix pe. In-memory session store hai — production mein Redis se replace ho sakta hai.

**Konsi skill use hui:** FastAPI BackgroundTasks + asyncio.Lock + asyncio.to_thread + Pydantic v2

**Interview mein kaise explain karein:**
"MCP server ek event-driven state machine hai. `asyncio.to_thread` se blocking LLM calls ko async event loop se alag thread mein chalaya — FastAPI block nahi hota. `asyncio.Lock` se concurrent requests pe race conditions se bacha. Agent1 → Agent2 auto-advance `asyncio.ensure_future` se hoti hai — polling nahi, push-based transition hai."

**Workflow step by step:**
1. `POST /dispatch` → new session create → background task → Agent 1 run
2. Agent 1 complete → state: `AGENT1_DONE` → auto-advance → Agent 2 run
3. Agent 2 complete → state: `AGENT3_READY` → wait for user
4. `GET /status` → frontend polling se progress check
5. `POST /escalate` → max retries hit → state: `FAILED`

**State Machine:**
```
IDLE → AGENT1_RUNNING → AGENT1_DONE → AGENT2_RUNNING → AGENT2_DONE
     → AGENT3_READY → AGENT3_RUNNING → COMPLETED
     (any failure) → FAILED
```

---

### 4. Router — Dynamic Routing (`backend/supervisor/router.py`)

**Kya kaam karta hai (Roman Urdu):**
State machine transition table yahan define hai. Current state dekh ke next agent decide hota hai. Agent factory bhi yahan hai — agent name se class instantiate hoti hai. Circular imports se bachne ke liye agent imports yahan hain, mcp_server.py mein nahi.

**Interview mein kaise explain karein:**
"Router ko deliberately mcp_server se alag rakha — separation of concerns. mcp_server HTTP layer sambhalta hai, router business logic. `_STATE_TO_AGENT` dict se routing declarative hai — naya agent add karna sirf ek line ka kaam hai. `detect_parallel_ready()` future extension point hai jab parallel agent execution add karni ho."

**Workflow:**
1. `get_next_agent_name(state)` → transition table lookup
2. `build_agent(name, session_id)` → correct agent class instantiate
3. `run_agent(name, session_id, input_data)` → `agent.run()` synchronously
4. Result wapas `mcp_server.py` ko — state update hoti hai

---

## Phase 4 — Voice Interview Agent (Complete)

### 1. Speech-to-Text — `backend/voice/stt.py`

**Kya kaam karta hai (Roman Urdu):**
Local Whisper "base" model se audio file ko text mein convert karta hai — koi API nahi, koi cost nahi. Lazy loading hai: sirf pehli call pe model download hota hai, baad mein cache mein rehta hai. `is_silent()` helper empty answers detect karta hai taake LLM call waste na ho.

**Konsi skill use hui:** openai-whisper (local), wave module, lazy singleton pattern

**Interview mein kaise explain karein:**
"Whisper 'base' model choose kiya — CPU pe chalata hai, 74M parameters, English accuracy ~95%. Lazy loading se cold start problem solve ki: model sirf tab load hota hai jab pehla audio aata hai. `is_silent()` se empty audio detect karta hai — RMS dB threshold use kiya, LLM ko unnecessary zero-score calls se bachaya."

**Workflow:** `transcribe(audio_path)` → model load (if first time) → Whisper inference → clean text return

---

### 2. Text-to-Speech — `backend/voice/tts.py`

**Kya kaam karta hai (Roman Urdu):**
Coqui TTS se text ko WAV audio file mein convert karta hai — bilkul local. `speak_question_intro()` question number ke saath bolta hai, `speak_follow_up()` follow-up ke liye. Generated files `data/audio/tts/` mein UUID-named save hoti hain.

**Konsi skill use hui:** Coqui TTS (tts_models/en/ljspeech/tacotron2-DDC), lazy loading

**Interview mein kaise explain karein:**
"Coqui TTS choose kiya kyunki yeh production-quality open-source TTS hai. tacotron2-DDC model CPU pe bhi reasonable speed pe chalta hai. Text 500 chars pe truncate kiya — TTS quality long inputs pe degrade hoti hai. File naming UUID-based hai taake concurrent sessions conflict na karein."

**Workflow:** `speak(text)` → TTS model load (first time) → WAV synthesis → `data/audio/tts/tts_XXXX.wav` save → path return

---

### 3. LiveKit Manager — `backend/voice/livekit_manager.py`

**Kya kaam karta hai (Roman Urdu):**
LiveKit WebRTC room manage karta hai — agent question audio publish karta hai, user ka answer audio receive karta hai. JWT token generation, WAV↔PCM conversion, aur async/sync bridging yahan implement hua hai. LiveKit configure nahi hai toh graceful fallback hai — local testing possible hai.

**Konsi skill use hui:** LiveKit Python SDK (livekit.rtc + livekit.api), asyncio, wave, JWT tokens

**Interview mein kaise explain karein:**
"LiveKit WebRTC use kiya real-time voice ke liye — direct audio streaming, no HTTP polling. Agent side pe publish_audio() AudioSource mein WAV frames inject karta hai. receive_audio() track_subscribed event pe AudioStream consume karta hai aur WAV mein save karta hai. asyncio.run() se sync wrapper banaya taake BaseAgent ke synchronous execute() mein kaam kare."

**Workflow:**
1. `generate_room_token()` → JWT with VideoGrants
2. `publish_audio(path)` → WAV→PCM chunks → LiveKit AudioFrames → broadcast
3. `receive_audio(timeout)` → track_subscribed → AudioStream consume → PCM→WAV save → path return

---

### 4. Voice Interview Agent — `backend/agents/voice_interview/agent.py`

**Kya kaam karta hai (Roman Urdu):**
Agent 3 — poora interview conduct karta hai. Har sawal ke liye: TTS se bolta hai, LiveKit pe broadcast karta hai, user ka jawab record karta hai, Whisper se transcribe karta hai, Groq LLM se evaluate karta hai. Score 5 ya kam ho toh follow-up question bhi puchta hai. End mein SessionReport generate karta hai.

**Konsi skill use hui:** BaseAgent inheritance, ChatGroq (2 temperatures), TTS+STT+LiveKit integration, Pydantic v2

**Interview mein kaise explain karein:**
"Voice agent mein do LLM instances use kiye — eval ke liye temperature=0.1 (consistent scoring), feedback ke liye temperature=0.4 (varied suggestions). Empty answer detection se LLM calls save kiye. Follow-up logic: score ≤ 5 AND non-empty follow_up field toh automatically follow-up ask hota hai. Voice modules lazy-init hain — import errors propagate nahi hote agent startup pe."

**Workflow step by step:**
1. Input: `QuestionGeneratorAgent.data` (behavioral + technical + role_specific lists)
2. Flatten → ordered question list
3. Init voice modules (TTS, STT, LiveKitManager)
4. Per question loop:
   - `speak_question_intro(text, n, total)` → WAV path
   - `livekit.publish_audio(path)` → user hears question
   - `livekit.receive_audio(timeout=60)` → user's answer WAV
   - `transcribe(answer_wav)` → answer text
   - `_evaluate_answer()` → Groq → `AnswerEval` dict
   - Score ≤ 5 → follow-up question cycle
5. `_generate_session_feedback()` → Groq → overall feedback + recommendation
6. `validate()` → `SessionReport.model_validate()` → avg_score auto-computed
7. PASS → `AgentResult(success=True)` | FAIL → `self_critique()` → retry

---

### 5. Prompts — `backend/agents/voice_interview/prompts.py`

**Kya kaam karta hai (Roman Urdu):**
Teen prompt templates: EVAL_PROMPT (answer score karo 0-10), FEEDBACK_PROMPT (session ka overall assessment), FOLLOW_UP_PROMPT (targeted follow-up question generate karo). Har prompt scoring rubric ke saath آتا hai.

**Interview mein kaise explain karein:**
"Evaluation prompt mein explicit scoring rubric embed kiya — 0-2: no answer, 3-4: partial, etc. Yeh LLM ko anchor deta hai taake scores consistent hon across questions. Feedback prompt recommendation ke rules bhi include karta hai: avg>=7 → hire, 5-6.9 → consider, <5 → reject. Yeh rule-based threshold LLM ke arbitrary judgements se zyada reliable hai."

---

### 6. Validators — `backend/agents/voice_interview/validator.py`

**Kya kaam karta hai (Roman Urdu):**
`AnswerEval` (single answer ka schema) aur `SessionReport` (full session ka schema) Pydantic v2 models hain. `model_validator(mode='after')` se `avg_score`, `total_questions`, aur `passed` auto-compute hote hain — LLM pe average calculate karne ka bharosa nahi karte.

**Interview mein kaise explain karein:**
"SessionReport mein model_validator use kiya derived fields ke liye — avg_score = mean(answers.score) khud calculate hota hai. LLM ne jo bhi value diya woh overwrite ho jaata hai. Recommendation enum se type safety guarantee hai — 'hire/consider/reject' ke علاوہ kuch accept nahi hota."

---

*Interview + skill notes: `docs/SKILLS_NOTES.md`*

---

## Phase 5 — Backend API + Next.js Frontend (Complete)

### 1. Backend REST API + WebSocket — `backend/main.py`

**Kya kaam karta hai (Roman Urdu):**
FastAPI application hai jo frontend ke liye saare endpoints expose karta hai. CV+JD analysis start karo, pipeline status check karo, results lo, interview start karo — sab kuch HTTP + WebSocket se. `WebSocketManager` real-time progress broadcast karta hai — frontend ko har state change immediately milta hai bina polling ke.

**Konsi skill use hui:** FastAPI lifespan, BackgroundTasks, WebSocket, asyncio polling, CORS middleware

**Interview mein kaise explain karein:**
"Backend mein WebSocket-based real-time notification system banaya. WS handler har 500ms pe state check karta hai aur sirf tab broadcast karta hai jab state change ho — bandwidth waste nahi hoti. `_strip_internal()` helper se internal LLM keys (jaise `_cv_parsed`, `_critique`) frontend tak nahi pahunchte — clean API contract. `asyncio.to_thread()` se blocking agent calls async context mein run hote hain."

**Endpoints:**
```
POST /api/analyze              → CV + JD submit, session_id return
GET  /api/status/{session_id}  → pipeline current state
GET  /api/results/{session_id} → full analysis output + questions + report
POST /api/interview/start/{id} → LiveKit token generate, Agent 3 start
WS   /ws/{session_id}          → real-time state updates (JSON)
```

**Workflow step by step:**
1. `POST /api/analyze` → `_PipelineSession` create → BackgroundTask → Agent 1 dispatch
2. WS client connect → 500ms poll loop → state change pe `{"state": "agent1_running"}` broadcast
3. Agent 1 done → auto-advance → Agent 2 → `agent2_done` broadcast
4. `GET /api/results` → `_strip_internal()` → clean JSON return
5. `POST /api/interview/start` → LiveKit token generate → Agent 3 background mein start
6. COMPLETED/FAILED → WS close hoti hai

---

### 2. TypeScript API Client — `frontend/src/lib/api.ts`

**Kya kaam karta hai (Roman Urdu):**
Frontend ka poora backend communication yahan se hota hai. TypeScript interfaces sab API responses ke liye define hain — type safety end-to-end. `createWebSocket()` auto-reconnection nahi karta (by design — interview session one-shot hoti hai). `pollUntil()` helper slow networks ke liye fallback hai.

**Konsi skill use hui:** TypeScript generics, fetch API, WebSocket, type-safe interfaces

**Interview mein kaise explain karein:**
"API layer mein single responsibility raha — sirf HTTP/WS calls, koi business logic nahi. `AnalysisResult`, `Questions`, `InterviewReport` jaise TypeScript interfaces define kiye jo backend Pydantic models se match karte hain — koi type assertion (`as any`) nahi. `pollUntil()` exponential backoff nahi karta kyunki WS primary hai — yeh sirf edge case fallback hai."

**Key types:**
```typescript
AnalysisResult    → match_score, strengths, gaps, required_skills
Questions         → behavioral[], technical[], role_specific[]
InterviewReport   → avg_score, recommendation, strong_areas, weak_areas
WsStateUpdate     → state: string
```

---

### 3. Upload Page — `frontend/src/app/page.tsx`

**Kya kaam karta hai (Roman Urdu):**
CV aur JD paste karne ka main page hai. Do `CVUploader` components hain — ek CV ke liye, ek JD ke liye. Sample data button se demo content load hota hai. Submit pe validation hoti hai (CV min 50 chars, JD min 30 chars), phir `analyzeCV()` call hoti hai aur `/results` page pe redirect.

**Konsi skill use hui:** Next.js App Router, React hooks (useState, useRouter), form validation

**Interview mein kaise explain karein:**
"Upload page deliberately simple rakha — koi file upload nahi, sirf textarea. Yeh user experience ke liye better hai: copy-paste se job seekers ka workflow match karta hai. Client-side validation se unnecessary API calls avoid hoti hain. Loading state se double-submit prevent hota hai."

**Workflow:** Paste CV → Paste JD → Validate → `analyzeCV(cv, jd)` → session_id → `/results?session_id=...`

---

### 4. Results Page — `frontend/src/app/results/page.tsx`

**Kya kaam karta hai (Roman Urdu):**
Pipeline ka live dashboard hai. WebSocket se real-time updates aate hain — `ProgressTracker` har agent ka status dikhata hai. Jab Agent 1 done ho jaata hai, `ScoreCard` (match score) aur strengths/gaps badges appear hote hain. Jab Agent 2 complete ho, `QuestionList` show hota hai. "Start Interview" button Agent 3 ke liye.

**Konsi skill use hui:** Next.js useSearchParams, WebSocket client, conditional rendering, React state

**Interview mein kaise explain karein:**
"Results page progressive disclosure use karta hai — data jaise-jaise available hoti hai waise-waise appear hoti hai. WebSocket primary channel hai, polling fallback sirf WS fail hone pe activate hota hai. `useSearchParams()` se URL mein session_id stored hai — page refresh pe bhi state recover hoti hai."

**Workflow:**
1. `session_id` URL se read
2. WS connect → state updates
3. `agent1_done` → `getResults()` → ScoreCard + gaps render
4. `agent2_done` → QuestionList render
5. "Start Interview" → `/interview?session_id=...`

---

### 5. ScoreCard Component — `frontend/src/components/ScoreCard.tsx`

**Kya kaam karta hai (Roman Urdu):**
Match score 0-100 ko SVG circular progress bar mein dikhata hai. Score ke hisaab se color change hota hai: green (≥70 strong match), amber (40-69 partial), red (<40 weak). `stroke-dashoffset` CSS transition se smooth animation hai.

**Konsi skill use hui:** SVG rendering, CSS animations, computed geometry (circumference math)

**Interview mein kaise explain karein:**
"SVG path animation use kiya — `stroke-dasharray` = circumference, `stroke-dashoffset` = fill amount. Yeh CSS transition ke saath smooth counter-animation deta hai. Score thresholds business rules se define hain: 70+ strong match, 40-69 consider, below 40 rethink. Inline `style` props sirf dynamic values ke liye use kiye — baaki Tailwind."

---

### 6. VoiceInterface Component — `frontend/src/components/VoiceInterface.tsx`

**Kya kaam karta hai (Roman Urdu):**
Voice interview ka poora UI hai. Current question card, phase indicator (waiting/asking/recording/evaluating), aur per-question scores dikhata hai. WebSocket se agent ki state changes reflect hoti hain. Interview complete hone pe `FinalReport` sub-component show hota hai jisme avg score, recommendation badge, strong/weak areas, improvement tips, aur per-question breakdown hai.

**Konsi skill use hui:** React phase state machine, WebSocket integration, dynamic SVG/CSS, conditional rendering

**Interview mein kaise explain karein:**
"VoiceInterface ek frontend state machine hai — `InterviewPhase` type se possible states define hain, `PhaseIndicator` component har state ke liye alag icon/animation render karta hai. `FinalReport` separate component mein extract kiya — separation of concerns. LiveKit token present hone pe real-time indicator show hota hai, absent hone pe graceful fallback message."

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

**`frontend/src/components/QuestionList.tsx`** — Accordion per category (behavioral/technical/role_specific). QuestionCard mein difficulty badge, skill_tag, aur collapsible follow-up.

**`frontend/src/components/CVUploader.tsx`** — Reusable textarea with char count, min-length validation, red border on tooShort, clear button.

**Interview mein bolna:**
"Frontend mein component-driven architecture rakhi — har component single responsibility ke saath. Tailwind utility classes ke upar semantic component classes define kiye (`.card`, `.btn-primary`) — yeh consistency guarantee karta hai without a full design system. TypeScript strict mode se prop type errors build time pe catch hote hain, runtime nahi."
