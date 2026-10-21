# NCET VerifyFlow product roadmap

This roadmap reflects the current repository, with priority on a reliable HOD document pipeline, branch-specific work visibility, and useful student self-service. It keeps the existing NCET theme and makes AI an optional later addition. None of the future AI items assume a provider key is configured.

Features marked implemented are present in this worktree. The local non-AI integration suite, migrations, security scans and browser workflows passed on 2026-10-21. GitHub `main` is now writable and contains the reviewed source; Render still points at the former repository, so these changes are not live yet.

## Current capabilities found in the code

- **Implemented:** HOD approval and correction decisions use an accessible in-page review form with a recorded note, instead of browser popups. Workflow messages describe optional automated checks and the human fallback accurately when AI is not configured.
- **Implemented and API/browser-tested:** HODs can assign a mixed PDF batch with one shared checklist or a separate validated checklist per file. The API requires an exact checklist for each selected PDF, caps rule counts, and saves each approved checklist with its task.
- Department HOD task queue with PDF batches, assignment, deadlines, holds, notifications, staff workload, activity history, approval trends, and human decisions.
- Reusable HOD checklists stored per department, with immutable versions, version selection, archive controls, and task-level rule snapshots. This works without an AI key.
- Deterministic document inspection plus an asynchronous verification worker. When no AI provider is available, submitted work goes to human review.
- Separate student request/complaint desk with private case messages, status transitions, branch scope, filters, pagination, and student notifications.
- Student portal with profile, requests, replies, and portfolio areas. Request status cards filter the private queue; request cards summarize the next step and latest HOD response.
- Students can print/save a private request receipt and reopen a resolved request by replying within 14 days of its latest update. Closed cases remain immutable.
- All-departments roster no longer labels a missing branch as Computer Applications; missing branch data is called out and must be selected during admin edits.
- The administrator can import students for active academic departments from CSV/XLSX; each student's department code is stored on the user account and displayed through the current department catalog.
- XLSX imports cap the compressed upload and expanded archive, reject macros/encryption, require core workbook entries, and require openpyxl's `defusedxml` parser protection.
- Department-bound HOD/staff can enroll, import, list, and edit students only within their own active branch; administrators retain cross-branch management. The existing BCA-named URL and profile table are compatibility names, not a BCA-only data boundary.
- **Implemented:** The current 1,000-row roster batches branch-label resolution into one catalog lookup rather than issuing a query for every displayed student. Server-side pagination and complete roster export remain planned for larger institutions.
- **Implemented and locally tested:** Principal oversight reports institution-wide aggregate student-request and project counts by department. Regression coverage confirms that the response omits request bodies, references and student identities. Principals still have detailed access to the project board; an aggregate-only access policy remains open for review.
- Account creation now reads the active academic department catalog, requires an explicit selection, and the server rejects unknown or inactive branches. HOD-created staff stay bound to the HOD's own department.
- Student case access and HOD notifications resolve a branch's stable code and current name together, so newly configured branches route to the right HOD. Missing student branches display as unset instead of defaulting to Computer Applications.
- Renaming a non-BCA department now carries its HOD/staff accounts, documents, rulebooks, and task queues to the new display name in one transaction; stable student/case codes are retained. Conflicting rulebook versions stop the rename with a clear error. The Computer Applications label is protected until its BCA-only routes use catalog codes.
- Department filtering for HOD access in task and complaint APIs.
- Separate HOD task tracking and private student complaint workspaces, each with its own API and branch access checks.
- `/plot` browser-local performance page reports this visit's Web Vitals, actual browser-reported network transfer sizes, and a timed read-only health check; it clearly labels the sample as local rather than a production percentile.
- **Implemented and locally verified:** The student project directory batches contribution-profile reads, and project feeds/details batch student USN lookups while eager-loading post/comment authors. This removes per-row author/profile queries from the interactive board.
- **Implemented and locally verified, awaiting production migration:** Project posts retain the author's department at creation. Student, staff and HOD feeds, directories, profile lookups, discussion routes, moderation actions and post alerts are restricted to the assigned branch; each HOD moderates only that branch. Existing posts are assigned their author's current branch by migration `l12ncet016`. Institutional administrator, Principal and IQAC accounts keep institution-wide read access.

