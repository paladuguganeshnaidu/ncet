# NCET VerifyFlow — NVIDIA AI Document Assurance Plan

Status: staged implementation in draft PR #1 (NVIDIA provider, relative checklist weights, bounded reference comparison, descriptive document metrics, evidence-rich HOD report, explicit HOD override, and approved-only oversight task access). Larger security and scalability items remain planned. This document distinguishes features already in the repository from work not yet shipped. Review it with NCET leadership and the privacy/security team before using real institutional data.

## 1. Executive goal

HODs provide reference documents, task instructions and a versioned acceptance checklist. Staff upload completed documents. The platform extracts text and layout, runs deterministic checks, asks an authorized NVIDIA NIM model for evidence-linked semantic feedback, and creates an auditable report. The HOD makes the final approval or correction decision. AI recommendations are never treated as proof of misconduct or authorship.

## 2. Architecture observed in the repository

| Layer | Current implementation | Planned extension |
| --- | --- | --- |
| Frontend | Vanilla HTML/CSS/JS under `static/`; `/app` and `/tasks` workspaces | Single cohesive review UX, side-by-side reference comparison, evidence highlight and rubric editor |
| API / identity | Python 3.13 + FastAPI, Argon2id, CSRF, HttpOnly sessions, department/role checks | MFA/SSO, approval delegation and explicit override reasons |
| HOD workflow | `app/taskflow.py` reference batches (1–50 PDFs), assignments, weighted task checklists and templates, deadlines, auditable approval overrides | Instruction anchors, multi-document submission bundles |
| Staff submission | PDF task submissions with durable revisions; separate general-document upload supports PDF/DOCX/TXT/images | Multiple required deliverables per task, progress, change summaries, provenance evidence |
| Extraction | PyMuPDF, python-docx, Tesseract OCR; descriptive words, citation markers, bounded 5-word reference overlap (`app/document_intelligence.py`) | Table/figure extraction, page-region coordinates, DOCX rendering comparison |
| AI integration | `app/ai_gateway.py`, semantic review and rule drafting | NVIDIA NIM first; per-model capabilities, token budgets, retries/usage monitoring |
| Data | PostgreSQL, SQLAlchemy, Alembic; private binary storage and versioned rule policies | Review rubric snapshots, evidence spans, cost records, appeal history |
| Worker | Durable PostgreSQL polling jobs with timeout recovery | Idempotent leases, dead-letter queue, retries, resource budgets |
| Delivery | Docker, Compose + ClamAV, single-service Render pilot, CI/security workflows | Always-on isolated worker, private scanner, backups/alerts, staged release |

### End-to-end pipeline

1. HOD uploads an approved reference PDF and sets task instructions, deadline, required sections, format and evidence requirements.
2. Reference analysis may propose rules, but HOD confirms every rule before assignment. Record the exact rule/template version on each task.
3. Staff downloads the reference and uploads the completed PDF. Upload gates check role, department, file signature, size and malware scan where enabled.
4. Worker extracts page text, OCR confidence notes, observed page dimensions/fonts and structural cues.
5. A deterministic engine verifies literal headings, phrases, page limits and word limits. Unverifiable formatting, dates or signatures get 'uncertain'.
6. NVIDIA NIM reviews qualitative requirements. Its returned rule IDs, statuses, confidence and short verbatim quotations are validated locally. Missing or invented evidence becomes 'uncertain'.
7. Report dialog shows pass/issue/uncertain, available page/section, direct quotation, correction advice, weighted rubric coverage, descriptive document metrics, limited reference overlap and model provenance.
8. HOD examines the source, confirms/overrides advisory findings and approves or requests correction. Every revision and final decision is audit logged.
9. Principal/IQAC task list and reference downloads are restricted to approved tasks; separate oversight summaries remain aggregate.

### State handling

`queued → verifying → awaiting_hod / manual_review / correction_required → approved / correction_required → resubmission`.

Existing task code may suggest correction on confident failures, but the HOD can inspect and override it. Target policy: no automatic disciplinary conclusion or publication; the HOD remains accountable for final acceptance. Model timeout, bad JSON, unreadable OCR, missing rules or unsupported claims must not become success.

## 3. What to measure — truthful evaluation rubric

Recommended initial rubric, subject to HOD approval, with a score only when sufficient evidence exists:

| Dimension | Example checks | Weight |
| --- | --- | ---: |
| Task completeness | Every requested deliverable, heading and required detail present | 25 |
| Structure / ordering | Correct template, sections and required sequence | 20 |
| Evidence and correctness | Claims supported by supplied material, internal consistency, factual checks against permitted references | 20 |
| Formatting | Page constraints, tables, margins, fonts, metadata; unclear checks manual | 10 |
| References and citations | Required citations exist, match supplied sources and are appropriately attributed | 10 |
| Cross-section consistency | Dates, totals, entities, figures and conclusions agree across sections | 10 |
| Language clarity | Professional writing without altering meaning | 5 |
| **Total** | **Weighted quality/adherence, not authorship** | **100** |

