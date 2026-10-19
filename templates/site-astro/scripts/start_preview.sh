#!/bin/sh
set -e

PORT=${PORT:-4321}
node scripts/preview_server.mjs > preview.log 2>&1 &
echo $! > .preview.pid

for i in $(seq 1 40); do
  if curl -s -o /dev/null "http://localhost:${PORT}/" 2>/dev/null || wget -q -O /dev/null "http://localhost:${PORT}/" 2>/dev/null; then
    echo "Preview server responsive on port ${PORT}"
    exit 0
  fi
  sleep 0.25
done

echo "Preview server failed to start within timeout"
cat preview.log
exit 1
