#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from openexile3.collision import load_collision_table
from openexile3.terrain import load_terrain_definitions

ap=argparse.ArgumentParser(description='Inspect Exile III native terrain collision table')
ap.add_argument('data_dir',type=Path)
ap.add_argument('terrain_ids',nargs='*',type=int)
args=ap.parse_args()
exe=args.data_dir/'EXILE3.EXE'
table=load_collision_table(exe); defs=load_terrain_definitions(exe)[2]
print(f'collision table offset: 0x{table.file_offset:X} ({table.file_offset})')
ids=args.terrain_ids or [5,7,71,75,77,90,100,102,124,125,245,246]
for tid in ids:
    d=defs[tid]
    print(f'{tid:3d}  {d.name:32s} picture={d.picture:3d}  code={table.blocking_code(tid)}  {table.blocking_name(tid)}')