## P0 — Make the document pipeline usable without AI

1. **Implemented:** Let an HOD prepare an explicit checklist per allocation, shared across selected reference PDFs and saved with each task. AI-drafted rules remain optional and require explicit review.
2. **Implemented:** Reusable department-owned checklist templates with immutable version history and archive controls. HODs can load older versions, edit them, and save a new version before assigning.
3. **Implemented:** Every task API row and queue entry now identifies the next responsible actor and action. Manual review is labeled separately from automated verification.
4. **Implemented:** HOD task tracking groups department references by workflow stage, overdue state, staff member, deadline, update date and search term. Filtered exports stream every matching department task to CSV without including PDF contents; spreadsheet formula cells are escaped.
5. **Implemented:** The worker checks deadlines every 15 minutes, processing up to 10 batches of 100 tasks per check, and sends idempotent in-app reminders to assigned active staff and active HODs in the same department: once when a deadline is within 24 hours, then at most once per UTC day while overdue. A delivery ledger prevents duplicates after worker restarts, and the HOD activity history records each reminder. Email, SMS, and AI services are not called.
6. **Implemented and locally migration-verified:** A deadline index supports the recurring due/overdue reminder scan (migration `j10ncet014`).
7. **Implemented and integration-tested:** Oversight staff summaries use SQL aggregates, and HOD tracking fetches only the newest 60 history entries per visible task in SQL. Task date filters also handle the maximum calendar date without overflowing. Large-production-volume query and load tests remain open.

Acceptance: a HOD can take a reference PDF from upload through assignment and manual review with no AI key; staff can submit revisions; all steps have actor and timestamp history; one branch cannot inspect another branch’s records.

## P1 — Separate branch dashboards for work and complaints

**Implemented:** HOD document task tracking and student complaint handling use separate dashboard pages and distinct records. The task dashboard has task-only status counts; the complaints dashboard has case-only status counts. Both remain department-scoped.

### HOD task dashboard

- Keep the existing task dashboard as the operational queue. It has one-click status views, staff/deadline/date filters, search, sorting and a filtered CSV export. Add saved filters and workload-aware assignment suggestions that HODs confirm.
- Show workload distribution and aging from real task timestamps, with clear empty/loading/error states and a link to each underlying record.
- Add branch-level comparison only for institutional roles; HOD views remain restricted to their own department.

### HOD complaints dashboard

- Improve complaints as a separate workspace from document tasks, with response-time aging, unread replies, and a faster case detail panel. Keep its existing case-only counts and filters.
- Add configurable response targets, overdue escalation to the authorized department lead, and a private audit trail for status and reply actions.
- Add case reference receipts and attachment support only after malware scanning, private storage, retention, and access checks are in place.

Acceptance: task metrics never include complaint records and complaint metrics never include task records; each dashboard links to its distinct workflow and uses the same department access policy as its API.

## P1 — Improve the student desk

