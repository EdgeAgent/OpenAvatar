#!/bin/sh
# Talking Avatar Bench — start the server (macOS/Linux).
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python server.py
