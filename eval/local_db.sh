#!/usr/bin/env bash
# Start/stop a throwaway local PostgreSQL (with pgvector) for the RAG evaluation.
# Usage: eval/local_db.sh start|stop
# Needs PostgreSQL binaries with the pgvector extension (e.g. Postgres.app). Set PG_BIN to override.
set -euo pipefail

PG_BIN="${PG_BIN:-/Applications/Postgres.app/Contents/Versions/latest/bin}"
DIR="$(cd "$(dirname "$0")" && pwd)/.pgdata"
PORT="${EVAL_PG_PORT:-5548}"

case "${1:-}" in
  start)
    if [ ! -d "$DIR" ]; then
      "$PG_BIN/initdb" -D "$DIR" -U evaluser --auth=trust >/dev/null
    fi
    if ! "$PG_BIN/pg_ctl" -D "$DIR" status >/dev/null 2>&1; then
      "$PG_BIN/pg_ctl" -D "$DIR" -o "-p $PORT -c listen_addresses=127.0.0.1 -c unix_socket_directories=''" \
        -l "$DIR/server.log" -w start >/dev/null
    fi
    "$PG_BIN/createdb" -h 127.0.0.1 -p "$PORT" -U evaluser eval_db 2>/dev/null || true
    "$PG_BIN/psql" -q -h 127.0.0.1 -p "$PORT" -U evaluser eval_db -c "CREATE EXTENSION IF NOT EXISTS vector"
    echo "export DATABASE_URL=postgresql://evaluser@127.0.0.1:$PORT/eval_db"
    ;;
  stop)
    "$PG_BIN/pg_ctl" -D "$DIR" stop
    ;;
  *)
    echo "usage: $0 start|stop" >&2; exit 1
    ;;
esac
