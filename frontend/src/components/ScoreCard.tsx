"use client";

// Circular progress card — match score 0-100 dikhata hai.
// Green >70, yellow 40-70, red <40. SVG stroke-dashoffset animation hai.

interface ScoreCardProps {
  score: number;
  size?: number;
}

export default function ScoreCard({ score, size = 160 }: ScoreCardProps) {
  const clampedScore = Math.max(0, Math.min(100, score));
  const radius = (size - 24) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (clampedScore / 100) * circumference;

  const { color, label, bg } = getScoreStyle(clampedScore);

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative" style={{ width: size, height: size }}>
        {/* Background ring */}
        <svg width={size} height={size} className="rotate-[-90deg]">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="rgba(100,116,139,0.2)"
            strokeWidth={12}
          />
          {/* Score arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={12}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            style={{ transition: "stroke-dashoffset 1s ease-in-out" }}
          />
        </svg>

        {/* Score text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="font-bold leading-none"
            style={{ fontSize: size * 0.28, color }}
          >
            {clampedScore}
          </span>
          <span className="text-slate-500 text-xs mt-1">/ 100</span>
        </div>
      </div>

      {/* Label badge */}
      <div
        className="text-xs font-semibold px-3 py-1 rounded-full border"
        style={{ color, borderColor: color, backgroundColor: bg }}
      >
        {label}
      </div>
      <p className="text-slate-400 text-xs text-center">CV-JD Match Score</p>
    </div>
  );
}

function getScoreStyle(score: number): {
  color: string;
  label: string;
  bg: string;
} {
  if (score >= 70) {
    return {
      color: "#34d399",          // emerald-400
      label: "Strong Match",
      bg: "rgba(6,78,59,0.3)",
    };
  }
  if (score >= 40) {
    return {
      color: "#fbbf24",          // amber-400
      label: "Partial Match",
      bg: "rgba(92,45,5,0.3)",
    };
  }
  return {
    color: "#f87171",            // red-400
    label: "Weak Match",
    bg: "rgba(69,10,10,0.3)",
  };
}
