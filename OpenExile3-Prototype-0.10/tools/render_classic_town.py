#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from openexile3.classic_render import ClassicTownRenderer

ap=argparse.ArgumentParser(description='Render an Exile III current-town save with classic frills, party and NPCs')
ap.add_argument('data_dir',type=Path)
ap.add_argument('save',type=Path)
ap.add_argument('--output',type=Path,default=Path('current-town.png'))
ap.add_argument('--width',type=int,default=9,help='viewport width in tiles')
ap.add_argument('--height',type=int,default=9,help='viewport height in tiles')
ap.add_argument('--scale',type=int,default=1)
ap.add_argument('--anim-frame',type=int,default=2,choices=range(4))
ap.add_argument('--no-npcs',action='store_true')
ap.add_argument('--no-party',action='store_true')
args=ap.parse_args()
save=args.save.read_bytes()
r=ClassicTownRenderer(args.data_dir,anim_frame=args.anim_frame)
im=r.render_from_save(save,view_width=args.width,view_height=args.height,scale=args.scale,
                      draw_npcs=not args.no_npcs,draw_party=not args.no_party)
args.output.parent.mkdir(parents=True,exist_ok=True); im.save(args.output)
print(f'Wrote {args.output} ({im.width}x{im.height})')
