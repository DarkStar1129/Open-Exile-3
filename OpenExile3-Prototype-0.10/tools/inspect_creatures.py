#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from openexile3.sprites import monster_name, monster_picture_for_id
from openexile3.town import extract_current_town_creatures

ap=argparse.ArgumentParser(description='Inspect current-town live creature records')
ap.add_argument('data_dir',type=Path); ap.add_argument('save',type=Path)
args=ap.parse_args(); data=args.save.read_bytes(); exe=args.data_dir/'EXILE3.EXE'
creatures=extract_current_town_creatures(data)
print(f'populated: {sum(c.populated for c in creatures)} / 60')
print(f'active:    {sum(c.populated and c.active != 0 for c in creatures)} / 60')
for c in creatures:
    if not c.populated: continue
    print(f'{c.slot:02d} active={c.active:2d} id={c.monster_id:3d} {monster_name(exe,c.monster_id):20s} '
          f'xy=({c.x:2d},{c.y:2d}) dir={c.direction} lvl={c.level:2d} hp={c.health}/{c.max_health} pic={monster_picture_for_id(c.monster_id)}')
