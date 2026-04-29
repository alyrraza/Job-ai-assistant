"use client";

// Interview questions ko category-wise accordion mein dikhata hai.
// Difficulty badges aur skill tags ke saath — collapsible per category.

import { useState } from "react";
import { ChevronDown, ChevronRight, Brain, Users, Target } from "lucide-react";
import type { Questions, QuestionItem } from "@/lib/api";

interface QuestionListProps {
  questions: Questions;
}

const CATEGORY_META = {
  behavioral: {
    label: "Behavioral",
    icon: Users,
    color: "text-purple-400",
    bg: "bg-purple-900/20 border-purple-700/30",
  },
  technical: {
    label: "Technical",
    icon: Brain,
    color: "text-blue-400",
    bg: "bg-blue-900/20 border-blue-700/30",
  },
  role_specific: {
    label: "Role-Specific",
    icon: Target,
    color: "text-orange-400",
    bg: "bg-orange-900/20 border-orange-700/30",
  },
} as const;

export default function QuestionList({ questions }: QuestionListProps) {
  const [open, setOpen] = useState<Record<string, boolean>>({
    behavioral: true,
    technical: false,
    role_specific: false,
  });

  const toggle = (cat: string) =>
    setOpen((prev) => ({ ...prev, [cat]: !prev[cat] }));

  const categories: Array<{ key: keyof typeof CATEGORY_META; items: QuestionItem[] }> = [
    { key: "behavioral", items: questions.behavioral },
    { key: "technical", items: questions.technical },
    { key: "role_specific", items: questions.role_specific },
  ];

  return (
    <div className="space-y-3">
      {categories.map(({ key, items }) => {
        const meta = CATEGORY_META[key];
        const Icon = meta.icon;
        const isOpen = open[key];

        return (
          <div key={key} className={`card border ${meta.bg}`}>
            {/* Header */}
            <button
              className="w-full flex items-center justify-between"
              onClick={() => toggle(key)}
              aria-expanded={isOpen}
            >
              <div className="flex items-center gap-3">
                <Icon size={18} className={meta.color} />
                <span className={`font-semibold ${meta.color}`}>{meta.label}</span>
                <span className="text-slate-500 text-sm">({items.length} questions)</span>
              </div>
              {isOpen ? (
                <ChevronDown size={18} className="text-slate-400" />
              ) : (
                <ChevronRight size={18} className="text-slate-400" />
              )}
            </button>

            {/* Questions */}
            {isOpen && (
              <div className="mt-4 space-y-3">
                {items.map((q, i) => (
                  <QuestionCard key={i} question={q} index={i + 1} />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function QuestionCard({ question, index }: { question: QuestionItem; index: number }) {
  const [showFollowUp, setShowFollowUp] = useState(false);

  return (
    <div className="bg-slate-900/60 border border-slate-700/40 rounded-xl p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1">
          <span className="text-slate-600 text-sm font-mono mt-0.5 w-5 shrink-0">
            {index}.
          </span>
          <p className="text-slate-200 text-sm leading-relaxed">{question.text}</p>
        </div>
        <div className="flex gap-1.5 shrink-0">
          <span className={`badge-${question.difficulty}`}>{question.difficulty}</span>
        </div>
      </div>

      {question.skill_tag && (
        <div className="mt-2 ml-8 flex items-center gap-2">
          <span className="text-slate-600 text-xs">Skill:</span>
          <span className="text-slate-400 text-xs bg-slate-800 px-2 py-0.5 rounded">
            {question.skill_tag}
          </span>
        </div>
      )}

      {question.follow_up && (
        <div className="mt-2 ml-8">
          <button
            className="text-slate-500 hover:text-slate-400 text-xs transition-colors"
            onClick={() => setShowFollowUp(!showFollowUp)}
          >
            {showFollowUp ? "▲ Follow-up chhupao" : "▼ Follow-up dekho"}
          </button>
          {showFollowUp && (
            <p className="text-slate-400 text-xs mt-1.5 italic border-l-2 border-slate-600 pl-3">
              {question.follow_up}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
