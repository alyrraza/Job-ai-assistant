"use client";

// Results page — CV analysis score, strengths/gaps, generated questions dikhao.
// WebSocket se live pipeline progress milti hai — polling fallback bhi hai.
// "Start Interview" button se voice interview /interview page pe jaata hai.

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Mic,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import { getResults, getStatus, createWebSocket, startInterview } from "@/lib/api";
import type { FullResults, WsStateUpdate } from "@/lib/api";
import ScoreCard from "@/components/ScoreCard";
import QuestionList from "@/components/QuestionList";
import ProgressTracker from "@/components/ProgressTracker";

type LoadState = "loading" | "analyzing" | "questions_ready" | "error" | "failed";

export default function ResultsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");

  const [results, setResults] = useState<FullResults | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [pipelineState, setPipelineState] = useState<string>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const startedRef = useRef(false);

  const fetchResults = useCallback(async () => {
    if (!sessionId) return;
    try {
      const data = await getResults(sessionId);
      setResults(data);
      if (data.error) {
        setErrorMsg(data.error);
        setLoadState("failed");
      } else if (data.questions) {
        setLoadState("questions_ready");
      } else {
        setLoadState("analyzing");
      }
      setPipelineState(data.state);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Results load karne mein error");
      setLoadState("error");
    }
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) {
      setErrorMsg("session_id URL mein nahi mila. Upload page se dobara try karo.");
      setLoadState("error");
      return;
    }

    fetchResults();

    // WebSocket for live updates
    const ws = createWebSocket(
      sessionId,
      (update: WsStateUpdate) => {
        setPipelineState(update.state);
        if (update.type === "state_update") {
          if (update.error) {
            setErrorMsg(update.error);
            setLoadState("failed");
          } else if (update.questions_ready) {
            fetchResults();
            setLoadState("questions_ready");
          } else {
            setLoadState("analyzing");
          }
        }
        if (update.type === "done" || update.type === "error") {
          fetchResults();
        }
      },
      () => {
        // WS closed — fall back to single poll
        fetchResults();
      }
    );

    return () => {
      if (ws.readyState === WebSocket.OPEN) ws.close();
    };
  }, [sessionId, fetchResults]);

  const handleStartInterview = async () => {
    if (startedRef.current) return;
    startedRef.current = true;
    if (!sessionId || isStarting) return;
    setIsStarting(true);
    try {
      await startInterview(sessionId);
      router.push(`/interview?session_id=${sessionId}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("409")) {
        // Interview already started — redirect anyway
        router.push(`/interview?session_id=${sessionId}`);
        return;
      }
      startedRef.current = false;
      setIsStarting(false);
    }
  };

  if (!sessionId || loadState === "error") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <AlertTriangle size={40} className="text-amber-400" />
        <p className="text-slate-300">{errorMsg ?? "Invalid session"}</p>
        <button className="btn-secondary" onClick={() => router.push("/")}>
          Upload Page Pe Wapis Jao
        </button>
      </div>
    );
  }

  if (loadState === "failed") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <XCircle size={40} className="text-red-400" />
        <p className="text-slate-300">Pipeline failed: {errorMsg}</p>
        <button className="btn-secondary flex items-center gap-2" onClick={fetchResults}>
          <RefreshCw size={16} /> Retry karo
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Pipeline progress tracker */}
      <ProgressTracker state={pipelineState} />

      {/* Loading state */}
      {loadState === "analyzing" && !results?.analysis && (
        <div className="card flex items-center gap-4 py-10 justify-center">
          <Loader2 size={28} className="animate-spin text-indigo-400" />
          <div>
            <p className="text-slate-200 font-medium">AI analyze kar raha hai...</p>
            <p className="text-slate-500 text-sm">CV parse → JD parse → comparison → questions generate</p>
          </div>
        </div>
      )}

      {/* Analysis results */}
      {results?.analysis && (
        <>
          {/* Score + summary row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="flex items-center justify-center">
              <ScoreCard score={results.analysis.match_score} />
            </div>
            <div className="lg:col-span-2 card flex flex-col justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-100 mb-3">Analysis Summary</h2>
                <p className="text-slate-300 text-sm leading-relaxed">{results.analysis.summary}</p>
              </div>
              <div className="flex gap-4 mt-4 text-sm">
                <div className="flex items-center gap-1.5">
                  {results.analysis.experience_match ? (
                    <CheckCircle2 size={16} className="text-emerald-400" />
                  ) : (
                    <XCircle size={16} className="text-red-400" />
                  )}
                  <span className="text-slate-400">Experience Match</span>
                </div>
                <div className="flex items-center gap-1.5">
                  {results.analysis.education_match ? (
                    <CheckCircle2 size={16} className="text-emerald-400" />
                  ) : (
                    <XCircle size={16} className="text-red-400" />
                  )}
                  <span className="text-slate-400">Education Match</span>
                </div>
              </div>
            </div>
          </div>

          {/* Strengths + Gaps */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="card">
              <h3 className="font-semibold text-emerald-400 mb-3 flex items-center gap-2">
                <CheckCircle2 size={18} /> Strengths ({results.analysis.strengths.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {results.analysis.strengths.map((s, i) => (
                  <span
                    key={i}
                    className="bg-emerald-900/40 text-emerald-300 border border-emerald-700/40 text-sm px-3 py-1 rounded-full"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>

            <div className="card">
              <h3 className="font-semibold text-red-400 mb-3 flex items-center gap-2">
                <XCircle size={18} /> Gaps ({results.analysis.gaps.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {results.analysis.gaps.map((g, i) => (
                  <span
                    key={i}
                    className="bg-red-900/40 text-red-300 border border-red-700/40 text-sm px-3 py-1 rounded-full"
                  >
                    {g}
                  </span>
                ))}
                {results.analysis.gaps.length === 0 && (
                  <span className="text-slate-500 text-sm">Koi major gap nahi! 🎉</span>
                )}
              </div>
              {results.analysis.top_missing_skill && (
                <p className="text-slate-500 text-xs mt-3">
                  Most critical gap:{" "}
                  <span className="text-red-300 font-medium">
                    {results.analysis.top_missing_skill}
                  </span>
                </p>
              )}
            </div>
          </div>
        </>
      )}

      {/* Questions */}
      {results?.questions && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-slate-100">
              Interview Questions ({results.questions.total_count})
            </h2>
            <div className="flex gap-2 text-xs">
              {Object.entries(results.questions.difficulty_distribution).map(([d, n]) => (
                <span key={d} className={`badge-${d}`}>
                  {d}: {n}
                </span>
              ))}
            </div>
          </div>
          <QuestionList questions={results.questions} />
        </div>
      )}

      {/* Start Interview CTA */}
      {loadState === "questions_ready" && results?.questions && (
        <div className="card border border-indigo-700/40 bg-indigo-950/20 text-center py-8">
          <Mic size={36} className="mx-auto mb-4 text-indigo-400" />
          <h3 className="text-xl font-bold text-slate-100 mb-2">
            Questions Ready — Interview Shuru Karo!
          </h3>
          <p className="text-slate-400 text-sm mb-6 max-w-md mx-auto">
            AI tumse in questions pe real-time voice interview lega.
            Mic ready raho — interview {results.questions.total_count} questions ka hoga.
          </p>
          <button
            className="btn-primary flex items-center gap-2 mx-auto text-base px-8"
            onClick={handleStartInterview}
            disabled={isStarting}
          >
            {isStarting ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Mic size={18} />
            )}
            <span>{isStarting ? "Starting..." : "Voice Interview Start Karo"}</span>
          </button>
        </div>
      )}

      {/* Analyzing — questions generating */}
      {loadState === "analyzing" && results?.analysis && !results?.questions && (
        <div className="card flex items-center gap-4">
          <Loader2 size={24} className="animate-spin text-indigo-400 shrink-0" />
          <div>
            <p className="text-slate-200 font-medium">Questions generate ho rahe hain...</p>
            <p className="text-slate-500 text-sm">Gaps aur strengths ke basis pe personalized questions ban rahe hain</p>
          </div>
        </div>
      )}
    </div>
  );
}
