#!/usr/bin/env python3
from __future__ import annotations
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from openexile3.classic_render import ClassicTownRenderer,ClassicOutdoorRenderer
from openexile3.location import save_mode,SaveMode

ap=argparse.ArgumentParser(description='Render an Exile III save, automatically selecting town or outdoor mode')
ap.add_argument('data_dir',type=Path)
ap.add_argument('save',type=Path)
ap.add_argument('--output',type=Path,default=Path('openexile3-location.png'))
ap.add_argument('--width',type=int,default=9)
ap.add_argument('--height',type=int,default=9)
ap.add_argument('--scale',type=int,default=1)
ap.add_argument('--anim-frame',type=int,default=2,choices=range(4))
ap.add_argument('--no-party',action='store_true')
ap.add_argument('--no-npcs',action='store_true')
ap.add_argument('--no-los',action='store_true')
ap.add_argument('--clamp-camera',action='store_true',help='shift wide views inward at map edges instead of centering exactly on the party')
args=ap.parse_args(); data=args.save.read_bytes(); mode,_=save_mode(data)
if mode is SaveMode.TOWN:
    r=ClassicTownRenderer(args.data_dir,anim_frame=args.anim_frame)
    im=r.render_from_save(data,view_width=args.width,view_height=args.height,scale=args.scale,
                          draw_party=not args.no_party,draw_npcs=not args.no_npcs,
                          line_of_sight=not args.no_los,clamp_camera=args.clamp_camera)
elif mode is SaveMode.OUTDOOR:
    r=ClassicOutdoorRenderer(args.data_dir,anim_frame=args.anim_frame)
    im=r.render_from_save(data,view_width=args.width,view_height=args.height,scale=args.scale,
                          draw_party=not args.no_party,clamp_camera=args.clamp_camera)
else:
    raise SystemExit('Unknown Exile III save mode flag')
args.output.parent.mkdir(parents=True,exist_ok=True);im.save(args.output)
print(f'Wrote {args.output} ({im.width}x{im.height}) [{mode.value}]')
