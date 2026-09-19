#!/usr/bin/env python3
from __future__ import annotations
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from openexile3.collision import load_collision_table
from openexile3.terrain import load_terrain_definitions
from openexile3.town import extract_current_town_creatures,extract_current_town_position,extract_current_town_terrain,tile

DIRS=(('N',0,-1),('NE',1,-1),('E',1,0),('SE',1,1),('S',0,1),('SW',-1,1),('W',-1,0),('NW',-1,-1))
ap=argparse.ArgumentParser(description='Check base movement around the current Exile III party position')
ap.add_argument('data_dir',type=Path);ap.add_argument('save',type=Path)
args=ap.parse_args();data=args.save.read_bytes();exe=args.data_dir/'EXILE3.EXE'
coll=load_collision_table(exe);defs=load_terrain_definitions(exe)[2];terr=extract_current_town_terrain(data);x,y=extract_current_town_position(data)
occupied={(c.x,c.y) for c in extract_current_town_creatures(data) if c.populated and c.active!=0}
print(f'party ({x},{y})')
for name,dx,dy in DIRS:
    nx,ny=x+dx,y+dy
    if not (0<=nx<64 and 0<=ny<64): print(f'{name:>2} ({nx:2d},{ny:2d}) OUT OF BOUNDS'); continue
    tid=tile(terr,nx,ny);d=defs[tid];blocked=coll.blocks_party(tid);occ=(nx,ny) in occupied
    reason=[]
    if blocked: reason.append(coll.blocking_name(tid))
    if occ: reason.append('creature')
    print(f'{name:>2} ({nx:2d},{ny:2d}) tid={tid:3d} {d.name:26s} {"BLOCKED" if reason else "OPEN":7s} {", ".join(reason)}')
