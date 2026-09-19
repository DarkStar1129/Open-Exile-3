#!/usr/bin/env python3
"""Summarize semantic changes between two Exile III save files.

Useful for reverse-engineering changes made by the original EXILE3ED.EXE
without dumping thousands of raw byte differences.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openexile3.save import SKILL_NAMES, parse_save


def inventory_diff(a: tuple[str, ...], b: tuple[str, ...]) -> str:
    if a == b:
        return ""
    return f"inventory: {list(a)} -> {list(b)}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("before", type=Path)
    ap.add_argument("after", type=Path)
    ap.add_argument("--exe", type=Path, default=None, help="optional EXILE3.EXE for town names")
    args = ap.parse_args()

    before = parse_save(args.before, exe_path=args.exe)
    after = parse_save(args.after, exe_path=args.exe)
    raw_a = args.before.read_bytes()
    raw_b = args.after.read_bytes()

    print(f"Before: {args.before}")
    print(f"After:  {args.after}")
    print(f"Raw differing bytes: {sum(a != b for a, b in zip(raw_a, raw_b)) + abs(len(raw_a)-len(raw_b))}")
    for label, a, b in (
        ("age", before.age, after.age),
        ("day", before.day, after.day),
        ("gold", before.gold, after.gold),
        ("food", before.food, after.food),
        ("town", (before.current_town, before.current_town_name), (after.current_town, after.current_town_name)),
        ("direction", before.direction, after.direction),
    ):
        if a != b:
            print(f"{label}: {a} -> {b}")

    for pa, pb in zip(before.characters, after.characters):
        changes: list[str] = []
        for label, a, b in (
            ("HP", (pa.cur_health, pa.max_health), (pb.cur_health, pb.max_health)),
            ("SP", (pa.cur_sp, pa.max_sp), (pb.cur_sp, pb.max_sp)),
            ("XP", pa.experience, pb.experience),
            ("skill points", pa.skill_points, pb.skill_points),
            ("level", pa.level, pb.level),
            ("graphic", pa.which_graphic, pb.which_graphic),
        ):
            if a != b:
                changes.append(f"{label}: {a} -> {b}")
        for idx, (a, b) in enumerate(zip(pa.skills, pb.skills)):
            if a != b:
                changes.append(f"{SKILL_NAMES[idx]}[{idx}]: {a} -> {b}")
        inv = inventory_diff(pa.inventory_names, pb.inventory_names)
        if inv:
            changes.append(inv)
        if changes:
            print(f"\nPC {pa.index}: {pa.name}")
            for change in changes:
                print(f"  {change}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
