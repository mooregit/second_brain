#!/usr/bin/env bash
set -euo pipefail

EXTRACTION_MODEL="${OLLAMA_EXTRACTION_MODEL:-qwen3:8b}"
EMBEDDING_MODEL="${OLLAMA_EMBEDDING_MODEL:-nomic-embed-text}"
PYTHON_BIN="${PYTHON_BIN:-}"

if [ -z "${PYTHON_BIN}" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "Neither python3 nor python is available on the host."
    exit 1
  fi
fi

echo "Checking Ollama from the host..."
if ! curl -fsS http://localhost:11434/api/tags >/tmp/second-brain-ollama-host.json; then
  cat <<'EOF'
Ollama is not reachable from the host at http://localhost:11434.

Try:
  sudo systemctl status ollama
  sudo systemctl restart ollama
  curl http://localhost:11434/api/tags

If Ollama is not installed as a systemd service, start it with:
  ollama serve
EOF
  exit 1
fi
cat /tmp/second-brain-ollama-host.json
echo

"${PYTHON_BIN}" - <<PY
import json

required = {"${EXTRACTION_MODEL}", "${EMBEDDING_MODEL}"}
with open("/tmp/second-brain-ollama-host.json", "r", encoding="utf-8") as handle:
    model_names = {model["name"] for model in json.load(handle).get("models", [])}

models = set(model_names)
for name in model_names:
    if name.endswith(":latest"):
        models.add(name.removesuffix(":latest"))

missing = sorted(required - models)
if missing:
    print("Missing configured Ollama model(s): " + ", ".join(missing))
    print("Install them with:")
    for model in missing:
        print(f"  ollama pull {model}")
else:
    print("Configured Ollama models are installed.")
PY

if ! docker compose -f docker-compose.dev.yml ps >/dev/null 2>&1; then
  cat <<'EOF'
Docker Compose is not accessible from this shell.

Try one of:
  newgrp docker
  sudo usermod -aG docker "$USER" && log out/in
  sudo docker compose -f docker-compose.dev.yml ps

After Docker access works, rerun:
  ./scripts/check-ollama-docker.sh
EOF
  exit 1
fi

echo "Checking Ollama from the backend container..."
docker compose -f docker-compose.dev.yml exec -T backend python - <<'PY'
import httpx
import sys

try:
    response = httpx.get("http://host.docker.internal:11434/api/tags", timeout=5)
    response.raise_for_status()
except httpx.ConnectError as exc:
    print("Backend container resolved host.docker.internal, but could not connect to Ollama.")
    print("This usually means Ollama is bound to 127.0.0.1 only.")
    print()
    print("On Linux with systemd-managed Ollama, run:")
    print("  sudo systemctl edit ollama")
    print()
    print("Add:")
    print("  [Service]")
    print('  Environment="OLLAMA_HOST=0.0.0.0:11434"')
    print()
    print("Then run:")
    print("  sudo systemctl daemon-reload")
    print("  sudo systemctl restart ollama")
    print("  ss -ltnp | grep 11434")
    print()
    print("The ss output should show 0.0.0.0:11434 or [::]:11434, not only 127.0.0.1:11434.")
    print(f"Original error: {exc}")
    sys.exit(1)
except httpx.HTTPError as exc:
    print(f"Backend container reached Ollama but received an HTTP error: {exc}")
    sys.exit(1)

print(response.json())
PY

echo "Ollama is reachable from both host and backend container."
