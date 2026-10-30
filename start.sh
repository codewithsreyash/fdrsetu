#!/usr/bin/env bash
# FDRSETU one-command startup (dev mode)
set -e
cd "$(dirname "$0")"

# 1. Infrastructure (Postgres + Redis) — skip if already running
if command -v docker >/dev/null && ! docker ps --format '{{.Names}}' | grep -q fdrsetu-pg; then
  docker compose up -d || docker-compose up -d
fi

# 2. Backend
cd backend
if [ ! -d venv ]; then
  python3 -m venv venv
  ./venv/bin/pip install -r requirements.txt
fi
./venv/bin/python -m app.seed   # seeds demo data on first run only
./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# 3. Frontend
cd ../frontend
[ -d node_modules ] || npm install
npm run dev &
FE_PID=$!

echo ""
echo "FDRSETU running:"
echo "  Frontend  http://localhost:5173"
echo "  API       http://localhost:8000/api  (Swagger: /docs)"
echo ""
echo "Demo logins (password: Demo@123):"
echo "  institution@fdrsetu.demo  officer@fdrsetu.demo  bank@fdrsetu.demo  admin@fdrsetu.demo"
wait $API_PID $FE_PID
