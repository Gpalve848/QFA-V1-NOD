#!/usr/bin/env bash
# Runs the experiment protocol (see README.md) end to end.
#   bash experiments/run_all.sh              # all scenarios
#   bash experiments/run_all.sh E3 E5        # selected scenarios
# Requires the stack to be up (docker compose up -d) and the `qaf` CLI on PATH.

set -u
cd "$(dirname "$0")/.."
# Stop Git Bash on Windows from rewriting container paths like /scripts/load.js.
export MSYS_NO_PATHCONV=1

COOLDOWN=${COOLDOWN:-60}   # seconds between scenarios so rate() windows clear
WARMUP=${WARMUP:-75}       # seconds of load before recording starts
RECORD=${RECORD:-180}      # seconds of recording per scenario
INTERVAL=${INTERVAL:-15}

#        id  scenario                 k6 profile  fault command (empty = none)
SCENARIOS=(
  "E1|low|low|"
  "E2|medium|medium|"
  "E3|peak|peak|"
  "E4|spike|spike|"
  "E5|failure-payment-errors|medium|qaf chaos payment --error-rate 0.3"
  "E6|failure-order-latency|medium|qaf chaos order --latency 800"
  "E7|failure-product-cpu|medium|qaf chaos product --cpu-burn 30"
  "E8|failure-user-memory|low|qaf chaos user --leak-mb 220"
  "E9|outage-payment|medium|docker compose stop payment"
)

# Restarting the services gives every scenario a clean process (no leaked memory,
# no injected faults) instead of carrying state over from the previous scenario.
reset_all() {
  docker compose restart user product order payment >/dev/null 2>&1
}

selected=("$@")
for entry in "${SCENARIOS[@]}"; do
  IFS='|' read -r id scenario profile fault <<<"$entry"
  if [ ${#selected[@]} -gt 0 ] && [[ ! " ${selected[*]} " =~ " $id " ]]; then continue; fi

  echo "===== $id $scenario (load: $profile, fault: ${fault:-none}) ====="
  reset_all
  sleep "$COOLDOWN"

  docker compose run --rm k6 run --quiet -e PROFILE="$profile" \
    --summary-export "/scripts/results/k6-$scenario.json" /scripts/load.js >"load-tests/results/k6-$scenario.log" 2>&1 &
  k6_pid=$!

  sleep 15
  [ -n "$fault" ] && eval "$fault" >/dev/null
  sleep $((WARMUP - 15))

  qaf record --scenario "$scenario" --duration "$RECORD" --interval "$INTERVAL" \
    --out "experiments/results/$id-$scenario.csv" | grep -E '^\s+\[' || true

  wait "$k6_pid"
done

reset_all
echo "===== done ====="
qaf summarize experiments/results/E*.csv
