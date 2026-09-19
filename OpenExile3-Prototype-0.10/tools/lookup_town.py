#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from openexile3.ne import decode_win16_string_resources
from openexile3.outdoor import load_outdoor
from openexile3.save import TOWN_STRING_BASE,TOWN_STRING_STRIDE

ap=argparse.ArgumentParser(description='Look up Exile III town numbers and outdoor entrances by name')
ap.add_argument('data_dir',type=Path)
ap.add_argument('query',help='Town name substring, case-insensitive')
args=ap.parse_args()
D=args.data_dir.expanduser().resolve(); q=args.query.casefold()
strings=decode_win16_string_resources(D/'EXILE3.EXE')
sectors=load_outdoor(D/'OUTDOOR.DAT')
found=[]
for town in range(200):
    name=strings.get(TOWN_STRING_BASE+town*TOWN_STRING_STRIDE,'').strip()
    if name and q in name.casefold():
        difficulty=strings.get(TOWN_STRING_BASE+town*TOWN_STRING_STRIDE+1,'').strip()
        entrances=[]
        for sec in sectors:
            for ex in sec.exits:
                if ex.town==town:
                    entrances.append((sec.world_x,sec.world_y,sec.index,sec.region_label,ex.x,ex.y))
        found.append((town,name,difficulty,entrances))
if not found:
    raise SystemExit(f'No town name matched {args.query!r}')
for town,name,difficulty,entrances in found:
    print(f'Town #{town}: {name}')
    if difficulty: print(f'  resource difficulty: {difficulty}')
    if entrances:
        for sx,sy,idx,region,x,y in entrances:
            print(f'  entrance: sector ({sx},{sy}) record {idx}, local ({x},{y}), region {region!r}')
    else:
        print('  outdoor entrance: none found in OUTDOOR.DAT')
