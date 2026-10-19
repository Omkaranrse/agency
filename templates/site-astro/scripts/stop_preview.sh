#!/bin/sh
if [ -f .preview.pid ]; then
  PID=$(cat .preview.pid)
  if [ -n "$PID" ]; then
    kill "$PID" 2>/dev/null || true
  fi
  rm -f .preview.pid
fi
echo "Preview server stopped"
