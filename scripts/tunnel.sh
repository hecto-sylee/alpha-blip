#!/usr/bin/env bash
# Expose the local server over HTTPS for phone demos.
set -euo pipefail
exec ngrok http "${PORT:-8000}"
