# Test Results — CV Interview Coach

**Timestamp:** 2026-04-29 06:09:51
**Python:** 3.11.4

---

## Results

| # | Test | Status | Error |
|---|------|--------|-------|
| 01 | T01 — Config loads Settings object | ✅ PASS |  |
| 02 | T02 — GROQ_API_KEY present in .env | ✅ PASS |  |
| 03 | T03 — ChromaDB connects and creates collections | ✅ PASS |  |
| 04 | T04 — SQLite database initializes | ✅ PASS |  |
| 05 | T05 — MLflow tracking URI configured | ✅ PASS |  |
| 06 | T06 — BaseAgent is abstract (cannot instantiate directly) | ✅ PASS |  |
| 07 | T07 — CVAnalyzerAgent instantiates | ✅ PASS |  |
| 08 | T08 — CV validator rejects empty output | ✅ PASS |  |
| 09 | T09 — CV validator accepts valid schema | ✅ PASS |  |
| 10 | T10 — RAG VectorStore creates both collections | ✅ PASS |  |
| 11 | T11 — Retriever returns list type (empty DB ok) | ✅ PASS |  |
| 12 | T12 — QuestionGeneratorAgent instantiates | ✅ PASS |  |
| 13 | T13 — Question validator rejects < 9 questions | ✅ PASS |  |
| 14 | T14 — Question validator accepts valid 3+4+2 output | ✅ PASS |  |
| 15 | T15 — Supervisor /health endpoint returns 200 | ✅ PASS |  |
| 16 | T16 — Supervisor /dispatch accepts CV+JD payload | ✅ PASS |  |
| 17 | T17 — VoiceInterviewAgent instantiates | ✅ PASS |  |
| 18 | T18 — AnswerEval validator rejects empty input | ✅ PASS |  |
| 19 | T19 — SessionReport avg_score auto-computed by model_validator | ✅ PASS |  |
| 20 | T20 — Router build_agent returns correct types for all three agents | ✅ PASS |  |

---

## Summary

- **Passed:** 20 / 20
- **Failed:** 0 / 20
- **Pass rate:** 100%

---

## Verdict

✅ READY FOR DEMO