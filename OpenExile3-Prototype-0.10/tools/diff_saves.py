#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from openexile3.save import PARTY_GOLD, PARTY_OFFSET, parse_save


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two Exile III saves.")
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--exe", type=Path)
    args = parser.parse_args()

    a = args.before.read_bytes()
    b = args.after.read_bytes()
    if len(a) != len(b):
        print(f"Sizes differ: {len(a):,} vs {len(b):,}")
    diffs = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
    diffs.extend((i, None, b[i]) for i in range(len(a), len(b)))
    diffs.extend((i, a[i], None) for i in range(len(b), len(a)))

    sa = parse_save(args.before, exe_path=args.exe)
    sb = parse_save(args.after, exe_path=args.exe)
    print(f"Known fields: gold {sa.gold} -> {sb.gold}; food {sa.food} -> {sb.food}; day {sa.day} -> {sb.day}")
    print(f"Raw differing bytes: {len(diffs)}")
    gold_offsets = {PARTY_OFFSET + PARTY_GOLD, PARTY_OFFSET + PARTY_GOLD + 1}
    for off, x, y in diffs[:256]:
        label = " [gold]" if off in gold_offsets else ""
        left = "--" if x is None else f"{x:02X}"
        right = "--" if y is None else f"{y:02X}"
        print(f"  0x{off:06X} ({off:6d}): {left} -> {right}{label}")
    if len(diffs) > 256:
        print(f"  ... {len(diffs)-256} more differences")


if __name__ == "__main__":
    main()
