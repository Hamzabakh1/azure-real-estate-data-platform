from __future__ import annotations

import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .bronze import ingest_sources
from .config import PlatformPaths
from .gold import publish_gold
from .io_utils import append_json_line, atomic_write_json
from .silver import transform_to_silver


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_pipeline(
    repo_root: str | Path | None = None,
    runtime_root: str | Path | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Run Bronze → Silver → Gold with checkpointing and operational metadata."""

    snapshot_date = as_of or date.today().isoformat()
    date.fromisoformat(snapshot_date)
    paths = PlatformPaths.create(repo_root, runtime_root)
    paths.prepare_runtime()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    started = time.perf_counter()
    run: dict[str, Any] = {
        "run_id": run_id,
        "snapshot_date": snapshot_date,
        "started_at": _utc_now(),
        "status": "RUNNING",
        "stages": {},
    }
    latest = paths.operations_dir / "latest_run.json"
    history = paths.operations_dir / "pipeline_runs.jsonl"
    atomic_write_json(latest, run)

    try:
        bronze_paths, bronze_metadata = ingest_sources(paths, run_id, snapshot_date)
        run["stages"]["bronze"] = {"status": "SUCCEEDED", "sources": bronze_metadata}
        atomic_write_json(latest, run)

        silver_paths, quality_metrics = transform_to_silver(
            paths, bronze_paths, run_id, snapshot_date
        )
        run["stages"]["silver"] = {"status": "SUCCEEDED", **quality_metrics}
        atomic_write_json(latest, run)

        gold_metrics = publish_gold(paths, silver_paths, snapshot_date)
        run["stages"]["gold"] = {"status": "SUCCEEDED", **gold_metrics}
        run["status"] = "SUCCEEDED"
    except Exception as exc:
        run["status"] = "FAILED"
        run["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        run["finished_at"] = _utc_now()
        run["duration_seconds"] = round(time.perf_counter() - started, 3)
        atomic_write_json(latest, run)
        append_json_line(history, run)

    return run
