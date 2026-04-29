"use client";

// CV + JD upload page — user yahan se pipeline shuru karta hai.
// Submit ke baad session_id milta hai aur /results page pe redirect hota hai.

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Briefcase, Loader2, ArrowRight, Sparkles } from "lucide-react";
import { analyzeCV } from "@/lib/api";

const PLACEHOLDER_CV = `John Doe
john@example.com | linkedin.com/in/johndoe

EXPERIENCE
Senior Software Engineer — Acme Corp (2021-2024)
- Built REST APIs with FastAPI and Python
- Deployed on AWS EC2 with Docker

SKILLS
Python, FastAPI, Docker, PostgreSQL, Redis, React

EDUCATION
B.S. Computer Science — State University (2019)`;

const PLACEHOLDER_JD = `Senior Backend Engineer — TechStartup

We're looking for a backend engineer to join our infra team.

Requirements:
- 3+ years Python experience (FastAPI/Django)
- Kubernetes and AWS experience
- Strong database design skills (PostgreSQL)
- Experience with CI/CD pipelines
- Terraform or similar IaC tools

Nice to have:
- Go experience
- GraphQL knowledge`;

export default function UploadPage() {
  const router = useRouter();
  const [cvText, setCvText] = useState("");
  const [jdText, setJdText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cvText.trim() || !jdText.trim()) {
      setError("CV aur JD dono fields fill karo.");
      return;
    }
    if (cvText.trim().length < 50) {
      setError("CV text bahut chhota hai — minimum 50 characters.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const sessionId = await analyzeCV(cvText.trim(), jdText.trim());
      router.push(`/results?session_id=${sessionId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis start karne mein error aya.");
      setLoading(false);
    }
  };

  const loadSample = () => {
    setCvText(PLACEHOLDER_CV);
    setJdText(PLACEHOLDER_JD);
  };

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="text-center mb-12 mt-4">
        <div className="inline-flex items-center gap-2 bg-indigo-950/50 border border-indigo-700/40 text-indigo-300 text-sm px-4 py-1.5 rounded-full mb-6">
          <Sparkles size={14} />
          <span>AI-Powered Interview Preparation</span>
        </div>
        <h1 className="text-5xl font-bold text-slate-100 mb-4 leading-tight">
          Apna CV Analyze Karo
          <br />
          <span className="text-indigo-400">Mock Interview Practice Karo</span>
        </h1>
        <p className="text-slate-400 text-lg max-w-xl mx-auto">
          CV + Job Description paste karo. AI score karega, gaps batayega,
          aur personalized voice interview lega.
        </p>
      </div>

      {/* How it works */}
      <div className="grid grid-cols-3 gap-4 mb-10">
        {[
          { step: "01", title: "Upload CV + JD", desc: "Text paste karo" },
          { step: "02", title: "AI Analysis", desc: "Score + gaps + questions" },
          { step: "03", title: "Voice Interview", desc: "Real mock interview" },
        ].map((item) => (
          <div key={item.step} className="card text-center">
            <div className="text-indigo-400 text-xs font-mono mb-2">{item.step}</div>
            <div className="font-semibold text-slate-100 text-sm">{item.title}</div>
            <div className="text-slate-500 text-xs mt-1">{item.desc}</div>
          </div>
        ))}
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* CV */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 bg-indigo-900/60 border border-indigo-700/50 rounded-lg flex items-center justify-center">
                <FileText size={16} className="text-indigo-400" />
              </div>
              <div>
                <div className="font-semibold text-slate-100 text-sm">Your CV / Resume</div>
                <div className="text-slate-500 text-xs">Plain text mein paste karo</div>
              </div>
            </div>
            <textarea
              className="textarea-field h-72"
              placeholder={PLACEHOLDER_CV}
              value={cvText}
              onChange={(e) => setCvText(e.target.value)}
              disabled={loading}
              aria-label="CV text"
            />
            <div className="flex justify-between mt-2">
              <span className="text-slate-600 text-xs">{cvText.length} chars</span>
              {cvText.length < 50 && cvText.length > 0 && (
                <span className="text-red-400 text-xs">Min 50 chars</span>
              )}
            </div>
          </div>

          {/* JD */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 bg-emerald-900/60 border border-emerald-700/50 rounded-lg flex items-center justify-center">
                <Briefcase size={16} className="text-emerald-400" />
              </div>
              <div>
                <div className="font-semibold text-slate-100 text-sm">Job Description</div>
                <div className="text-slate-500 text-xs">JD ka text yahan paste karo</div>
              </div>
            </div>
            <textarea
              className="textarea-field h-72"
              placeholder={PLACEHOLDER_JD}
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              disabled={loading}
              aria-label="Job description text"
            />
            <div className="mt-2">
              <span className="text-slate-600 text-xs">{jdText.length} chars</span>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-900/30 border border-red-700/50 text-red-300 rounded-xl px-4 py-3 mb-5 text-sm">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={loadSample}
            className="btn-secondary text-sm"
            disabled={loading}
          >
            Sample Data Load Karo
          </button>

          <button
            type="submit"
            className="btn-primary flex items-center gap-2 text-base px-8"
            disabled={loading || cvText.length < 50 || jdText.length < 30}
          >
            {loading ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <span>Analyze Karo</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
