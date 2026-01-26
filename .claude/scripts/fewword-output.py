#!/usr/bin/env python3
"""
Fewword output filter.

Replaces fragile sed-based output processing with Python string handling to
avoid failures when output contains special characters.
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Fewword output filter")
    parser.add_argument(
        "--strip-trailing",
        action="store_true",
        help="Strip trailing whitespace from each line",
    )
    args = parser.parse_args()

    data = sys.stdin.read()
    if args.strip_trailing:
        data = "\n".join(line.rstrip() for line in data.splitlines())

    sys.stdout.write(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
