#!/bin/bash

# Kill existing processes on ports 8000 and 8080 if any
fuser -k 8000/tcp > /dev/null 2>&1
fuser -k 8080/tcp > /dev/null 2>&1

# Ensure local bin is in PATH
export PATH=$PATH:/home/ubuntu/.local/bin

# Get project root (2 levels up from scripts/dev)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"
echo "Running from: $PROJECT_ROOT"

echo "Starting Developer Tools (Remote Mode)..."

# Start FastAPI Server
# Note: 'api' is at root in remote deployment
echo "[+] Starting API Server on http://localhost:8000/docs"
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# Start SQLite Web
# Note: 'db' is at root in remote deployment
echo "[+] Starting Database Viewer on http://localhost:8080"
sqlite_web db/vpn_bot.db --port 8080 --no-browser --host 0.0.0.0 &
DB_PID=$!

echo "Tools running. Press Ctrl+C to stop."

# Wait for user to exit
trap "kill $API_PID $DB_PID; exit" SIGINT
wait