- Put active requests, latest response, next step, and last-updated time at the top of the portal.
- **Implemented:** Clickable request status cards filter the student’s own queue. Each request card surfaces the next step, latest HOD response, and last-updated date without exposing other students’ records.
- **Implemented and locally migration-verified:** Composite indexes support the department/student case feed and newest-message lookups (`k11ncet015`), reducing sort and lookup work as case history grows.
- **Implemented:** A student reply reopens a resolved request for HOD review within 14 days of its latest update. After that window, the portal directs the student to create a new request; closed cases remain immutable.
- **Implemented:** Students can print or save a PDF receipt from their own case view. The receipt includes its reference, current status, category, subject, submitted time and request text, and omits the conversation and other students’ information.
- Add student-visible document task tracking only for tasks explicitly assigned to that student. Do not infer student ownership from a department-wide staff task.
- Build a separate student task view only after the HOD workflow supports explicit student recipients, student notifications, consent-aware document access, and an auditable assignment path. Keep request/complaint status separate from document tasks.
- Improve accessibility and mobile forms: keyboard flow, field-level errors, accessible status announcements, and resilient upload progress.
- Replace the legacy BCA-named enrollment routes/model with department-neutral names while preserving existing student IDs and credentials. The current legacy routes now enforce each HOD/staff member's active branch scope; finish the route/model rename after compatibility clients are mapped. Verify CSE and other branch labels across enrollment, login, profile, requests, HOD routing and the public directory.
- Review principal and IQAC access to project posts and student directory details. The principal oversight page now provides institution-wide aggregate counts, but the existing project board still provides detailed reads.
- Paginate and search large department rosters on the server; keep complete, permission-scoped roster exports separate from the current browser-visible page.

Acceptance: a student can sign in, understand the latest status, reply, receive a notification, and retrieve their own receipt; authorization tests prove cross-student access is denied.

## P2 — Automation and production operations

- Move document verification and exports to durable jobs with retry limits, idempotency keys, dead-letter visibility, and worker health reporting.
- Add storage lifecycle/retention controls and a managed object-storage option for production-scale PDFs. Preserve private/no-store download headers.
- Add operator dashboards for queue age, failures, database/storage health, latency, and resource use. Redact student data from logs and define alert thresholds.
- Add backup/restore drills, schema migration checks, security headers, login throttling, dependency update policy, and a documented incident process.
- **Implemented:** One-command Ubuntu installer installs Docker, collects the initial admin login and hostname, generates database/encryption secrets, writes a mode-600 `.env`, starts PostgreSQL, ClamAV, the web/worker and Caddy TLS proxy, then prints DNS/firewall instructions without printing secret values.
- **Implemented, awaiting VPS secrets:** GitHub Actions deploys `main` after CI/security/browser jobs pass when `VPS_DEPLOY_ENABLED=true`; pinned SSH host verification, deploy-path checks, and public route smoke checks are included. Keep Render auto-deploy available after the correct repository is connected.
- Add verified backup/restore drills, schema rollback guidance, log redaction review, privileged MFA, and production p95/queue-age alert thresholds.

## Next release plan

Ship in this order after the repository and production service are connected to the reviewed branch:

1. **Production safety:** resolve the database expiry and exposure, configure malware scanning and `/healthz`, repair the custom-domain certificate, and prove backup restore. These controls come before widening document uploads.
2. **HOD document automation:** workload-aware staff suggestions that HODs confirm, visible retry/failure states for background jobs, and configurable deadline escalation. Keep final decisions human and every change auditable.
3. **Student request desk:** add response target/aging indicators and accessible mobile form progress; keep requests, document tasks, and project activity as separate records and views.
4. **Operations and scale:** server-page student rosters, add queue/storage/database health and real request latency, define retention/export controls, and exercise restore and migration rollback.
5. **Access hardening:** add privileged-user MFA, review institution-wide project access, and agree aggregate-only leadership reporting before changing what those roles can see.
6. **Optional AI:** only after the owner configures a paid provider, add bounded checklist suggestions with explicit HOD approval, cost limits, and a manual fallback. No feature in the first five releases depends on an AI key.

## P3 — Optional AI enhancements

- Configure a provider only when the owner chooses one. Store keys as secrets, report configuration status without exposing them, and enforce spending/time limits.
- Use AI for draft checklist extraction and advisory summaries only. HOD review remains required; unavailable, uncertain, or malformed output routes to manual review.
- Add provider health and usage metrics without sending student complaints or unrelated profile data to a model.

## Main gaps and risks to resolve before claiming production readiness

