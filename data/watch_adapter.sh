#!/bin/sh
# Closes the loop: when the v1 chain writes its summary, commit the new adapter and push.
# The push touches artifacts/diyo-1-lora/**, which is exactly what .github/workflows/eval.yml
# triggers on, so the score updates without anyone remembering to run it.
set -eu
cd "$(dirname "$0")/.."

SUMMARY=data/train/v1.json
for _ in $(seq 1 240); do
  [ -f "$SUMMARY" ] && break
  sleep 30
done
[ -f "$SUMMARY" ] || { echo "no $SUMMARY after 2h"; exit 1; }

STATUS=$(python3 -c "import json;print(json.load(open('$SUMMARY'))['status'])")
RUN=$(python3 -c "import json;print(json.load(open('$SUMMARY'))['run_id'])")
WIN=$(python3 -c "import json;print(json.load(open('$SUMMARY'))['best_win_rate'])")
SPENT=$(python3 -c "import json;print(json.load(open('$SUMMARY'))['credits_spent'])")

if [ "$STATUS" != "succeeded" ]; then
  echo "run $RUN ended $STATUS — not publishing an adapter"
  exit 1
fi

git add artifacts/diyo-1-lora data/train/v1.json
if git diff --cached --quiet; then
  echo "no adapter change to publish"
  exit 0
fi

git -c user.name=DrSkyle -c user.email=272306194+DrSkyle@users.noreply.github.com commit -q -F - <<EOF
diyo-1: retrained on 2,256 rows (win rate $WIN, $SPENT credits)

AutoScientist run $RUN. The eval workflow scores it automatically.

Co-authored-by: CommandCodeBot <noreply@commandcode.ai>
EOF
git push -q origin HEAD
echo "published $RUN — eval workflow triggered"
