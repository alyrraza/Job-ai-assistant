import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CV Interview Coach",
  description: "AI-powered mock interview: upload CV + JD → get score → practice voice interview",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-900 text-slate-50">
        <nav className="border-b border-slate-800 px-6 py-4">
          <div className="max-w-6xl mx-auto flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
              CV
            </div>
            <span className="font-semibold text-slate-100">Interview Coach</span>
            <span className="ml-2 text-xs bg-indigo-900/50 text-indigo-300 border border-indigo-700/50 px-2 py-0.5 rounded-full">
              AI-Powered
            </span>
          </div>
        </nav>
        <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
