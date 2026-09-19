#!/usr/bin/env python3
"""Simulate a sequence of Exile III moves in memory without touching the save."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from openexile3.location import SaveMode
from openexile3.movement import DIRECTION_NAMES,MovementSandbox

MOVES={
    'N':(0,-1),'NE':(1,-1),'E':(1,0),'SE':(1,1),
    'S':(0,1),'SW':(-1,1),'W':(-1,0),'NW':(-1,-1),
}


def parse_moves(text:str) -> list[str]:
    normalized=text.replace(',',' ').replace(';',' ').upper().split()
    out=[]
    for tok in normalized:
        # Compact cardinal strings like "SSEN" are convenient, but preserve
        # explicit diagonal tokens such as NE/SE/SW/NW.
        if tok in MOVES:
            out.append(tok)
        elif tok and all(c in 'NSEW' for c in tok):
            out.extend(tok)
        else:
            raise ValueError(f'Unknown move token: {tok}')
    return out


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('data_dir',type=Path)
    ap.add_argument('save',type=Path)
    ap.add_argument('moves',help='e.g. "S S E NE" or compact cardinal string "SSEN"')
    args=ap.parse_args()
    sand=MovementSandbox(args.data_dir,args.save.read_bytes())
    print(f'mode={sand.mode.value} start={sand.position} facing={sand.direction}')
    if sand.mode is SaveMode.OUTDOOR:
        print(f'corner={sand.outdoor_corner} sector={sand.outdoor_sector} local={sand.outdoor_local_position} world={sand.outdoor_world_position} region={sand.region_label!r}')
    for i,name in enumerate(parse_moves(args.moves),1):
        dx,dy=MOVES[name]
        r=sand.attempt(dx,dy)
        extra=[]
        if r.shifted: extra.append('shift='+ '+'.join(r.shifted))
        if r.town_exit is not None: extra.append(f'town_exit={r.town_exit}')
        if sand.mode is SaveMode.OUTDOOR:
            extra.extend((f'corner={sand.outdoor_corner}',f'sector={sand.outdoor_sector}',f'local={sand.outdoor_local_position}',f'world={sand.outdoor_world_position}',f'region={sand.region_label!r}'))
        status='MOVED' if r.moved else 'BLOCKED'
        print(f'{i:02d} {name:<2} {status:<7} {r.source}->{r.destination} reason={r.reason} terrain={r.terrain_id} block={r.blocking_code} ' + ' '.join(extra))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
