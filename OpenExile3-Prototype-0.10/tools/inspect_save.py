#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from openexile3.save import parse_save, extract_town_resource_difficulty


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect an Exile III Windows save (read-only).")
    parser.add_argument("save", type=Path)
    parser.add_argument("--exe", type=Path, help="EXILE3.EXE, used to resolve town names")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = parse_save(args.save, exe_path=args.exe)
    if args.json:
        obj = asdict(summary)
        obj["path"] = str(obj["path"])
        print(json.dumps(obj, indent=2))
        return

    print(f"File: {summary.path}")
    print(f"Size: {summary.size:,} bytes")
    print(f"Header: {summary.header_hex}")
    print(f"Age/ticks: {summary.age}")
    print(f"Day: {summary.day}")
    print(f"Gold: {summary.gold}")
    print(f"Food: {summary.food}")
    print(f"Party direction: {summary.direction}")
    town = str(summary.current_town)
    if summary.current_town_name:
        town += f" ({summary.current_town_name})"
    print(f"Current town: {town}")
    print(f"Current town difficulty in save: {summary.current_town_difficulty}")
    if args.exe:
        rd = extract_town_resource_difficulty(args.exe, summary.current_town)
        if rd is not None:
            print(f"Town difficulty in EXE resources: {rd}")
    print("Characters:")
    for pc in summary.characters:
        print(
            f"  {pc.index}. {pc.name}: HP {pc.cur_health}/{pc.max_health}, "
            f"SP {pc.cur_sp}/{pc.max_sp}, level {pc.level}, XP {pc.experience}, graphic {pc.which_graphic}"
        )
        if pc.inventory_names:
            print("     Inventory: " + ", ".join(pc.inventory_names))


if __name__ == "__main__":
    main()
