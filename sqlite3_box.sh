#!/usr/bin/env bash
# Usage: ./sqlite3_box.sh backend/app.db
# Runs sqlite3 with box mode and headers enabled by default.

sqlite3 -cmd ".headers on" -cmd ".mode box" "$@"
