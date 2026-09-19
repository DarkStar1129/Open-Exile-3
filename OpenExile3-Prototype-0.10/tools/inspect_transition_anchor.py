#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openexile3.save import parse_save
from openexile3.transitions import retained_town_entrance

ap = argparse.ArgumentParser(description="Resolve a town save's retained outdoor entrance anchor")
ap.add_argument("data_dir", type=Path)
ap.add_argument("save", type=Path)
args = ap.parse_args()
D = args.data_dir.expanduser().resolve()
S = args.save.expanduser().resolve()
data = S.read_bytes()
summary = parse_save(S, exe_path=D / "EXILE3.EXE")
anchor = retained_town_entrance(D, data)
print(f"Town: #{summary.current_town} {summary.current_town_name or ''}".rstrip())
if anchor is None:
    raise SystemExit("No exact retained outdoor entrance matched the current town")
print(f"Entrance sector: ({anchor.sector_x},{anchor.sector_y}), record {anchor.sector_index}")
print(f"Region: {anchor.region_label}")
print(f"Local entrance: ({anchor.local_x},{anchor.local_y})")
print(f"World tile: {anchor.world_position}")
if anchor.resource_difficulty is not None:
    print(f"Resource difficulty: {anchor.resource_difficulty}")
