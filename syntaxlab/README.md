# SyntaxLab® — CEP-5 Formal Language Validator

Visual interactive educational Email / URL Validator for **Theory of Computation**.

## Features

- Kinetic-typography editorial design: warm ivory `#FFFEF8`, electric cyan `#00D3FF`, original canvas 3D sphere and CSS 3D components.
- Functional Node.js HTTP API for email and URL syntax checking, per-symbol state trace, reasons and position reporting.
- Working step/back/play/reset finite-state visualization, positive/negative test suite, copy and locally saved runs.
- 37 bundled tests with Node's built-in test runner; no npm install necessary.
- Responsive, keyboard accessible, reduced-motion friendly, strict content-security policy.
- Original layouts and illustrations; uses libre Google Fonts Anton, DM Sans, Space Mono instead of proprietary F37 Judge.

## Run locally

```bash
node --version # 20+
npm test
npm start
# open http://localhost:3000
```

## Render deployment

One Render web service, runtime `node`, build `echo ready`, start command `node server.js`. Bind to `PORT` automatically. Health check: `/api/health`.

## APIs

- `GET /api/health` — status.
- `POST /api/validate` — JSON `{ "mode": "email"|"url", "input": "..." }`; returns accept/reject, rule, error position, trace, states, extracted parts.
- `GET /api/cases` — actually evaluates the included test cases.
- `POST /api/batch` — JSON `{ "items": [{"mode":"url","input":"https://example.com"}] }`, max 100 items.

## TOC model

Email is a restricted dot-atom ASCII local part plus domain labels and alphabetic suffix. The scanner records deterministic state transitions, then checks length and suffix policies. URL uses `http(s)://`, host `DOMAIN|localhost`, optional port, and optional path, query and fragment; unsupported IPv6, IDN, userinfo, and advanced RFC URL edge cases are rejected by design. The URL trace records transitions through grammar components; it is not a claim to be a complete RFC-equivalent DFA.

**Syntax-valid is not deliverable, reachable, or safe.** No email messages or requests to submitted URLs are sent.

## Supabase optional persistence

`supabase/schema.sql` sets up authenticated per-user saved runs under RLS. The initial frontend deliberately saves only to `localStorage` until a separate Supabase project and authentication are configured. Do **not** insert email addresses into publicly accessible telemetry tables.

## Reference

The visual direction is inspired by Mat Voyce's editorial kinetic-type portfolio without copying code, art, branding, or proprietary fonts. Work authored for NCET CEP-5.
