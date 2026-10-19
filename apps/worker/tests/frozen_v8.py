"""Load the byte-identical deployed v8 worker with its original package imports."""

import importlib.util
from pathlib import Path

WORKER = Path(__file__).parent / "fixtures/research_worker_v8.py"
spec = importlib.util.spec_from_file_location("issuedigest_worker.frozen_v8", WORKER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
run_worker = module.run_worker
