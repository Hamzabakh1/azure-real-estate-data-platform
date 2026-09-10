from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlatformPaths:
    """Resolved project and runtime paths.

    ``repo_root`` contains versioned code and source fixtures. ``runtime_root`` can
    point to a temporary directory in CI so generated lake, database, and log files
    never modify the checkout.
    """

    repo_root: Path
    runtime_root: Path

    @classmethod
    def create(
        cls, repo_root: str | Path | None = None, runtime_root: str | Path | None = None
    ) -> "PlatformPaths":
        repository = Path(repo_root or Path.cwd()).resolve()
        runtime = Path(runtime_root or repository).resolve()
        return cls(repository, runtime)

    @property
    def source_dir(self) -> Path:
        return self.repo_root / "data" / "source"

    @property
    def source_manifest(self) -> Path:
        return self.repo_root / "config" / "source_manifest.json"

    @property
    def lake_dir(self) -> Path:
        return self.runtime_root / "data" / "lake"

    @property
    def quarantine_dir(self) -> Path:
        return self.runtime_root / "data" / "quarantine"

    @property
    def gold_dir(self) -> Path:
        return self.runtime_root / "data" / "gold"

    @property
    def operations_dir(self) -> Path:
        return self.runtime_root / "data" / "operations"

    @property
    def gold_database(self) -> Path:
        return self.gold_dir / "real_estate_analytics.db"

    @property
    def local_schema(self) -> Path:
        return self.repo_root / "sql" / "local_sqlite_schema.sql"

    def prepare_runtime(self) -> None:
        for directory in (
            self.lake_dir,
            self.quarantine_dir,
            self.gold_dir,
            self.operations_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
