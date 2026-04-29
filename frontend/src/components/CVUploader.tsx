"use client";

// Reusable CV/JD textarea with character count and validation feedback.
// page.tsx mein use hota hai — standalone component taake reuse ho sake.

import { type ChangeEvent } from "react";
import type { LucideIcon } from "lucide-react";

interface CVUploaderProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  minChars?: number;
  icon: LucideIcon;
  iconColor: string;
  disabled?: boolean;
  rows?: number;
}

export default function CVUploader({
  label,
  value,
  onChange,
  placeholder = "",
  minChars = 50,
  icon: Icon,
  iconColor,
  disabled = false,
  rows = 14,
}: CVUploaderProps) {
  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
  };

  const tooShort = value.length > 0 && value.length < minChars;
  const valid = value.trim().length >= minChars;

  return (
    <div className="flex flex-col gap-2">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <div className={`w-8 h-8 rounded-lg border flex items-center justify-center ${iconColor}`}>
          <Icon size={16} />
        </div>
        <span className="font-semibold text-slate-100 text-sm">{label}</span>
        {valid && (
          <span className="ml-auto text-emerald-400 text-xs">✓ Ready</span>
        )}
      </div>

      {/* Textarea */}
      <textarea
        className={`textarea-field transition-colors duration-150 ${
          tooShort ? "border-red-600/60 focus:ring-red-500" : ""
        }`}
        style={{ minHeight: `${rows * 1.5}rem` }}
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        disabled={disabled}
        aria-label={label}
        aria-invalid={tooShort}
      />

      {/* Footer */}
      <div className="flex justify-between items-center">
        <span
          className={`text-xs ${
            tooShort ? "text-red-400" : "text-slate-600"
          }`}
        >
          {value.length} chars
          {tooShort && ` — min ${minChars} required`}
        </span>
        {value.length > 0 && (
          <button
            type="button"
            className="text-slate-600 hover:text-slate-400 text-xs transition-colors"
            onClick={() => onChange("")}
            disabled={disabled}
          >
            Clear
          </button>
        )}
      </div>
    </div>
  );
}
