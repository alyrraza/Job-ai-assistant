// Yeh file backend API ke saath communicate karti hai.
// Har endpoint ke liye ek typed function hai — components directly fetch nahi karte.
// BASE_URL env variable se aata hai — production mein Render URL set karo.

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AnalysisResult {
  match_score: number;
  strengths: string[];
  gaps: string[];
  required_skills: string[];
  candidate_skills: string[];
  summary: string;
  experience_match: boolean;
  education_match: boolean;
  top_missing_skill: string;
}

export interface QuestionItem {
  text: string;
  difficulty: "easy" | "medium" | "hard";
  category: "behavioral" | "technical" | "role_specific";
  skill_tag: string;
  follow_up: string;
}

export interface Questions {
  behavioral: QuestionItem[];
  technical: QuestionItem[];
  role_specific: QuestionItem[];
  total_count: number;
  difficulty_distribution: Record<string, number>;
}

export interface AnswerEval {
  score: number;
  feedback: string;
  strong_points: string[];
  weak_points: string[];
  follow_up: string;
  question_text: string;
  answer_text: string;
  category: string;
  skill_tag: string;
  difficulty: string;
}

export interface InterviewReport {
  answers: AnswerEval[];
  overall_feedback: string;
  weak_areas: string[];
  strong_areas: string[];
  top_improvement_tips: string[];
  recommendation: "hire" | "consider" | "reject";
  avg_score: number;
  total_questions: number;
  passed: boolean;
}

export interface PipelineStatus {
  session_id: string;
  state: string;
  agent1_done: boolean;
  agent2_done: boolean;
  agent3_done: boolean;
  questions_ready: boolean;
  interview_completed: boolean;
  error: string | null;
}

export interface FullResults {
  session_id: string;
  state: string;
  analysis: AnalysisResult | null;
  questions: Questions | null;
  interview_report: InterviewReport | null;
  error: string | null;
}

export interface InterviewStartResult {
  status: string;
  session_id: string;
  room_name: string;
  livekit_token: string;
  livekit_url: string;
}

export interface WsStateUpdate {
  type: "state_update" | "done" | "error";
  state: string;
  agent1_done?: boolean;
  agent2_done?: boolean;
  agent3_done?: boolean;
  questions_ready?: boolean;
  interview_completed?: boolean;
  error?: string | null;
  message?: string;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${path} failed (${res.status}): ${body}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** CV + JD text submit karo → session_id milega. */
export async function analyzeCV(
  cv_text: string,
  jd_text: string
): Promise<string> {
  const data = await apiFetch<{ session_id: string }>("/api/analyze", {
    method: "POST",
    body: JSON.stringify({ cv_text, jd_text }),
  });
  return data.session_id;
}

/** Current pipeline state lo. */
export async function getStatus(session_id: string): Promise<PipelineStatus> {
  return apiFetch<PipelineStatus>(`/api/status/${session_id}`);
}

/** Full results lo — partial ya complete. */
export async function getResults(session_id: string): Promise<FullResults> {
  return apiFetch<FullResults>(`/api/results/${session_id}`);
}

/** Voice interview shuru karo — Agent 3 dispatch hoga. */
export async function startInterview(
  session_id: string
): Promise<InterviewStartResult> {
  return apiFetch<InterviewStartResult>(`/api/interview/start/${session_id}`, { method: "POST" });
}

/** WebSocket connection create karo — real-time pipeline updates ke liye. */
export function createWebSocket(
  session_id: string,
  onMessage: (update: WsStateUpdate) => void,
  onClose?: () => void
): WebSocket {
  const ws = new WebSocket(`${WS_URL}/ws/${session_id}`);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as WsStateUpdate;
      onMessage(data);
    } catch {
      // ignore malformed messages
    }
  };

  ws.onclose = () => onClose?.();

  ws.onerror = (err) => {
    console.error("WebSocket error:", err);
  };

  return ws;
}

/** Poll status every N ms until condition met or max attempts reached. */
export async function pollUntil(
  session_id: string,
  condition: (status: PipelineStatus) => boolean,
  intervalMs = 1500,
  maxAttempts = 60
): Promise<PipelineStatus> {
  for (let i = 0; i < maxAttempts; i++) {
    const s = await getStatus(session_id);
    if (condition(s) || s.state === "failed") return s;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error("Polling timeout — backend may be slow");
}
