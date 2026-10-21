#!/usr/bin/env bash
set -Eeuo pipefail

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 2; }

[[ "${VPS_PUBLIC_ORIGIN:-}" =~ ^https://[^/]+$ ]] || fail 'Set VPS_PUBLIC_ORIGIN to an HTTPS origin without a path.'

curl_args=(--fail --silent --show-error --retry 10 --retry-all-errors --retry-delay 6)
health_response="$(curl "${curl_args[@]}" "${VPS_PUBLIC_ORIGIN}/healthz")"
grep -Eq '"ok"[[:space:]]*:[[:space:]]*true' <<<"$health_response" || fail '/healthz did not return the expected ready response.'

plot_response="$(curl "${curl_args[@]}" "${VPS_PUBLIC_ORIGIN}/plot")"
grep -Fq 'Performance, made visible.' <<<"$plot_response" || fail '/plot did not return the performance page.'

portal_response="$(curl "${curl_args[@]}" "${VPS_PUBLIC_ORIGIN}/students/portal")"
grep -Fq 'Sign in using your USN' <<<"$portal_response" || fail '/students/portal did not return the sign-in page.'

printf 'Public HTTPS smoke passed for /healthz, /plot, and /students/portal.\n'
