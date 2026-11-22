"""Command-line entry point and verification matrix."""

from __future__ import annotations

import argparse
import json
import unittest
from pathlib import Path

from .persistence import atomic_write_json, load_json, parse_entities
from .solver import ScheduleSolver


def main() -> int:
    parser = argparse.ArgumentParser(description="Academic exam and invigilator scheduler")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=Path("schedule.json"))
    parser.add_argument("-b", "--blocks", type=int, required=True)
    parser.add_argument("--verify", action="store_true", help="run the self-contained test matrix")
    args = parser.parse_args()
    if args.verify:
        suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent / "tests"))
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        return 0 if result.wasSuccessful() else 1
    entities = parse_entities(load_json(args.input))
    _, exams, faculty, rooms = entities
    schedule = ScheduleSolver(exams, faculty, rooms, args.blocks).solve()
    atomic_write_json(args.output, schedule.to_dict())
    print(json.dumps(schedule.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
