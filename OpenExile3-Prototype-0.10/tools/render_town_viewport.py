#!/usr/bin/env python3
from __future__ import annotations
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from openexile3.classic_render import ClassicTownRenderer
from openexile3.town import extract_current_town_position

def main()->int:
    ap=argparse.ArgumentParser(description='Render a classic Exile III town viewport from a Windows save')
    ap.add_argument('data_dir',type=Path);ap.add_argument('save',type=Path)
    ap.add_argument('--center-x',type=int);ap.add_argument('--center-y',type=int);ap.add_argument('--width',type=int,default=9);ap.add_argument('--height',type=int,default=9)
    ap.add_argument('--anim-frame',type=int,default=2,choices=range(4));ap.add_argument('--scale',type=int,default=1,choices=range(1,9));ap.add_argument('--output',type=Path,default=Path('town-viewport.png'))
    args=ap.parse_args();data=args.save.read_bytes();center=extract_current_town_position(data)
    if args.center_x is not None or args.center_y is not None:center=(args.center_x if args.center_x is not None else center[0],args.center_y if args.center_y is not None else center[1])
    r=ClassicTownRenderer(args.data_dir,anim_frame=args.anim_frame);im=r.render_from_save(data,view_width=args.width,view_height=args.height,scale=args.scale,camera_center=center)
    args.output.parent.mkdir(parents=True,exist_ok=True);im.save(args.output);print(f'Wrote {args.output} ({im.width}x{im.height}) centered at {center}');return 0
if __name__=='__main__':raise SystemExit(main())
