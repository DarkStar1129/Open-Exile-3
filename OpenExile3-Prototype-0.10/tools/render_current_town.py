#!/usr/bin/env python3
from __future__ import annotations
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from openexile3.classic_render import ClassicTownRenderer

def main()->int:
    ap=argparse.ArgumentParser(description='Render the full live 64x64 current town with classic Exile III layers')
    ap.add_argument('data_dir',type=Path);ap.add_argument('save',type=Path)
    ap.add_argument('--anim-frame',type=int,default=2,choices=range(4));ap.add_argument('--scale',type=int,default=1,choices=range(1,5))
    ap.add_argument('--output',type=Path,default=Path('current-town.png'));ap.add_argument('--no-npcs',action='store_true');ap.add_argument('--no-party',action='store_true')
    args=ap.parse_args();data=args.save.read_bytes();r=ClassicTownRenderer(args.data_dir,anim_frame=args.anim_frame)
    # For an even 64x64 view, center (32,32) yields top-left (0,0).
    im=r.render_from_save(data,view_width=64,view_height=64,scale=args.scale,camera_center=(32,32),draw_npcs=not args.no_npcs,draw_party=not args.no_party)
    args.output.parent.mkdir(parents=True,exist_ok=True);im.save(args.output);print(f'Wrote {args.output} ({im.width}x{im.height})');return 0
if __name__=='__main__':raise SystemExit(main())
