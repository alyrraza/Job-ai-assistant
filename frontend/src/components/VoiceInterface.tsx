"use client";

// Voice Interview UI — current question dikhao, recording status, per-question score.
// Agent 3 background mein chal raha hai, frontend WebSocket se live updates leta hai.
// Final report interview complete hone ke baad yahan show hota hai.

import { useEffect, useState, useRef } from "react";
import { Mic, MicOff, Loader2, CheckCircle2, XCircle, Award, ArrowRight } from "lucide-react";
import { createWebSocket, getResults } from "@/lib/api";
import type { Questions, InterviewReport, AnswerEval, WsStateUpdate } from "@/lib/api";

interface VoiceInterfaceProps {
  sessionId: string;
  questions: Questions;
  livekitToken: string | null;
  roomName: string;
}

type InterviewPhase =
  | "waiting"
  | "asking"
  | "recording"
  | "evaluating"
  | "next"
  | "completed";

interface CurrentQuestion {
  text: string;
  category: string;
  difficulty: string;
  skill_tag: string;
  index: number;
  total: number;
}

export default function VoiceInterface({
  sessionId,
  questions,
  livekitToken,
  roomName,
}: VoiceInterfaceProps) {
  const allQuestions = [
    ...questions.behavioral,
    ...questions.technical,
    ...questions.role_specific,
  ];

  const [phase, setPhase] = useState<InterviewPhase>("waiting");
  const [currentQ, setCurrentQ] = useState<CurrentQuestion | null>(null);
  const [evaluations, setEvaluations] = useState<AnswerEval[]>([]);
  const [report, setReport] = useState<InterviewReport | null>(null);
  const [wsState, setWsState] = useState<string>("connecting");
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Simulate phase transitions driven by WS pipeline updates
    setCurrentQ({
      text: allQuestions[0]?.text ?? "",
      category: allQuestions[0]?.category ?? "",
      difficulty: allQuestions[0]?.difficulty ?? "medium",
      skill_tag: allQuestions[0]?.skill_tag ?? "",
      index: 1,
      total: allQuestions.length,
    });
    setPhase("asking");

    wsRef.current = createWebSocket(
      sessionId,
      (update: WsStateUpdate) => {
        setWsState(update.state);
        if (update.state === "completed") {
          fetchFinalReport();
        }
      },
      () => setWsState("disconnected")
    );

    return () => {
      wsRef.current?.close();
    };
  }, [sessionId]);

  const fetchFinalReport = async () => {
    try {
      const data = await getResults(sessionId);
      if (data.interview_report) {
        setReport(data.interview_report);
        setEvaluations(data.interview_report.answers);
        setPhase("completed");
      }
    } catch (err) {
      console.error("Report fetch failed:", err);
    }
  };

  if (phase === "completed" && report) {
    return <FinalReport report={report} sessionId={sessionId} />;
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Mock Interview</h1>
          <p className="text-slate-500 text-sm">Room: {roomName || "connecting..."}</p>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              wsState === "agent3_running" ? "bg-emerald-400 animate-pulse" : "bg-slate-600"
            }`}
          />
          <span className="text-slate-500 text-xs font-mono">{wsState}</span>
        </div>
      </div>

      {/* Progress bar */}
      {currentQ && (
        <div>
          <div className="flex justify-between text-xs text-slate-500 mb-1.5">
            <span>Question {currentQ.index} of {currentQ.total}</span>
            <span>{Math.round((currentQ.index / currentQ.total) * 100)}%</span>
          </div>
          <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 transition-all duration-500"
              style={{ width: `${(currentQ.index / currentQ.total) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Current question card */}
      {currentQ && (
        <div className="card border border-indigo-700/30 bg-indigo-950/20">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-indigo-400 text-xs font-mono uppercase tracking-wide">
              {currentQ.category.replace("_", " ")}
            </span>
            <span className={`badge-${currentQ.difficulty}`}>{currentQ.difficulty}</span>
            {currentQ.skill_tag && (
              <span className="text-slate-500 text-xs bg-slate-800 px-2 py-0.5 rounded">
                {currentQ.skill_tag}
              </span>
            )}
          </div>
          <p className="text-slate-100 text-lg leading-relaxed">{currentQ.text}</p>
        </div>
      )}

      {/* Recording / Status indicator */}
      <div className="card flex items-center justify-center py-10">
        <div className="flex flex-col items-center gap-4">
          <PhaseIndicator phase={phase} />
          <p className="text-slate-400 text-sm">{PHASE_LABELS[phase]}</p>
          {livekitToken && (
            <p className="text-slate-600 text-xs font-mono">
              LiveKit connected • {roomName}
            </p>
          )}
          {!livekitToken && (
            <p className="text-amber-500 text-xs">
              LiveKit nahi mila — local fallback mode (simulated)
            </p>
          )}
        </div>
      </div>

      {/* Per-question scores so far */}
      {evaluations.length > 0 && (
        <div className="card">
          <h3 className="text-slate-300 font-medium mb-3 text-sm">
            Completed Answers
          </h3>
          <div className="space-y-2">
            {evaluations.map((ev, i) => (
              <div
                key={i}
                className="flex items-center justify-between text-sm py-2 border-b border-slate-700/40 last:border-0"
              >
                <span className="text-slate-400 truncate max-w-[70%]">
                  Q{i + 1}: {ev.question_text.slice(0, 60)}...
                </span>
                <ScorePill score={ev.score} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const PHASE_LABELS: Record<InterviewPhase, string> = {
  waiting: "Interview shuru hone ka intezaar hai...",
  asking: "AI sawal pooch raha hai (TTS)...",
  recording: "Aapka jawab record ho raha hai...",
  evaluating: "AI jawab evaluate kar raha hai...",
  next: "Agla sawal aa raha hai...",
  completed: "Interview complete!",
};

function PhaseIndicator({ phase }: { phase: InterviewPhase }) {
  if (phase === "asking") {
    return (
      <div className="w-16 h-16 bg-indigo-900/60 border-2 border-indigo-500 rounded-full flex items-center justify-center">
        <Mic size={28} className="text-indigo-400" />
      </div>
    );
  }
  if (phase === "recording") {
    return (
      <div className="w-16 h-16 bg-red-900/60 border-2 border-red-400 rounded-full flex items-center justify-center animate-pulse">
        <Mic size={28} className="text-red-400" />
      </div>
    );
  }
  if (phase === "evaluating") {
    return (
      <div className="w-16 h-16 bg-amber-900/40 border-2 border-amber-600 rounded-full flex items-center justify-center">
        <Loader2 size={28} className="text-amber-400 animate-spin" />
      </div>
    );
  }
  if (phase === "waiting") {
    return (
      <div className="w-16 h-16 bg-slate-800 border-2 border-slate-600 rounded-full flex items-center justify-center">
        <MicOff size={28} className="text-slate-500" />
      </div>
    );
  }
  return (
    <div className="w-16 h-16 bg-emerald-900/60 border-2 border-emerald-500 rounded-full flex items-center justify-center">
      <CheckCircle2 size={28} className="text-emerald-400" />
    </div>
  );
}

function ScorePill({ score }: { score: number }) {
  const color =
    score >= 7 ? "text-emerald-400 bg-emerald-900/40 border-emerald-700/40"
    : score >= 5 ? "text-amber-400 bg-amber-900/40 border-amber-700/40"
    : "text-red-400 bg-red-900/40 border-red-700/40";
  return (
    <span className={`text-xs font-bold border px-2 py-0.5 rounded-full ${color}`}>
      {score}/10
    </span>
  );
}

// ---------------------------------------------------------------------------
// Final Report screen
// ---------------------------------------------------------------------------

function FinalReport({
  report,
  sessionId,
}: {
  report: InterviewReport;
  sessionId: string;
}) {
  const recColor = {
    hire: "text-emerald-400 bg-emerald-900/30 border-emerald-600",
    consider: "text-amber-400 bg-amber-900/30 border-amber-600",
    reject: "text-red-400 bg-red-900/30 border-red-600",
  }[report.recommendation];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Hero */}
      <div className="card text-center py-10 border border-indigo-700/30">
        <Award size={48} className="mx-auto mb-4 text-indigo-400" />
        <h1 className="text-3xl font-bold text-slate-100 mb-2">Interview Complete!</h1>
        <div className="flex items-center justify-center gap-4 mt-4">
          <div className="text-center">
            <div className="text-4xl font-bold text-indigo-400">{report.avg_score}</div>
            <div className="text-slate-500 text-sm">Avg Score / 10</div>
          </div>
          <div className="w-px h-12 bg-slate-700" />
          <div className="text-center">
            <div className="text-4xl font-bold text-slate-200">{report.total_questions}</div>
            <div className="text-slate-500 text-sm">Questions</div>
          </div>
          <div className="w-px h-12 bg-slate-700" />
          <div
            className={`border rounded-xl px-4 py-2 font-bold uppercase text-sm ${recColor}`}
          >
            {report.recommendation}
          </div>
        </div>
      </div>

      {/* Overall feedback */}
      <div className="card">
        <h2 className="font-semibold text-slate-200 mb-3">Overall Feedback</h2>
        <p className="text-slate-300 text-sm leading-relaxed">{report.overall_feedback}</p>
      </div>

      {/* Strong + Weak areas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-emerald-400 font-semibold mb-3 flex items-center gap-2">
            <CheckCircle2 size={16} /> Strong Areas
          </h3>
          {report.strong_areas.length ? (
            <ul className="space-y-1.5">
              {report.strong_areas.map((a, i) => (
                <li key={i} className="text-slate-300 text-sm flex items-start gap-2">
                  <span className="text-emerald-500 mt-0.5">•</span> {a}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500 text-sm">Koi strong area identified nahi hua</p>
          )}
        </div>

        <div className="card">
          <h3 className="text-red-400 font-semibold mb-3 flex items-center gap-2">
            <XCircle size={16} /> Weak Areas
          </h3>
          {report.weak_areas.length ? (
            <ul className="space-y-1.5">
              {report.weak_areas.map((a, i) => (
                <li key={i} className="text-slate-300 text-sm flex items-start gap-2">
                  <span className="text-red-500 mt-0.5">•</span> {a}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500 text-sm">Koi major weak area nahi! 🎉</p>
          )}
        </div>
      </div>

      {/* Improvement tips */}
      {report.top_improvement_tips.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-slate-200 mb-3">
            Top Improvement Tips
          </h3>
          <ol className="space-y-2">
            {report.top_improvement_tips.map((tip, i) => (
              <li key={i} className="flex items-start gap-3 text-sm text-slate-300">
                <span className="bg-indigo-900/50 text-indigo-300 w-5 h-5 rounded flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                  {i + 1}
                </span>
                {tip}
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Per-question breakdown */}
      <div className="card">
        <h3 className="font-semibold text-slate-200 mb-4">Per-Question Scores</h3>
        <div className="space-y-3">
          {report.answers.map((ans, i) => (
            <div key={i} className="bg-slate-900/50 rounded-xl p-4">
              <div className="flex items-start justify-between gap-3 mb-2">
                <p className="text-slate-200 text-sm leading-relaxed">
                  Q{i + 1}: {ans.question_text}
                </p>
                <ScorePill score={ans.score} />
              </div>
              <p className="text-slate-400 text-xs ml-0">{ans.feedback}</p>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div className="flex gap-3 justify-center pb-4">
        <a href="/" className="btn-secondary flex items-center gap-2">
          <ArrowRight size={16} />
          New Interview
        </a>
        <a
          href={`/results?session_id=${sessionId}`}
          className="btn-secondary flex items-center gap-2"
        >
          Results Dobara Dekho
        </a>
      </div>
    </div>
  );
}
