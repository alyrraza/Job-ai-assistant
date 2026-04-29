"use client";

// Voice Interview page — LiveKit token milne pe VoiceInterface, warna text simulation mode.
// startInterview() se livekit_token + livekit_url milte hain.
// 409 ya no-LiveKit = simulation mode (text-based answers).

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Loader2, AlertTriangle, Send, Award } from "lucide-react";
import { getResults, startInterview } from "@/lib/api";
import type { FullResults, QuestionItem, Questions } from "@/lib/api";
import VoiceInterface from "@/components/VoiceInterface";

export default function InterviewPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const sessionId = searchParams.get("session_id");

  const [results, setResults] = useState<FullResults | null>(null);
  const [livekitToken, setLivekitToken] = useState<string>("");
  const [livekitUrl, setLivekitUrl] = useState<string>("");
  const [roomName, setRoomName] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setError("session_id missing. Results page se dobara aaiye.");
      setLoading(false);
      return;
    }

    (async () => {
      try {
        // Fetch questions
        const data = await getResults(sessionId);
        if (!data.questions) {
          setError("Questions abhi ready nahi. Results page pe wait karo.");
          setLoading(false);
          return;
        }
        setResults(data);

        // Get LiveKit token — 409 or no LiveKit means simulation mode
        try {
          const interviewData = await startInterview(sessionId);
          setLivekitToken(interviewData.livekit_token ?? "");
          setLivekitUrl(interviewData.livekit_url ?? "");
          setRoomName(interviewData.room_name ?? "");
        } catch {
          // Interview already started (409) or LiveKit not configured — simulation mode
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Interview load karne mein error");
      } finally {
        setLoading(false);
      }
    })();
  }, [sessionId]);

  if (!sessionId || error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <AlertTriangle size={40} className="text-amber-400" />
        <p className="text-slate-300 text-center max-w-md">
          {error ?? "Invalid session ID"}
        </p>
        <button className="btn-secondary" onClick={() => router.push("/")}>
          Home Pe Wapis Jao
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 size={40} className="animate-spin text-indigo-400" />
        <p className="text-slate-300">Interview setup ho raha hai...</p>
        <p className="text-slate-500 text-sm">Agent 3 initialize ho raha hai</p>
      </div>
    );
  }

  if (!results?.questions) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <AlertTriangle size={40} className="text-amber-400" />
        <p className="text-slate-300">Questions load nahi hue</p>
        <button
          className="btn-secondary"
          onClick={() => router.push(`/results?session_id=${sessionId}`)}
        >
          Results Page Pe Wapis Jao
        </button>
      </div>
    );
  }

  // Voice mode — LiveKit configured and token received
  if (livekitToken) {
    return (
      <VoiceInterface
        sessionId={sessionId}
        questions={results.questions}
        livekitToken={livekitToken}
        roomName={roomName}
      />
    );
  }

  // Simulation mode — no LiveKit token (not configured or already started)
  return (
    <SimulationInterview
      sessionId={sessionId}
      questions={results.questions}
      livekitUrl={livekitUrl}
    />
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Text-based simulation interview — LiveKit nahi hone pe fallback
// ─────────────────────────────────────────────────────────────────────────────

function SimulationInterview({
  sessionId,
  questions,
  livekitUrl = "",
}: {
  sessionId: string;
  questions: Questions;
  livekitUrl?: string;
}) {
  const allQ: QuestionItem[] = [
    ...questions.behavioral,
    ...questions.technical,
    ...questions.role_specific,
  ];

  const [idx, setIdx] = useState(0);
  const [answer, setAnswer] = useState("");
  const [completed, setCompleted] = useState(false);

  const handleSubmit = () => {
    if (!answer.trim()) return;
    setAnswer("");
    if (idx + 1 >= allQ.length) {
      setCompleted(true);
    } else {
      setIdx((prev) => prev + 1);
    }
  };

  if (completed) {
    return (
      <div className="max-w-3xl mx-auto text-center space-y-6 py-12">
        <Award size={48} className="mx-auto text-indigo-400" />
        <h2 className="text-2xl font-bold text-slate-100">Interview Complete!</h2>
        <p className="text-slate-400 text-sm">
          Sab {allQ.length} sawaalon ke jawab submit ho gaye.
        </p>
        <a
          href={`/results?session_id=${sessionId}`}
          className="btn-secondary inline-flex items-center gap-2"
        >
          Results Dekho
        </a>
      </div>
    );
  }

  const current = allQ[idx];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Mock Interview</h1>
          <p className="text-slate-500 text-sm">
            {livekitUrl ? "Room: connected" : "Room: simulation mode (no LiveKit configured)"}
          </p>
        </div>
        <span className="text-slate-500 text-xs font-mono">
          {idx + 1} / {allQ.length}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-indigo-500 transition-all duration-500"
          style={{ width: `${(idx / allQ.length) * 100}%` }}
        />
      </div>

      {/* Question card */}
      <div className="card border border-indigo-700/30 bg-indigo-950/20">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-indigo-400 text-xs font-mono uppercase tracking-wide">
            {current.category.replace("_", " ")}
          </span>
          <span className={`badge-${current.difficulty}`}>{current.difficulty}</span>
          {current.skill_tag && (
            <span className="text-slate-500 text-xs bg-slate-800 px-2 py-0.5 rounded">
              {current.skill_tag}
            </span>
          )}
        </div>
        <p className="text-slate-100 text-lg leading-relaxed">{current.text}</p>
      </div>

      {/* Answer input */}
      <div className="card space-y-3">
        <label className="text-slate-400 text-sm font-medium">Apna Jawab</label>
        <textarea
          className="textarea-field"
          style={{ minHeight: "8rem" }}
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Yahan apna jawab type karo... (Ctrl+Enter se submit)"
          onKeyDown={(e) => {
            if (e.key === "Enter" && e.ctrlKey) handleSubmit();
          }}
        />
        <div className="flex items-center justify-between">
          <span className="text-slate-600 text-xs">{answer.length} chars</span>
          <button
            className="btn-primary flex items-center gap-2"
            onClick={handleSubmit}
            disabled={!answer.trim()}
          >
            <Send size={16} />
            {idx + 1 < allQ.length ? "Submit & Next" : "Submit Final Answer"}
          </button>
        </div>
      </div>
    </div>
  );
}
