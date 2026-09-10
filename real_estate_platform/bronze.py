from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import PlatformPaths
from .io_utils import read_csv, read_json, sha256


def ingest_sources(paths: PlatformPaths, run_id: str, as_of: str) -> tuple[dict[str, Path], list[dict[str, Any]]]:
    """Copy immutable source snapshots into partitioned Bronze folders."""

    manifest = read_json(paths.source_manifest)
    outputs: dict[str, Path] = {}
    metadata: list[dict[str, Any]] = []
    seen_entities: set[str] = set()

    for source in manifest["sources"]:
        entity = source["entity"]
        if entity in seen_entities:
            raise ValueError(f"Duplicate entity in source manifest: {entity}")
        seen_entities.add(entity)
        source_path = paths.source_dir / source["file"]
        if not source_path.is_file():
            raise FileNotFoundError(f"Missing source file: {source_path}")

        destination = (
            paths.lake_dir
            / "bronze"
            / entity
            / f"ingest_date={as_of}"
            / f"run_id={run_id}"
            / source_path.name
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        outputs[entity] = destination

        if source["format"] == "csv":
            record_count = len(read_csv(destination))
        elif source["format"] == "json":
            payload = read_json(destination)
            record_count = len(payload if isinstance(payload, list) else payload.get("records", []))
        else:
            raise ValueError(f"Unsupported source format: {source['format']}")

        metadata.append(
            {
                "entity": entity,
                "source_file": source["file"],
                "bronze_path": str(destination.relative_to(paths.runtime_root)),
                "record_count": record_count,
                "sha256": sha256(destination),
                "ingested_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            }
        )

    return outputs, metadata
