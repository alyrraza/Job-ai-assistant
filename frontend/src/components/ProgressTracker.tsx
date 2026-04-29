"use client";

// Pipeline progress tracker — 4 steps dikhata hai: Upload → Analysis → Questions → Interview.
// Current state se active step highlight hoti hai — animated indicator.

import { Check, Loader2 } from "lucide-react";

interface ProgressTrackerProps {
  state: string;
}

const STEPS = [
  {
    id: "upload",
    label: "CV + JD Uploaded",
    states: ["agent1_running", "agent1_done", "agent2_running", "agent2_done", "agent3_ready", "agent3_running", "completed"],
  },
  {
    id: "analysis",
    label: "CV Analysis",
    states: ["agent2_running", "agent1_done", "agent2_done", "agent3_ready", "agent3_running", "completed"],
    runningStates: ["agent1_running"],
  },
  {
    id: "questions",
    label: "Questions Generated",
    states: ["agent2_done", "agent3_ready", "agent3_running", "completed"],
    runningStates: ["agent2_running"],
  },
  {
    id: "interview",
    label: "Voice Interview",
    states: ["completed"],
    runningStates: ["agent3_running"],
  },
];

type StepStatus = "done" | "running" | "pending";

function getStepStatus(step: typeof STEPS[number], state: string): StepStatus {
  if (step.states.includes(state)) return "done";
  if (step.runningStates?.includes(state)) return "running";
  return "pending";
}

export default function ProgressTracker({ state }: ProgressTrackerProps) {
  if (state === "idle") return null;

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        {STEPS.map((step, i) => {
          const status = getStepStatus(step, state);
          return (
            <div key={step.id} className="flex items-center flex-1">
              {/* Step indicator */}
              <div className="flex flex-col items-center gap-1.5 flex-1">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${
                    status === "done"
                      ? "bg-emerald-600 border-emerald-500"
                      : status === "running"
                      ? "bg-indigo-900 border-indigo-400"
                      : "bg-slate-800 border-slate-600"
                  }`}
                >
                  {status === "done" ? (
                    <Check size={14} className="text-white" />
                  ) : status === "running" ? (
                    <Loader2 size={14} className="text-indigo-400 animate-spin" />
                  ) : (
                    <span className="text-slate-600 text-xs font-mono">{i + 1}</span>
                  )}
                </div>
                <span
                  className={`text-xs text-center leading-tight max-w-[80px] ${
                    status === "done"
                      ? "text-emerald-400"
                      : status === "running"
                      ? "text-indigo-300"
                      : "text-slate-600"
                  }`}
                >
                  {step.label}
                </span>
              </div>

              {/* Connector line */}
              {i < STEPS.length - 1 && (
                <div
                  className={`h-0.5 flex-1 mx-2 mb-5 transition-colors duration-300 ${
                    getStepStatus(STEPS[i + 1], state) !== "pending" || status === "done"
                      ? "bg-emerald-700"
                      : "bg-slate-700"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* State label */}
      <div className="mt-2 text-center">
        <span className="text-slate-500 text-xs font-mono">state: {state}</span>
        {state === "failed" && (
          <span className="ml-2 text-red-400 text-xs">Pipeline fail ho gaya</span>
        )}
      </div>
    </div>
  );
}
