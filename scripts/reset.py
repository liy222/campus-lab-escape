"""Safely remove an explicitly selected local game database."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from scripts.dev import ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True, help="explicit directory within this project's data directory")
    parser.add_argument("--confirm", action="store_true", help="perform deletion; omission only previews")
    args = parser.parse_args()
    allowed = ROOT / "data"
    target = args.data_dir.absolute()
    try:
        # Reject traversal through junctions/symlinks before resolving the final path.
        for component in (target, *target.parents):
            if component == ROOT.parent:
                break
            if component.is_symlink() or component.is_junction():
                raise ValueError("symlink/junction data paths are not allowed")
        resolved = target.resolve()
        if not resolved.is_relative_to(allowed.resolve()):
            raise ValueError(f"data directory must be inside {allowed}")
        if not resolved.exists():
            print(f"No data directory exists: {resolved}")
            return 0
        if not resolved.is_dir():
            raise ValueError("data directory must be a directory")
        names = {"game.sqlite", "game.sqlite-wal", "game.sqlite-shm"}
        files = list(resolved.iterdir())
        if any(path.name not in names or not path.is_file() or path.is_symlink() or path.is_junction()
               for path in files):
            raise ValueError("directory contains files other than the known game.sqlite database; refusing deletion")
        print(f"Data directory: {resolved}")
        for path in files:
            print(f"{'Removing' if args.confirm else 'Would remove'}: {path.name}")
            if args.confirm:
                path.unlink()
        if not args.confirm:
            print("Preview only. Stop the app, then add --confirm to delete this database and its saves.")
        return 0
    except (OSError, ValueError) as error:
        print(f"Reset refused: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
