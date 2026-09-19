#!/usr/bin/env python3
"""Native scalable Exile III town viewer.

Reads the real Exile III save and assets, centers on the decoded party position,
renders classic shoreline/wall trim and live NPCs, and can show a much larger
field of view than the original 9x9 Windows viewport.
"""
from __future__ import annotations
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from openexile3.assets import TERRAIN_CELL_H,TERRAIN_CELL_W
from openexile3.classic_render import ClassicTownRenderer
from openexile3.town import extract_current_town_position,extract_current_town_name

def main()->int:
    try: import pygame
    except ImportError:
        print('pygame is required. In a venv: python -m pip install pygame');return 2
    ap=argparse.ArgumentParser()
    ap.add_argument('data_dir',type=Path);ap.add_argument('save',type=Path)
    ap.add_argument('--width',type=int,default=1600);ap.add_argument('--height',type=int,default=1000)
    ap.add_argument('--zoom',type=int,default=2)
    args=ap.parse_args();data=args.save.read_bytes();party=extract_current_town_position(data);name=extract_current_town_name(data)
    pygame.init();screen=pygame.display.set_mode((args.width,args.height),pygame.RESIZABLE);pygame.display.set_caption(f'OpenExile3 0.7 - {name}')
    font=pygame.font.Font(None,24);clock=pygame.time.Clock();zoom=max(1,args.zoom);cam=list(party);show_grid=False;running=True;last_key=None;last_frame=-1
    cache=None;cache_key=None
    def pil_surface(im): return pygame.image.fromstring(im.convert('RGB').tobytes(),im.size,'RGB')
    while running:
        for e in pygame.event.get():
            if e.type==pygame.QUIT: running=False
            elif e.type==pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE,pygame.K_q):running=False
                elif e.key in (pygame.K_LEFT,pygame.K_a):cam[0]=max(0,cam[0]-1)
                elif e.key in (pygame.K_RIGHT,pygame.K_d):cam[0]=min(63,cam[0]+1)
                elif e.key in (pygame.K_UP,pygame.K_w):cam[1]=max(0,cam[1]-1)
                elif e.key in (pygame.K_DOWN,pygame.K_s):cam[1]=min(63,cam[1]+1)
                elif e.key==pygame.K_HOME:cam[:]=party
                elif e.key in (pygame.K_EQUALS,pygame.K_PLUS,pygame.K_KP_PLUS):zoom=min(6,zoom+1)
                elif e.key in (pygame.K_MINUS,pygame.K_KP_MINUS):zoom=max(1,zoom-1)
                elif e.key==pygame.K_F11:pygame.display.toggle_fullscreen()
                elif e.key==pygame.K_g:show_grid=not show_grid
                cache_key=None
        w,h=screen.get_size();tilew,tileh=TERRAIN_CELL_W*zoom,TERRAIN_CELL_H*zoom
        cols=max(3,(w//tilew)|1);rows=max(3,(h//tileh)|1);frame=(pygame.time.get_ticks()//180)%4
        key=(tuple(cam),zoom,cols,rows,frame,w,h)
        if key!=cache_key:
            rend=ClassicTownRenderer(args.data_dir,anim_frame=frame)
            im=rend.render_from_save(data,view_width=cols,view_height=rows,scale=zoom,camera_center=tuple(cam))
            cache=pil_surface(im);cache_key=key
        screen.fill((0,0,0));screen.blit(cache,((w-cache.get_width())//2,(h-cache.get_height())//2))
        hud=f'{name}  party={party} camera={tuple(cam)}  {cols}x{rows} tiles  zoom={zoom}x | WASD/arrows pan  Home party  +/- zoom  F11 fullscreen  Q quit'
        t=font.render(hud,True,(255,255,255));bg=pygame.Surface((t.get_width()+12,t.get_height()+8),pygame.SRCALPHA);bg.fill((0,0,0,180));screen.blit(bg,(6,6));screen.blit(t,(12,10))
        pygame.display.flip();clock.tick(60)
    pygame.quit();return 0
if __name__=='__main__':raise SystemExit(main())
