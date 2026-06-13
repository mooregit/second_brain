#!/usr/bin/env bash
set -euo pipefail

HOSTNAME="${1:-secondbrain}"
ENTRY="127.0.0.1 ${HOSTNAME}"

if grep -Eq "^[[:space:]]*127\\.0\\.0\\.1[[:space:]].*\\b${HOSTNAME}\\b" /etc/hosts; then
  echo "${HOSTNAME} already exists in /etc/hosts"
  exit 0
fi

echo "${ENTRY}" | sudo tee -a /etc/hosts >/dev/null
echo "Added ${ENTRY} to /etc/hosts"

