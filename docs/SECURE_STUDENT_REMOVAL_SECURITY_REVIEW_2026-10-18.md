# NCET VerifyFlow: Secure Student Removal & Security Review
**Review:** 18 October 2026 · **PR:** #25 · **Production:** Not independently verified

## Scope and constraints
This review covers the actual FastAPI/Python backend, database models, BCA management page, browser workflows, CI checks and Python dependency manifest. Automated tests use isolated test fixtures; they never modify the live student roster.

This document does **not** claim the application is unhackable, that all vulnerabilities are gone, or that a production penetration test was completed. Correct institution configuration and operational controls remain essential.

## Student removal workflow
Two separate actions avoid destroying academic evidence:
- **Remove account access**: BCA HOD (department-scoped) and administrator; disable sign-in, revoke every active session, hide published portfolio. Preserve student enrollment row, complaint/academic records and audit history. Can be restored by authorized administrator.
- **Permanently delete eligible account**: administrator only; removes user, enrollment, portfolio, sessions and ephemeral notifications, but **refuses** any selected student who has a durable reference such as complaints, messages, approved documents, comments, collaboration posts, task events or audit history. No partial deletion: one blocked student rejects the entire batch.

Bulk UI allows a maximum of 50 checked USNs per operation. Results are never trusted based on browser inputs alone.

### Security controls
| ID | Defense | Implementation |
| --- | --- | --- |
| SR-01 | Role-based authorization | Backend admin/BCA HOD checks, permanent deletion admin-only |
| SR-02 | Tenant isolation | HOD SQL query restricted to Computer Applications students; unavailable USNs return the same 404 |
| SR-03 | Strong session binding | Both preview and execute require signed-in session and matching CSRF token |
| SR-04 | Two-step impact verification | Preview describes each affected account, public profile and dependencies |
| SR-05 | Tamper/expiration protection | HMAC-SHA256 preview signed with session secret; 5-minute validity; account status, names, departments and blockers included in digest |
| SR-06 | Independent authentication | Password re-verification just before mutation; 5 failures in 15 minutes triggers 429 throttle |
| SR-07 | Explicit consent | Exact displayed confirmation phrase, reason, and backup acknowledgment required for permanent deletion |
| SR-08 | Data-integrity safeguard | PostgreSQL target/actor row locks, automatic FK inspection, integrity-error rollback, all-or-nothing transaction |
| SR-09 | Post-removal containment | Revoke all login sessions, deactivate accounts, unpublish directory profile |
| SR-10 | Traceability | Durable actor/date/USN/action/reason audit log; no passwords or tokens logged |
| SR-11 | Replay mitigation | Already inactive accounts cannot be disabled again; previously deleted USNs no longer resolve |
| SR-12 | Least privilege | Staff, students, Principal, unrelated HOD and IQAC cannot access bulk-removal routes |

## Security findings and remediation
| Finding | Severity | Outcome |
| --- | --- | --- |
| Bulk selection/removal unavailable | Functional | New two-step UI/API, strict role scope and review |
| Risk of deleting referenced academic history | High | Permanent deletion is blocked by any durable user foreign-key reference |
| Credentials remain usable after record removal | High | Sessions revoked and account status disabled atomically |
| Same-site forged bulk mutation | High | CSRF + signed short-lived preview + recent password |
| Credential guessing at high-risk endpoint | Medium | Per-actor 5-failure / 15-minute throttle |
| Preview replacement, replay or drift | Medium | HMAC / session / expiry / account-state digest |
| Local development server exposed on all interfaces | Medium | Default localhost bind; Render production retains required ingress bind |
| Bandit flagged blocked URLs as public listeners | False positive | Narrow #nosec B104 annotations only where URL strings are explicitly rejected |
| Outdated python-multipart | Security advisory | Upgraded to 0.0.32 |
| Older cryptography bound excluded patched releases | Security advisory | Upgraded to 50.0.2 |
| Old FastAPI constrained Starlette to vulnerable releases | Security advisory | Upgraded FastAPI to 0.143.3 and Starlette to 1.8.0 |

## Automated verification
- Python unit/integration test suite and Alembic schema/migration drift checks in GitHub Actions.
- Chromium multi-role smoke, responsive audit across 320–1440px, separate 320/390/768/1366px student-removal browser simulation.
- Dedicated adversarial tests for unauthorized roles, across-department access, forged/expired/changed preview, CSRF, password failures, history blockers, all-or-nothing selection and immediately invalidated student sessions.
- CI has a new separate **NCET Security Audit** workflow: Bandit source inspection for medium/high-severity patterns and `pip-audit` for published dependency advisories.
- Track the PR's final GitHub Actions jobs before marking this change verified; green previous commits do not suffice after later dependency updates.

## Vulnerability-scan evidence
The initial Bandit run flagged three B104 occurrences: Render's intended 0.0.0.0 production ingress and two blocked-URL checks. Development was changed to loopback; the production bind and denied host strings carry narrow documented exceptions. The initial dependency audit reported 23 advisory *entries* across three packages (some repeated). Requirements were upgraded from python-multipart 0.0.29 to 0.0.32, cryptography from 46.x constraints to 50.0.2, and FastAPI/Starlette to 0.143.3/1.8.0. Subsequent NCET Security Audit job 117690816439 returned success and logged: **No known vulnerabilities found**. Scanner success is not a proof of no unknown vulnerabilities.

## Important residual security risks
1. **Antivirus is not active in Render blueprint.** `render.yaml` currently has `SCAN_MODE=off`. Existing file size/type/magic signature/ZIP limits reduce risk but do not replace malware scanning. Enable a **properly provisioned** ClamAV or managed scanning service in production and verify fail-closed behavior; don't set `SCAN_MODE=clamav` without a scanner or file uploads will fail.
2. **No external penetration test** has been performed: advanced attacks, race conditions under live PostgreSQL load, infrastructure/secrets, vendor accounts and incident response require additional work.
3. **No real-production E2E sign-off:** Render service owner, deployed SHA, environment, TLS, database backup and actual account roles must be verified without exposing private student information.
4. **Permanent deletion remains irreversible.** The user must actually ensure a restorable backup and confirm institutional retention policy before choosing it; a checkbox cannot prove that a backup exists.
5. **Multi-factor authentication** for privileged roles is not part of the current login system. Prioritize MFA/passkeys or SSO with institution policy and session control.
6. **Consent and audit retention:** disable is preferred where complaint, examination or legal records must remain. Avoid pasting student passwords into tickets/chats.
7. **High availability:** free Render service and synchronous expensive analysis cannot guarantee no downtime. Use service monitoring, bounded jobs, prepared restores and dedicated production infrastructure.
8. **Security scanners have blind spots:** clean Bandit/pip-audit/CI is not the same as full OWASP ASVS, WCAG, SOC2, PCI, or zero vulnerabilities.

## Release checklist
- [x] New authorized selection-based removal endpoints and UI
- [x] Protect student/academic history by default
- [x] Require review, confirmation, password and CSRF
- [x] Add adversarial API and browser regressions
- [x] Add Bandit and pip-audit workflows
- [x] Update dependencies after vulnerability findings
- [ ] Require final green Python/Chromium/security checks before merge (prior fully-green run: 39132658900; latest UI wording patch pending recheck)
- [ ] Confirm Render deployment and live authorized role review
- [ ] Provision upload malware scanner, operational backups and privileged MFA

## Guidance for HODs
Use **Student registration → Registered students**, search/select students, review the removal impact, type the exact confirmation and re-enter your own account password. **Remove account access** is recommended for student roster cleanup. Only an administrator can choose permanent deletion, and it is refused when academic or complaint history exists.
