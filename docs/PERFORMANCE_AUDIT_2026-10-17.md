# NCET VerifyFlow — performance and interaction audit

Reproducible benchmarks for the public student portfolio and public directory. This audit describes measured local/CI characteristics, **not** unmeasured production Core Web Vitals or a Lighthouse score.

## Benchmark methodology

- Baseline: commit `b2e3c9d05d78766e238269ed3fcdf088c0ff8679`, the last deployed public résumé, GitHub tree blob byte lengths.
- Optimized branch: `feature/profile-tabs-performance-audit-20261017`, static UTF-8 source byte lengths.
- Compared critical assets only; excludes logo files, profile photographs, HTML, gzip/Brotli effects, request RTT and backend response latency. The logo image set is unchanged.
- Responsive tab test: Playwright Chromium on GitHub Actions runner, 6 viewport widths 320, 375, 390, 768, 1024, 1440. Tab timings are wall-clock click-to-settled-panel, measured in a local browser with mocked static responses. Results depend on runner load.
- SQL test: 24 synthetic published students each with a 100 KB stored photo; capture SQLAlchemy SELECT statements and check selected columns/query count on public roster and sitemap.

## Critical asset budget

| Measure | Baseline | Optimized | Change |
|---|---:|---:|---:|
| Uncompressed critical CSS and JS | 38,679 bytes | 14,091 bytes | -63.6% |
| Critical stylesheet/script requests | 6 | 2 | -66.7% |
| Stored image blobs selected by public directory | Could include photo columns in ORM fetch/count | **0** targeted | Removed by defer/projection |
| Directory SQL SELECT count (24 profiles) | Unbounded repeated branch lookups | Maximum 4 (automated assertion) | Batch name retrieval |

Baseline critical CSS sources: `bca.css` (10,432 B), `experience.css` (8,120 B), `responsive-upgrade.css` (6,555 B), `ncet-brand-system.css` (4,636 B) and `resume-profile.css` (7,184 B), plus `ncet-loading.js` (1,752 B).

Optimized profile loads one dedicated CSS file (`resume-profile.css`, 10,839 B) and one small tab script (`student-profile-tabs.js`, 3,252 B). All six sections remain server-rendered; JavaScript enhances them into tabs.

## Behavioral performance and quality checks

- Actual 18-interaction Chromium benchmark **before the last stylesheet refinement** (run `39010513654`): median tab switch **298 ms**, p95 **299 ms**; final run provides updated numbers.
- URL deep linking, Arrow keys, Back navigation, reduced-motion preference, and no-JavaScript fallback.
- Six profile widths and six other routes at seven viewport widths (42 public browser checks), in addition to existing Admin, HOD, Staff, Principal, IQAC smoke tests.
- Dynamic opt-in sitemap preserved; private documents and personal contact details remain excluded from public pages.
- Versioned static CSS and JS cache for up to 1 hour with stale-while-revalidate; nonversioned static assets retain 5-minute max-age.
- Profile HTML and sensitive APIs remain no-store, prioritizing immediate revocation/unpublication.
- The CI tests and reproducible benchmark source live in `tests/browser_student_resume.py`, `tests/browser_responsive_audit.py`, and `tests/test_public_performance.py`.

### Department task feed query guard (2026-10-21)

The `/api/tasks` feed now selects task metadata without loading stored reference-PDF bytes, fetches staff names in one query, and fetches at most 50 decisions per task with one window-function query. A regression test checks the response, selected columns, and query count for a four-task synthetic list. This is a database-work reduction; it is not a measured production latency claim. HOD dashboard pagination and aggregate SQL remain separate from this feed.

## Remaining production instrumentation

For an end-to-end **production** benchmark, measure real-user LCP, INP and CLS; sample server p50/p95 latency at load and DB CPU/memory, and test under representative concurrent users. The tests above cannot honestly certify universal 100% responsiveness or a particular live Lighthouse score.
