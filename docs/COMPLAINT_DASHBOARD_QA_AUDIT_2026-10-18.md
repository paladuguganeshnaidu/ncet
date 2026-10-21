# NCET VerifyFlow — Complaint Dashboard & Application QA Audit
**Audit window:** 18 October 2026 (IST)  
**Scope:** `/complaints`, existing BCA complaints and oversight, HOD tasks, student requests, all existing repository CI flows.  
**Branch:** `feat/complaints-route-audit-hardening-20261018` · **Review:** GitHub PR #24

## Executive outcome
The previous BCA complaint console existed under `/bca/complaints`; the requested `/complaints` route was missing. This revision adds the canonical route and improves high-priority complaint handling, privacy, responsive presentation, and query efficiency. No production student data was modified during the automated simulations. All new test fixtures use an isolated SQLite database and browser mock transport.

**Important:** Clean CI does **not** certify zero security defects, universal accessibility compliance, or production availability. The public Render URL could not be independently accessed through the available browser; the live deployment must still be verified in the correct Render workspace with an authorized test account. Do not use production student complaints as demonstration data.

## Review workstreams
The checks emulate independent reviewer perspectives (not real recruited testers):
1. **Security / tenant isolation:** Authentication, authorization, direct static URL bypass, CSP, CSRF, records owned by other students, Principal summary-only access, other-department HOD denial.
2. **Backend / database:** SQL-level scope, state/category/date/attention filters, pagination, boundary dates, large fixture sets, on-demand complaint details, DB queries that avoid loading private bodies.
3. **Frontend / accessibility:** Semantic heading and label structure, visually distinguished states, keyboard-usable native controls, reduced-motion support, modal details, overflow tests at 320/390/768/1366 pixels, escaped untrusted strings.
4. **Workflow / regression:** New complaint, student reply, HOD reply, status changes, case closure, notifications, student and faculty dashboards, task assignment/approval.
5. **Platform / CI:** Python compile and unit/integration tests, database Alembic migrations/drift, JavaScript syntax, Chromium five-role smoke, public pages, responsive layout, and deployment prerequisites.

## Verified source-code findings and remediations

| ID | Severity | Finding | Remediation |
| --- | --- | --- | --- |
| F-01 | High / functional | `/complaints` was not registered; canonical links used `/bca/complaints`. | Added authenticated `/complaints` and retained old route compatibility; updated HOD navigation, alerts and robots/noindex. |
| F-02 | Medium / privacy hygiene | Private dashboard HTML shell could be fetched directly as `/static/complaints-dashboard.html` without route authorization. The shell itself contains no student records, but this is confusing and contrary to the private-route contract. | Block direct static HTML for complaints/oversight/enrollment; authenticated routes continue serving their pages. |
| F-03 | Medium / privacy | The complaint-detail query retrieved records and conversations before checking student ownership/department. | Restrict query to owner/department before fetching the record, so a student gets consistent 404 for missing/other-student records. |
| F-04 | Medium / performance | BCA oversight used `.all()` on all student complaints and project posts to compute totals. | Changed to grouped SQL counts and limited HOD preview to the 30 newest records; Principal still sees counts only. |
| F-05 | Medium / workflow | No dedicated high-visibility queue for requests awaiting an HOD response or aging unresolved cases. | Added dark priority banner, server-side `awaiting_reply` and `older_than_7d` filters, counters and row indicators. Seven-day age is an **attention signal**, not a fabricated formal SLA. |
| F-06 | Medium / UX | After replying/updating a complaint, the frontend re-opened the already-open dialog and cleared success feedback during refresh. | Refreshes modal content in place, shows the saved confirmation, and disables duplicate form submission while sending. |
| F-07 | Low / responsiveness | Header was fixed to 78px even when the mobile navigation needed an additional line. | Mobile header now expands and navigation wraps; viewport regression checks cover phone/tablet/desktop. |
| F-08 | Medium / compatibility | New per-case age calculations compared timezone-aware UTC with naive datetimes returned by SQLite, causing failed backend tests. | Normalized timestamps before Python age comparisons; PostgreSQL datetimes remain supported. |
| F-09 | Low / test quality | Async browser assertions could check a stale list before the new server filter completed. | Explicitly wait for filtered results, modal loading, and saved notifications. |
| F-10 | Medium / frontend safety | Private student descriptions/messages are untrusted strings. | Existing HTML escaping is retained and a new hostile markup browser fixture asserts no injected `img` or `svg` nodes are rendered. |

