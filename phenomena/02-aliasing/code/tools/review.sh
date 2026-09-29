#!/usr/bin/env bash
# Director's review: one contact sheet per scene (one frame every 15), in a language.
#   tools/review.sh en            all scenes of the main film
#   tools/review.sh ar s04_trick  one scene
set -euo pipefail
cd "$(dirname "$0")/.."
L="${1:-en}"; shift || true
COMP="${COMP:-main}"
SCENES=("$@")
if [ ${#SCENES[@]} -eq 0 ]; then
  SCENES=($(node -e "const c=require('./data/comps.json')['$COMP'];console.log(c.scenes.map(s=>s.id).join(' '))"))
fi
for S in "${SCENES[@]}"; do
  node render.mjs --comp "$COMP" --lang "$L" --scene "$S" --every "${EVERY:-15}" --contact --cols 5 --workers "${WORKERS:-3}" --quiet \
    | grep -E "contact sheet|PROBLEMS|  - " || true
done
