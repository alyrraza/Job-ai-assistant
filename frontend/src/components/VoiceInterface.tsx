"use client";

// Voice Interview UI — LiveKit room se connect hota hai.
// RoomAudioRenderer TTS audio play karta hai, mic toggle user ka audio publish karta hai.
// Backend TTS publish karta hai → frontend sunata hai → user bolta hai → backend receive karta hai.

import { useEffect, useState, useRef } from "react";
import { Mic, MicOff, Loader2, CheckCircle2, XCircle, Award, ArrowRight } from "lucide-react";
import { LiveKitRoom, RoomAudioRenderer, useLocalParticipant } from "@livekit/components-react";
import { createWebSocket, getResults } from "@/lib/api";
import type { Questions, InterviewReport, AnswerEval, WsStateUpdate } from "@/lib/api";

interface VoiceInterfaceProps {
  sessionId: string;
  questions: Questions;
  livekitToken: string;
  livekitUrl: string;
  roomName: string;
}

type InterviewPhase = "waiting" | "asking" | "recording" | "evaluating" | "next" | "completed";

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
  livekitUrl,
  roomName,
}: VoiceInterfaceProps) {
  return (
    <LiveKitRoom
      token={livekitToken}
      serverUrl={livekitUrl}
      audio={true}
      video={false}
      connect={true}
    >
      <RoomAudioRenderer />
      <InterviewRoom
        sessionId={sessionId}
        questions={questions}
        roomName={roomName}
      />
    </LiveKitRoom>
  );
}

function InterviewRoom({
  sessionId,
  questions,
  roomName,
}: {
  sessionId: string;
  questions: Questions;
  roomName: string;
}) {
  const allQuestions = [
    ...questions.behavioral,
    ...questions.technical,
    ...questions.role_specific,
  ];

  const { localParticipant } = useLocalParticipant();
  const [micEnabled, setMicEnabled] = useState(false);
  const [phase, setPhase] = useState<InterviewPhase>("asking");
  const [currentQ, setCurrentQ] = useState<CurrentQuestion | null>({
    text: allQuestions[0]?.text ?? "",
    category: allQuestions[0]?.category ?? "",
    difficulty: allQuestions[0]?.difficulty ?? "medium",
    skill_tag: allQuestions[0]?.skill_tag ?? "",
    index: 1,
    total: allQuestions.length,
  });
  const [evaluations, setEvaluations] = useState<AnswerEval[]>([]);
  const [report, setReport] = useState<InterviewReport | null>(null);
  const [wsState, setWsState] = useState<string>("connecting");
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
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

  const toggleMic = async () => {
    if (!localParticipant) return;
    const next = !micEnabled;
    try {
      await localParticipant.setMicrophoneEnabled(next);
      setMicEnabled(next);
      setPhase(next ? "recording" : "asking");
    } catch (err) {
      console.error("[VoiceInterface] Mic toggle failed:", err);
    }
  };

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

      {/* Mic button + status */}
      <div className="card flex flex-col items-center gap-5 py-8">
        <button
          onClick={toggleMic}
          className={`w-20 h-20 rounded-full border-2 flex items-center justify-center transition-all duration-200 focus:outline-none ${
            micEnabled
              ? "bg-red-900/60 border-red-400 animate-pulse hover:bg-red-800/60"
              : "bg-indigo-900/60 border-indigo-500 hover:bg-indigo-800/60"
          }`}
          title={micEnabled ? "Mic band karo" : "Mic shuru karo — jawab do"}
        >
          {micEnabled ? (
            <Mic size={32} className="text-red-400" />
          ) : (
            <MicOff size={32} className="text-indigo-400" />
          )}
        </button>

        <div className="text-center">
          <p className="text-slate-300 text-sm font-medium">
            {micEnabled
              ? "Recording... — jawab dene ke baad mic band karo"
              : "Mic dabao aur apna jawab bolo"}
          </p>
          <p className="text-slate-600 text-xs mt-1 font-mono">
            LiveKit connected • {roomName}
          </p>
        </div>

        {wsState === "agent3_running" && (
          <div className="flex items-center gap-2 text-emerald-400 text-xs">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            AI sun raha hai
          </div>
        )}
      </div>

      {/* Per-question scores so far */}
      {evaluations.length > 0 && (
        <div className="card">
          <h3 className="text-slate-300 font-medium mb-3 text-sm">Completed Answers</h3>
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

function ScorePill({ score }: { score: number }) {
  const color =
    score >= 7
      ? "text-emerald-400 bg-emerald-900/40 border-emerald-700/40"
      : score >= 5
      ? "text-amber-400 bg-amber-900/40 border-amber-700/40"
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
          <div className={`border rounded-xl px-4 py-2 font-bold uppercase text-sm ${recColor}`}>
            {report.recommendation}
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="font-semibold text-slate-200 mb-3">Overall Feedback</h2>
        <p className="text-slate-300 text-sm leading-relaxed">{report.overall_feedback}</p>
      </div>

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
            <p className="text-slate-500 text-sm">Koi major weak area nahi!</p>
          )}
        </div>
      </div>

      {report.top_improvement_tips.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-slate-200 mb-3">Top Improvement Tips</h3>
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
              <p className="text-slate-400 text-xs">{ans.feedback}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="flex gap-3 justify-center pb-4">
        <a href="/" className="btn-secondary flex items-center gap-2">
          <ArrowRight size={16} />
          New Interview
        </a>
        <a href={`/results?session_id=${sessionId}`} className="btn-secondary flex items-center gap-2">
          Results Dobara Dekho
        </a>
      </div>
    </div>
  );
}
