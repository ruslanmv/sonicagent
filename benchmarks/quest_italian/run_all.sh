#!/usr/bin/env bash
# Italian streaming bench over the Quest client's real path, on one machine:
#   headless Chromium (the Avatar's own TTS modules, AudioWorklet player at 48 kHz)
#   → OllaBridge Cloud's voice router (bench launcher) → SonicAgent with real Piper.
#
# Usage:
#   benchmarks/quest_italian/run_all.sh <label> '<client cfg json>' [voice ...]
#   e.g. run_all.sh baseline '{}'
#        run_all.sh jitter200 '{"jitterMs":200}' it_IT-giorgio-high
#
# Every voice gets a FRESH SonicAgent process, so its first reply is a true cold start.
# Server-side changes are tested by exporting SONIC_* before calling this (they pass through).
# See README.md next to this file for one-time setup.
set -uo pipefail

label=${1:?label}
cfg=${2:-'{}'}
shift 2 || true
voices=${*:-it_IT-paola-medium it_IT-serena-high it_IT-aurora-medium it_IT-giorgio-high}

HERE=$(cd "$(dirname "$0")" && pwd)
SONIC_DIR=${SONIC_DIR:-$(cd "$HERE/../.." && pwd)}
AVATAR_DIR=${AVATAR_DIR:?set AVATAR_DIR to a 3D-Avatar-Chatbot checkout}
OLLABRIDGE_DIR=${OLLABRIDGE_DIR:?set OLLABRIDGE_DIR to an ollabridge-cloud checkout}
WORK=${WORK:-${TMPDIR:-/tmp}/sonic-it-bench}
SA_CACHE=${SA_CACHE:-$WORK/sa-cache}
SA_CPUS=${SA_CPUS:-0,1} # the free HF CPU Space has 2 vCPUs
SA_PORT=${SA_PORT:-8701}
export OB_PORT=${OB_PORT:-8702}
export WWW_PORT=${WWW_PORT:-8090}
export BENCH_RESULTS=${BENCH_RESULTS:-$SONIC_DIR/benchmarks/results/quest_italian}
KEY=${BENCH_SERVICE_KEY:-bench-service-key-0123456789abcdef}
ORIGIN=http://127.0.0.1:$WWW_PORT
mkdir -p "$WORK/www" "$WORK/logs" "$BENCH_RESULTS"

# The page: the Avatar's src/ as it is, plus bench.html.
ln -sfn "$AVATAR_DIR/src" "$WORK/www/src"
cp "$HERE/bench.html" "$WORK/www/bench.html"
if ! curl -s -m 2 "$ORIGIN/bench.html" >/dev/null; then
    (cd "$WORK/www" && nohup python3 -m http.server "$WWW_PORT" --bind 127.0.0.1 >"$WORK/logs/www.log" 2>&1 &)
fi

# OllaBridge, once for the whole run.
if ! curl -s -m 2 "http://127.0.0.1:$OB_PORT/health" >/dev/null; then
    (
        cd "$HERE" &&
            OLLAMBRIDGE_VOICE_MODE=huggingface OLLAMBRIDGE_VOICE_BASE_URL=http://127.0.0.1:$SA_PORT \
                OLLAMBRIDGE_VOICE_API_KEY=$KEY OLLAMBRIDGE_VOICE_ALLOWED_ORIGINS=$ORIGIN CORS_ORIGINS=$ORIGIN \
                nohup "$OLLABRIDGE_DIR/.venv/bin/python" ollabridge_bench.py >"$WORK/logs/ollabridge.log" 2>&1 &
    )
    sleep 8
fi

start_sonic() {
    pkill -f "uvicorn sonicagent_rt.app:app --host 127.0.0.1 --port $SA_PORT" 2>/dev/null
    sleep 1
    (
        cd "$SONIC_DIR" &&
            SONIC_MODEL_CACHE_DIR=$SA_CACHE SONIC_TTS_ENABLED=true SONIC_VOICE_ENABLED=true \
                SONIC_AUTH_MODE=token SONIC_API_KEY=$KEY SONIC_STT_MODEL=tiny SONIC_STT_ALLOW_DOWNLOAD=true \
                SONIC_STT_WARMUP=true SONIC_STT_CPU_THREADS=2 SONIC_STT_MAX_CONCURRENCY=1 \
                SONIC_TTS_VOICE=${SONIC_TTS_VOICE:-it_IT-riccardo-x_low} SONIC_ALLOWED_ORIGINS=$ORIGIN \
                nohup taskset -c "$SA_CPUS" .venv/bin/uvicorn sonicagent_rt.app:app --host 127.0.0.1 \
                --port "$SA_PORT" --workers 1 >"$WORK/logs/sonicagent-$label-$1.log" 2>&1 &
    )
    # Ready = OllaBridge reports SonicAgent's STT and TTS ready (it refuses sessions before).
    for _ in $(seq 1 120); do
        curl -s -m 2 -H "Authorization: Bearer bench-device-token" \
            "http://127.0.0.1:$OB_PORT/v1/voice/capabilities" | grep -q '"stt_ready":true' && return 0
        sleep 1
    done
    echo "SonicAgent did not become ready; see $WORK/logs/sonicagent-$label-$1.log" >&2
    return 1
}

NODE_PATH=${NODE_PATH:-$(npm root -g)}
export NODE_PATH
for v in $voices; do
    start_sonic "$v" || exit 1
    sleep 2
    timeout 1200 node "$HERE/run.cjs" "$v" "$label" "$cfg" | tee -a "$BENCH_RESULTS/$label.log"
done
echo "results: $BENCH_RESULTS/$label  (next: python $HERE/analyze.py $label; node $HERE/summarize.cjs $label)"
