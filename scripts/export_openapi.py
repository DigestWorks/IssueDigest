"""Export the API's canonical schema without starting an HTTP server."""

import json
import sys
from pathlib import Path

from issuedigest_api.main import app

output = Path(sys.argv[1] if len(sys.argv) > 1 else "packages/api-client/openapi.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
