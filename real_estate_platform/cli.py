from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from .config import PlatformPaths
from .pipeline import run_pipeline


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Azure Real Estate Data Platform local runner")
    parser.add_argument("--repo-root", default=str(Path.cwd()), help="Repository root")
    parser.add_argument("--runtime-root", default=None, help="Optional generated-data root")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="Execute Bronze, Silver, and Gold")
    run.add_argument("--as-of", default=None, help="Snapshot date in YYYY-MM-DD format")
    subparsers.add_parser("inspect", help="Print Power BI-ready city-market rows")
    return parser


def main() -> None:
    args = _parser().parse_args()
    paths = PlatformPaths.create(args.repo_root, args.runtime_root)
    if args.command == "run":
        result = run_pipeline(paths.repo_root, paths.runtime_root, args.as_of)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if not paths.gold_database.exists():
        raise SystemExit("Gold database not found. Run the pipeline first.")
    with sqlite3.connect(paths.gold_database) as connection:
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute("SELECT * FROM mart_city_market")]
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