Each dimension should expose `status`, `weight`, `evidence_spans`, `rule_version`, `confidence_band`, `human_override`, and `remediation`. Confidence is an uncertainty indicator, not a percent probability that an employee did honest work. Do not rank staff character from this score.

### Authorship and originality: what is and is not knowable

No current LLM detector can establish from document text alone that work was entirely human-written. A polished, repetitive or unusual writing style is not proof of AI use, plagiarism or misconduct. Reports must say **'Authorship not determinable from document alone'**. If the institution needs authenticity review, request consent-based process evidence: drafts, document revision history, source notes, assignment-specific data, interviews, citations, and optional version snapshots. A human HOD evaluates those signals and any appeal. Never automatically accuse, penalize, or reject solely on a probability-of-AI score.

## 4. NVIDIA integration contract

- Server-only base URL: `https://integrate.api.nvidia.com/v1`; POST `/chat/completions`.
- `NVIDIA_API_KEY` is read from private environment or encrypted `integration_settings.nvidia_key`. Neither a frontend page nor logs receive the raw key.
- `NVIDIA_MODEL` chooses an available NVIDIA Catalog model; current starter default is `meta/llama-3.1-70b-instruct` (re-check availability and limits before deploying).
- NVIDIA is preferred when present. Existing DeepSeek/OpenRouter configuration is a compatibility fallback only if NVIDIA is absent; model errors never silently route a document to another provider.
- Document text remains user-role data, not system instructions; the verifier asks for exact quotations and validates source overlap before accepting an AI pass/issue.
- Do not assume a model supports provider-enforced JSON-schema mode. Parse response JSON locally, reject extra/invalid rule IDs and malformed types, and flag incomplete items for manual review.
- Bound pages, OCR work, input characters, output tokens, retries and request latency. For large documents, add chunked page-indexed review, evidence reconciliation and a final cross-chunk pass before raising limits.
- Current code sends extracted text to NVIDIA when configured. Privacy review, provider retention terms, institutional authorization and a data-processing agreement (as applicable) are release gates.

## 5. High-priority gaps and security controls

| Priority | Finding | Recommended gate |
| --- | --- | --- |
| P0 | Render Blueprint has `SCAN_MODE=off`; file headers are not malware scanning | Add a private ClamAV/AV service or block untrusted real uploads; fail closed |
| P0 | 2026-10-21 repository audit reported a public database allowlist and an expiring Free Postgres plan | Reverify current settings and backups; restrict network; perform restore drill |
| P0 | 2026-10-21 audit reported Render connected to `hackerncet/tuxnestsite` and custom-domain TLS failure | Verify current source/certificate, reconnect if still wrong, stage smoke tests |
| P0 | Generative AI can invent evidence or misstate confidence | Require verbatim source evidence for pass/issue; route unsupported claims to HOD |
| P1 | Two reviewer paths historically had divergent AI transport/validation | Centralize provider selection and JSON transport; share evidence contract and tests |
| P1 | Model/provider data handling, consent and retention unspecified for live student/staff records | Obtain college approval, restrict sensitive fields, set a retention/deletion policy |
| P1 | Long documents may exceed model context; OCR may be partial | Strict per-model budgets and page-indexed chunking; surface incomplete coverage |
| P1 | Reference PDF similarity can be mistaken for copied work | Compare only task-specific expected/forbidden overlap; never call template overlap plagiarism |
| P2 | Queue monitors/worker isolation not sufficient for campus scale | Separate worker, lease renewal, DLQ, retry caps, queue-age alerts, cost budgets |

Current security strengths observed: salted Argon2id, CSRF enforcement, authenticated download endpoints, role/department filters, immutable policy versions, encrypted integration settings, restrained CSP, upload signatures and size limits, and a ClamAV option on Compose. These controls require live verification, not just code inspection.

## 6. Future data/API design

Proposed migrations (not present yet):

- `task_rubric_versions(task_id, version, rules_json, weights_json, created_by, created_at)` with immutable published snapshots.
- `analysis_runs(id, submission_id, provider, model, source_sha256, rule_version, state, started_at, finished_at, input_tokens, output_tokens, error_code)`.
- `analysis_findings(id, run_id, rule_id, status, score, confidence_band, page, quote, quote_start, quote_end, recommendation)`.
- `review_overrides(id, finding_id, hod_id, old_status, new_status, reason, created_at)`.
- `submission_provenance(id, submission_id, kind, private_storage_key, consent_status, recorded_at)` with access controls and short retention.

Potential APIs (not implemented): `POST /api/tasks/{id}/rubric/preview`, `POST /api/tasks/{id}/submission-bundles`, `GET /api/tasks/{id}/analysis/{run_id}`, `POST /api/tasks/{id}/findings/{finding_id}/override`, `GET /api/admin/ai/usage`. All writes require CSRF and department/role enforcement. Bundle file retrieval must stay behind authenticated permission checks.

## 7. Delivery phases and acceptance gates

### Phase A — NVIDIA foundation (first review PR)

- NVIDIA provider selection, server-encrypted key management, admin UI, environment mapping, README and regression tests.
- Reuse shared JSON transport for general-document and assigned-task review; safely downgrade ungrounded AI citations.
- Build report truthfully states authorship cannot be determined from text alone.
- Required checks: Python suite, frontend syntax, migration drift, CI security workflow, fake NVIDIA response and malformed-response cases.

