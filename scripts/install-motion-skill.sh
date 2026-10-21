#!/usr/bin/env bash
set -euo pipefail
# Transitions.dev is an agent authoring skill, not a site runtime dependency.
# Install into the local Codex agent folder; don't vendor third-party recipes
# or execute external code in the production application.
export DISABLE_TELEMETRY=1
npx --yes skills add Jakubantalik/transitions.dev --skill '*' --agent codex --copy --yes
if [ ! -f .agents/skills/transitions-dev/SKILL.md ]; then
  echo "Transitions.dev skill installation did not produce SKILL.md" >&2
  exit 1
fi
printf 'Transitions.dev skill installed for local authoring.\n'
