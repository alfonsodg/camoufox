#!/bin/bash
set -e
cd "$(dirname "$0")/.."
PORT=8888

# Kill any existing instance
pkill -f "uvicorn service.app" 2>/dev/null || true
sleep 1

# Start service
echo "Starting solver service..."
POOL_SIZE=1 uvicorn service.app:app --port $PORT --log-level info &>/tmp/solver.log &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null" EXIT

# Wait for ready
for i in $(seq 1 30); do
  if curl -s --max-time 2 http://127.0.0.1:$PORT/health | grep -q "ok"; then
    break
  fi
  sleep 2
done

echo "=== Health Check ==="
curl -s http://127.0.0.1:$PORT/health | python3 -m json.tool

echo ""
echo "=== Solving reCAPTCHA v3 for SEACE ==="
RESULT=$(curl -s -X POST http://127.0.0.1:$PORT/solve \
  -H "Content-Type: application/json" \
  -d '{
    "type": "recaptcha_v3",
    "url": "https://prod2.seace.gob.pe/seacebus-uiwd-pub/buscadorPublico/buscadorPublico.xhtml",
    "sitekey": "6Lfhnb0pAAAAAB3RxPrOlihIByQUBjpZCAjX-cY2",
    "action": "search",
    "timeout": 30
  }')

echo "$RESULT" | python3 -m json.tool

SUCCESS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('success',False))")
TOKEN_LEN=$(echo "$RESULT" | python3 -c "import sys,json; t=json.load(sys.stdin).get('token',''); print(len(t) if t else 0)")
SOLVE_TIME=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('solve_time_ms',0))")

echo ""
echo "=== Result ==="
echo "Success: $SUCCESS"
echo "Token length: $TOKEN_LEN"
echo "Solve time: ${SOLVE_TIME}ms"