### Phase B — Rich HOD rubric and reference matching

- Version weighted rubrics and match every finding to a reference or submitted document page/section.
- Let HOD designate required evidence, exact structure and allowed template overlap. Add missing-section and cross-field checks.
- Acceptance: deterministic failing templates remain reproducible; AI cannot override a proven mandatory failure; all rule revisions are visible.

### Phase C — Deep document intelligence

- Multi-file staff deliverables, extracted tables/charts, section-aware chunking, citations, reference-to-submission comparison and targeted revisions.
- Acceptance: reports show exact page quotes, coverage percentage, OCR uncertainty, each missing requirement and an actionable correction.

### Phase D — Production safety and operations

- Signed access policies, external processing authorization, scanner deployment, private DB, disaster recovery, audit retention, token/cost dashboards, service health and staging smoke tests.
- Acceptance: role separation, malware block, safe timeout, no secret exposure, backup restoration, correct Render source, valid TLS, load-test targets.

### Phase E — Provenance / fairness safeguards

- Optional staff-supplied draft history and citation/source evidence, with consent, appeal path, transparent HOD review and privacy deletion.
- Acceptance: no automated human-authorship percentage or disciplinary action; clear limits and explainable human decisions.

## 8. Operational readiness checklist

- [ ] Confirm the active deployment/repository, private PostgreSQL access and valid TLS.
- [ ] Provide a real NVIDIA key only via server secrets or the authenticated admin UI; never commit it.
- [ ] Confirm the selected NVIDIA model has adequate context, token limits, regional/privacy terms and quota.
- [ ] Approve external document text processing with institutional stakeholders.
- [ ] Enable and verify fail-closed malware scanning before public/untrusted uploads.
- [ ] Run migrations/tests, stage role-based HOD → staff → AI → HOD acceptance, then deploy separately.
- [ ] Inspect example reports for invented quotations, partial OCR, missing mandatory items and unsupported authorship claims.
- [ ] Define retention, deletion, backups, monitoring, escalation and an appeals process.

## 9. Test scenarios

Use only synthetic non-confidential documents in early tests. Include a correctly structured submission, missing section, truncated PDF, scanned/handwritten scan, duplicate pages, wrong dates, contradictory figures, hallucinated AI quote, malicious prompt injection in a PDF, a large document, provider timeout/429/5xx, malformed JSON, attempted cross-department download, fake file extensions, ClamAV offline, and simultaneous resubmission/HOD review. Verify 'manual_review' safety where extraction or model evidence is incomplete.

## 10. References

- NVIDIA NIM Chat Completions API: https://docs.api.nvidia.com/nim/reference/meta-llama-3_1-70b-infer
- NVIDIA NIM API architecture: https://docs.nvidia.com/nim/large-language-models/latest/api-reference.html
- Existing code: `app/ai_gateway.py`, `app/verification.py`, `app/taskflow.py`, `app/reference_rules.py`, `app/storage.py`, `app/main.py`, `static/app.js`, `static/tasks.js`, `render.yaml`, `compose.yaml`.
- Prior source/deployment snapshot: `docs/PRODUCTION_READINESS_AUDIT_2026-10-21.md`. Historical live-state claims in that audit must be freshly verified.


## 6. Implemented review enhancements in the draft PR

- Relative rule importance: HOD enters a weight from 1 to 100 for each checklist rule. Total weights are relative, not required to sum to 100. Legacy stored rules default to weight 1. Required failures still block an automated positive recommendation; weighted scores only appear when all rules were assessed and no confidence/OCR uncertainty remains.
- Deterministic word limits: `min_words` and `max_words` work alongside existing heading, phrase and page checks. Scanned or OCR-limited documents with a detected word-count violation are marked uncertain, not declared noncompliant.
- Reference comparison: both PDFs are extracted; the AI receives a short, bounded page-labelled reference excerpt and the HOD's original instructions. The report records a SHA-256 hash of the reference and limited shared 5-word passages. Text reuse in a supplied template is expected; this percentage is **never a plagiarism probability or misconduct finding**.
- Document signals: extracted page count, word count, citation markers and extraction limitations appear in the review dialog. Citation markers are a rough descriptive count; they do not establish attribution quality or source authenticity.
- Human decision: the HOD can explicitly approve an automated correction suggestion with a logged explanation or request changes. The system cannot verify whether the HOD genuinely read the document.
- Oversight: Principal and IQAC no longer see unapproved task details or download reference PDFs via the task endpoints. Their aggregate insights remain available.

**Not yet implemented:** reliable plagiarism checking against licensed corpora; table/figure structural alignment; citation-resolution services; opt-in revision-history provenance; secure malware scanning on Render; isolated workers/queues, multi-document uploads, side-by-side PDF annotations, data retention automation, enterprise SSO/MFA, performance/load testing, and a live NVIDIA integration test with approved institutional content. Treat these as independent milestones with privacy, source-grounding and release tests.

The manuscript cannot prove an author is human. This product must make no authorship percentage or punitive verdict.
