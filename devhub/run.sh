#!/usr/bin/with-contenv sh
set -eu

mkdir -p /config/uploads
export DEVHUB_DATA_DIR=/config
export DEVHUB_DATABASE_URL="sqlite:////config/devhub.db"

if [ -f /data/options.json ]; then
  eval "$(python3 - <<'PY'
import json
import shlex
from pathlib import Path
p = Path('/data/options.json')
try:
    data = json.loads(p.read_text())
except Exception:
    data = {}
keys = {
    'DEVHUB_GITHUB_TOKEN': data.get('github_token', ''),
    'DEVHUB_GITHUB_OWNER': data.get('github_owner', ''),
    'DEVHUB_AI_ENABLED': str(bool(data.get('ai_enabled', False))).lower(),
    'DEVHUB_AI_PROVIDER': data.get('ai_provider', 'openai'),
    'DEVHUB_AI_MODEL': data.get('ai_model', 'gpt-5-mini'),
    'DEVHUB_AI_API_KEY': data.get('ai_api_key', ''),
    'DEVHUB_AI_BASE_URL': data.get('ai_base_url', 'https://api.openai.com/v1'),
}
for key, value in keys.items():
    print(f'export {key}={shlex.quote(str(value or ""))}')
PY
)"
fi

cd /app
alembic upgrade head
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8099 --proxy-headers