## Test matrix
| Surface | Automated scenario | Expected |
| --- | --- | --- |
| Anonymous | Visit `/complaints` or list API | 401 |
| Unauthorized HOD (different department), Staff, Admin, IQAC | Open dashboard or private case list | 403; no private record |
| Authorized BCA HOD | Load `/complaints`, filter, page, open, reply, update status | 200 + restricted data/actions |
| Principal | Open `/complaints`, query oversight and list | Redirect to summary-only oversight; list API 403 |
| Student A vs Student B | Read own versus other student's case | 200 for own; 404 for other or missing |
| Mutation without CSRF | Reply using authenticated cookie only | 403 |
| Closed complaint | Attempt further reply | 409 |
| Status/category/search/dates | Filter and paginate against SQL fixtures | Correct counts and bounded payload |
| Reply attention | New/submitted or latest student message | Listed until HOD response |
| Aged attention | Open request > 7 days, not resolved/closed | Marked and filterable |
| Date boundary | `to_date=9999-12-31` | 200, no arithmetic overflow |
| Direct private shell | Request `/static/complaints-dashboard.html` | 404 |
| XSS-like markup | Inject `<img onerror>` and `<svg onload>` in browser fixture | Rendered as text, not DOM elements |
| Client interaction | Search, select status/attention, clear, open/reply, modal refresh | No JS errors; confirmation persists |
| Phone/tablet/desktop | 320, 390, 768, 1366px complaint browser smoke | No horizontal overflow |
| Wider platform | Five roles, task HOD, BCA student flow, public pages, student resume, menus | Existing GitHub CI suite |
| Data migration | Apply Alembic and drift check | No schema change or pending migration |

## Performance constraints and operating notes
- BCA complaint list returns **20 rows per page** to the new HOD UI; API accepts a bounded `limit` up to 100.
- List queries return fields/counters, **not full complaint descriptions or private conversations**.
- Case details load on explicit click, and searches use a 300ms debounce.
- No external chart library, image analytics SDK, or AI call is introduced for complaint dashboards.
- SQL indexes on `student_cases` department/status/created date, reference, and `student_case_messages.case_id` are reused; query plans under real PostgreSQL load were not benchmarked.
- One dashboard request calculates grouped counts; further performance validation should use production-like datasets and service metrics, not invented latency figures.

## Automated execution evidence
- GitHub Actions run **39061691116**: Python/backend job **success** and Chromium multi-role UI job **success**.
- Backend: **123 passed**, **1 upstream Starlette/AnyIO deprecation warning** (no failed assertions).
- Browser checks: complaint priority filters, modal replies, hostile-markup escaping, five-role task UI, student flows, public pages, student resume, and mobile/desktop responsive audit all passed.
- The final documentation-only commit requires its own green CI run before merge.

## Release / residual risks
1. **Render deployment not verified:** PR merge and CI do not imply a running release. The correct Render workspace/service, deployed commit SHA, migrations, health, assets and signed-in E2E checks must be confirmed.
2. **Real account setup:** A legitimate HOD in a non-BCA department cannot read BCA complaints; administrators must explicitly assign a BCA HOD account to Computer Applications.
3. **Scope:** The existing complaint data model contains BCA student requests. This update does **not** grant a global all-department complaint feed; expanding to other colleges/departments requires separate explicit tenant permissions and data migration.
4. **Security limits:** CI tests a representative threat model, not a full independent penetration test (e.g. advanced abuse, third-party dependencies, infrastructure scanning, and production secrets remain outside scope).
5. **Accessibility limits:** Responsive/role browser automation and semantic controls are checked, but no formal WCAG 2.2 AA certification or real-user assistive technology study is asserted.
6. **Reliability limits:** Load, concurrency and Render cold-start behavior were not measured; do not infer exact latency or throughput.
7. **Zero-defect claim:** A finite automated suite cannot prove zero defects. Treat any future failure as actionable and rerun regressions after each patch.

## Release readiness checklist
- [x] Register `/complaints` and keep legacy URL functional
- [x] Align HOD navigation and notifications with canonical URL
- [x] Scope complaint reads in SQL and enforce per-role API authorization
- [x] Add priority queues, search, category/status/date filters, case replies and updates
- [x] Remove unbounded oversight aggregation
- [x] Extend browser/API tests for security and responsive flows
- [x] Confirm the implementation commit passes both GitHub Actions jobs (run `39061691116`)
- [ ] Confirm **live Render** serves that commit and execute authenticated manual E2E
- [ ] Perform scheduled production-like load/penetration/accessibility testing before asserting comprehensive production certification

**Privacy rule:** Never relax role checks to make an unrelated HOD dashboard look populated; confidentiality comes before convenience.
