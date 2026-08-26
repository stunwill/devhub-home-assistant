#!/usr/bin/with-contenv sh
set -eu

mkdir -p /config/uploads
export DEVHUB_DATA_DIR=/config
export DEVHUB_DATABASE_URL="sqlite:////config/devhub.db"

if [ -f /data/options.json ]; then
  export DEVHUB_GITHUB_TOKEN="$(python3 - <<'PY'
import json
from pathlib import Path
p = Path('/data/options.json')
try:
    print(json.loads(p.read_text()).get('github_token',''))
except Exception:
    print('')
PY
)"
  export DEVHUB_GITHUB_OWNER="$(python3 - <<'PY'
import json
from pathlib import Path
p = Path('/data/options.json')
try:
    print(json.loads(p.read_text()).get('github_owner',''))
except Exception:
    print('')
PY
)"
fi

cd /app
alembic upgrade head
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8099 --proxy-headers