The evidence-based current audit is in [`PRODUCTION_READINESS_AUDIT_2026-10-21.md`](PRODUCTION_READINESS_AUDIT_2026-10-21.md). It records Render's open database allowlists, Free database expiry risk, missing malware scanning and health check, deployment from the wrong repository, unavailable HTTP latency samples, and the unverified custom-domain TLS issue. The requested repository contains the reviewed snapshot; GitHub Security Audit and full CI both passed. Production release and live role workflows remain blocked by the Render source mismatch and dashboard sign-in.

- **Repository/deployment mismatch:** Render service `srv-db8ig6l9fdbs73ee0ap0` is still wired to `hackerncet/tuxnestsite` on `main`, auto-deploy enabled. The reviewed source is published at `paladuguganeshnaidu/ncet` `main` (`c9d4b242669fa02ec38f16014e6228f096287376`), but this service has not been reconnected. The Render Dashboard currently requires sign-in, and the connected Render MCP has no service-source update operation.
- **Render service controls:** Read-only service metadata shows its health-check path is blank, its database IP allowlist is `0.0.0.0/0`, and it runs on the Free plan. Tighten the database allowlist if supported by the database topology, configure `/healthz`, and choose an always-on production plan before relying on institutional availability.
- **File scanning:** Render sets `SCAN_MODE=off`; uploads receive format/signature/size checks but no malware scan. VPS Compose uses ClamAV and fails closed. Do not enable ClamAV mode on Render until a reachable scanner is provisioned, or uploads will fail closed.
- **Large rosters and community oversight:** The roster API currently returns at most 1,000 students per request. Department-scoped project boards passed local API/browser checks and their migration applies cleanly to a fresh local database; production migration awaits deployment. A principal aggregate dashboard is implemented in source but has not yet been tested. Institution-wide roles still have detailed project and directory access. Finish server-side roster pagination/export and decide the appropriate leadership detail policy before claiming institution-wide student services scale is complete.
- **Custom domain:** The previous browser check of `ncet.paladuguganeshnaidu.tech` failed TLS negotiation. DNS/certificate repair and a fresh secure browser check remain outstanding.
- The `/plot` page measures one browser visit and does not provide server-side production p95 latency or uptime history. Add privacy-preserving server metrics and representative concurrency measurements before sizing or performance claims.
- Local integration and mocked Chromium checks do not replace live role-based verification. The owner authorized a temporary staff-only production workflow with no AI use and cleanup, but it cannot run against the updated source until repository write access and the Render source connection are fixed. Do not create student accounts for smoke tests.
- “100% working” cannot be established from a code review alone. Use explicit acceptance criteria, local API/UI checks, deployment health, and authorized production smoke tests, and report the limits of each.

## Delivery order

1. Manual HOD checklist allocation, idempotent reminders, and accurate branch data.
2. Distinct task/complaint dashboards; student receipts and safe resolved-case follow-up.
3. **Implemented and locally verified:** Catalog-driven enrollment, department-scoped HOD/staff student roster and department-scoped project collaboration for active branches; finish department-neutral route/model names and add aggregate-only institutional community oversight.
4. **Completed locally, without AI-provider calls:** 127 non-AI integration tests passed; all migrations applied with no Alembic drift; 12 Chromium workflows passed; Bandit passed; pip-audit found and helped fix the Pillow 12 vulnerability set; Pillow 13 then returned no known local advisories.
5. Confirm Render database attachment, backup, malware scanning, paid capacity, source repository, and `/healthz`; repair custom-domain TLS.
6. Run the previously authorized live smoke tests using a temporary staff account, public sample PDF, zero AI usage, and explicit task/account cleanup after the updated source is live.
7. Configure VPS deployment secrets and verify the one-command Ubuntu install and GitHub-to-VPS deployment.
8. Add worker failure visibility, retention, backup/restore drills, and production p95/queue-age monitoring.
9. Optional AI provider setup only when the owner supplies a key and budget.
