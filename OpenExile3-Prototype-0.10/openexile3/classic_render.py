from __future__ import annotations

from pathlib import Path
from typing import Callable
from PIL import Image

from .assets import TERRAIN_CELL_H as H, TERRAIN_CELL_W as W
from .collision import load_collision_table, CollisionTable
from .location import extract_outdoor_location
from .outdoor import build_working_map, load_outdoor, working_tile
from .render import TerrainRenderer
from .save import parse_save_bytes, extract_outdoor_info, outdoor_info_at
from .sprites import load_monster_sprite, load_pc_sprite
from .visibility import has_line_of_sight
from .town import (
    active_tile,
    extract_current_town_creatures,
    extract_current_town_position,
    extract_current_town_terrain,
    locate_active_town_map,
)

# Classic Windows Exile/Blades trim rectangles before the original +61,+37
# source offset into MIXED.BMP.
_TRIM_RECTS = (
    (0,0,28,5), (0,31,28,36), (0,0,5,36), (24,0,28,36),
    (0,0,5,5), (24,0,28,5), (24,31,28,36), (0,31,5,36),
)

FLUID_TERRAIN_IDS = frozenset((71,72,73,74,75,76,90))
ROAD_PICTURES = frozenset((202,203,204))
ROAD_EXTEND_PICTURES = frozenset((
    61,62,63,64,65,66,401,402,406,202,203,204,215,216,90,91,92,93,
    102,103,104,105,112,113,114,115,187,188,189,190,192,193,194,195,
    196,197,191,200,201,
))


def _is_fluid(tid: int) -> bool:
    return tid in FLUID_TERRAIN_IDS


def _is_shore(tid: int) -> bool:
    return not _is_fluid(tid) and tid not in (77,90)


def _is_wall_picture(pic: int) -> bool:
    return 88 <= pic <= 120


def _is_ground_picture(pic: int) -> bool:
    return ((0 <= pic <= 87) or (121 <= pic <= 122) or
            (179 <= pic <= 208) or (211 <= pic <= 212) or
            (215 <= pic <= 246))


def _is_nature_picture(pic: int) -> bool:
    return ((0 <= pic <= 45) or (67 <= pic <= 73) or (75 <= pic <= 87) or
            (121 <= pic <= 122) or (179 <= pic <= 208) or
            (211 <= pic <= 212) or (217 <= pic <= 246))


def _rgba_colorkey(im: Image.Image, key=(255,255,255)) -> Image.Image:
    src = im.convert("RGBA")
    px = src.load()
    for y in range(src.height):
        for x in range(src.width):
            r,g,b,a = px[x,y]
            if (r,g,b) == key:
                px[x,y] = (r,g,b,0)
    return src


def _paste_colorkey(dst: Image.Image, src: Image.Image, xy: tuple[int,int]) -> None:
    if src.mode != "RGBA":
        src = _rgba_colorkey(src)
    dst.paste(src, xy, src)


def clamp_camera_center(cx:int, cy:int, map_w:int, map_h:int, view_width:int, view_height:int) -> tuple[int,int]:
    """Shift a camera inward so the viewport stays on-map when possible."""
    left=view_width//2; right=view_width-1-left
    top=view_height//2; bottom=view_height-1-top
    if view_width <= map_w:
        cx=min(map_w-1-right,max(left,cx))
    else:
        cx=map_w//2
    if view_height <= map_h:
        cy=min(map_h-1-bottom,max(top,cy))
    else:
        cy=map_h//2
    return cx,cy


class _ClassicMapRenderer:
    def __init__(self, data_dir: Path, *, anim_frame: int = 2):
        self.data_dir = Path(data_dir)
        self.terrain = TerrainRenderer(self.data_dir, anim_frame=anim_frame)
        self.collision = load_collision_table(self.data_dir / "EXILE3.EXE")
        with Image.open(self.data_dir / "MIXED.BMP") as src:
            self.mixed = src.convert("RGB")
        with Image.open(self.data_dir / "FIELDS.BMP") as src:
            self.fields = src.convert("RGB")

    def _forced_picture(self, picture: int) -> Image.Image | None:
        if not 0 <= picture < len(self.terrain.static):
            return None
        return self.terrain.static[picture]

    def _walkway_picture(self, tile_at, map_w:int, map_h:int, x:int,y:int,tid:int) -> int | None:
        if tid not in (245,246):
            return None
        def nat(nx:int, ny:int) -> bool:
            if not (0 <= nx < map_w and 0 <= ny < map_h):
                return False
            nt = tile_at(nx,ny)
            return _is_nature_picture(self.terrain.definitions[nt].picture)
        left,right,up,down = nat(x-1,y),nat(x+1,y),nat(x,y-1),nat(x,y+1)
        # Exile III uses pictures 218..225 as rounded walkway corner variants.
        if left and up: return 219
        if right and up: return 220
        if right and down: return 221
        if left and down: return 218
        return None

    def _trim_source(self, which_trim: int, mode: int, *, grass_wall: bool=False) -> tuple[Image.Image, tuple[int,int]]:
        l,t,r,b = _TRIM_RECTS[mode]
        sx0 = 61 + 28*which_trim + l
        sy0 = 37 + t + (36 if grass_wall and which_trim == 3 else 0)
        sx1 = 61 + 28*which_trim + r
        sy1 = 37 + b + (36 if grass_wall and which_trim == 3 else 0)
        return self.mixed.crop((sx0,sy0,sx1,sy1)), (l,t)

    def _draw_trim(self, canvas: Image.Image, vx:int, vy:int, which_trim:int, mode:int,
                   *, current_ground:int=0) -> None:
        if current_ground == 2 and which_trim < 3:
            return
        crop, (dx,dy) = self._trim_source(which_trim, mode,
                                           grass_wall=(current_ground==2))
        _paste_colorkey(canvas, crop, (vx*W+dx,vy*H+dy))

    def _fluid_trim_mask(self, tile_at, map_w:int,map_h:int,x:int,y:int,tid:int) -> int:
        if not _is_fluid(tid): return 0
        bits=0
        checks=((x,y-1,1),(x+1,y-1,2),(x+1,y,4),(x+1,y+1,8),
                (x,y+1,16),(x-1,y+1,32),(x-1,y,64),(x-1,y-1,128))
        for nx,ny,bit in checks:
            if 0<=nx<map_w and 0<=ny<map_h and _is_shore(tile_at(nx,ny)):
                bits |= bit
        # Exact cleanup used by the classic renderer.
        if bits & 1: bits &= 125
        if bits & 4: bits &= 245
        if bits & 10: bits &= 215
        if bits & 64: bits &= 95
        return bits

    def _place_trim(self, canvas:Image.Image, tile_at, map_w:int,map_h:int,
                    wx:int,wy:int,vx:int,vy:int,tid:int) -> None:
        bits=self._fluid_trim_mask(tile_at,map_w,map_h,wx,wy,tid)
        mapping=((1,1,0),(2,2,5),(4,0,3),(8,2,6),(16,1,1),(32,2,7),(64,0,2),(128,2,4))
        for bit,which,mode in mapping:
            if bits & bit:
                self._draw_trim(canvas,vx,vy,which,mode)

        pic=self.terrain.definitions[tid].picture
        if not _is_wall_picture(pic) or wx<=0 or wy<=0 or wx>=map_w-1 or wy>=map_h-1:
            return
        ids=(tile_at(wx-1,wy),tile_at(wx,wy-1),tile_at(wx+1,wy),tile_at(wx,wy+1))
        pics=tuple(self.terrain.definitions[i].picture for i in ids)
        L,U,R,D=(_is_wall_picture(p) for p in pics)
        gL,gU,gR,gD=(_is_ground_picture(p) for p in pics)
        ground2 = any(p == 2 for p in pics)
        cg=2 if ground2 else 0
        if L and U and gR and gD: self._draw_trim(canvas,vx,vy,3,6,current_ground=cg)
        if L and D and gR and gU: self._draw_trim(canvas,vx,vy,3,5,current_ground=cg)
        if R and U and gL and gD: self._draw_trim(canvas,vx,vy,3,7,current_ground=cg)
        if R and D and gL and gU: self._draw_trim(canvas,vx,vy,3,4,current_ground=cg)
        if gL and gU and gR and D:
            self._draw_trim(canvas,vx,vy,3,4,current_ground=cg); self._draw_trim(canvas,vx,vy,3,5,current_ground=cg)
        if L and gD and gR and gU:
            self._draw_trim(canvas,vx,vy,3,5,current_ground=cg); self._draw_trim(canvas,vx,vy,3,6,current_ground=cg)
        if gR and U and gL and gD:
            self._draw_trim(canvas,vx,vy,3,6,current_ground=cg); self._draw_trim(canvas,vx,vy,3,7,current_ground=cg)
        if R and gD and gL and gU:
            self._draw_trim(canvas,vx,vy,3,4,current_ground=cg); self._draw_trim(canvas,vx,vy,3,7,current_ground=cg)

    def _road_extend(self, tid:int) -> bool:
        return self.terrain.definitions[tid].picture in ROAD_EXTEND_PICTURES

    def _draw_road_piece(self, canvas:Image.Image, src_box:tuple[int,int,int,int],
                         dst_xy:tuple[int,int]) -> None:
        _paste_colorkey(canvas, self.fields.crop(src_box), dst_xy)

    def _place_road(self, canvas:Image.Image, tile_at, map_w:int,map_h:int,
                    wx:int,wy:int,vx:int,vy:int,tid:int) -> None:
        if self.terrain.definitions[tid].picture not in ROAD_PICTURES:
            return
        # Source/destination rectangles from the classic Windows renderer.
        horiz=(112,76,125,80)  # 13x4
        vert=(144,72,148,90)   # 4x18
        base_x=vx*W; base_y=vy*H
        neighbors=(
            (wx,wy-1,vert,(base_x+12,base_y+0)),
            (wx+1,wy,horiz,(base_x+15,base_y+16)),
            (wx,wy+1,vert,(base_x+12,base_y+18)),
            (wx-1,wy,horiz,(base_x+0,base_y+16)),
        )
        for nx,ny,src,dst in neighbors:
            if not (0<=nx<map_w and 0<=ny<map_h) or self._road_extend(tile_at(nx,ny)):
                self._draw_road_piece(canvas,src,dst)

    def _render_base(self, tile_at, map_w:int,map_h:int,cx:int,cy:int,
                     view_width:int,view_height:int, *, roads:bool=True) -> tuple[Image.Image,int,int]:
        canvas=Image.new("RGB",(view_width*W,view_height*H),(0,0,0))
        x0=cx-view_width//2; y0=cy-view_height//2
        for vy in range(view_height):
            for vx in range(view_width):
                wx,wy=x0+vx,y0+vy
                if not (0<=wx<map_w and 0<=wy<map_h): continue
                tid=tile_at(wx,wy)
                forced=self._walkway_picture(tile_at,map_w,map_h,wx,wy,tid)
                img=self._forced_picture(forced) if forced is not None else self.terrain.tile_image(tid)
                if img is not None: canvas.paste(img,(vx*W,vy*H))
        for vy in range(view_height):
            for vx in range(view_width):
                wx,wy=x0+vx,y0+vy
                if 0<=wx<map_w and 0<=wy<map_h:
                    tid=tile_at(wx,wy)
                    if roads:
                        self._place_road(canvas,tile_at,map_w,map_h,wx,wy,vx,vy,tid)
                    self._place_trim(canvas,tile_at,map_w,map_h,wx,wy,vx,vy,tid)
        return canvas,x0,y0


class ClassicTownRenderer(_ClassicMapRenderer):
    """Classic Exile III town renderer reconstructed from original assets."""

    def detect_active_size(self, save_data:bytes) -> int:
        live=extract_current_town_terrain(save_data)
        match=locate_active_town_map((self.data_dir/"TOWN.DAT").read_bytes(),live)
        return match.size

    def render_from_save(self, save_data:bytes, *, view_width:int=9,view_height:int=9,
                         draw_npcs:bool=True,draw_party:bool=True,scale:int=1,
                         camera_center:tuple[int,int] | None=None, line_of_sight:bool=True,
                         active_size:int | None=None,
                         party_position:tuple[int,int] | None=None,
                         party_direction:int | None=None,
                         clamp_camera:bool=False) -> Image.Image:
        terrain=extract_current_town_terrain(save_data)
        saved_party=extract_current_town_position(save_data)
        party_x,party_y=party_position if party_position is not None else saved_party
        cx,cy=camera_center if camera_center is not None else (party_x,party_y)
        size=active_size or self.detect_active_size(save_data)
        if clamp_camera:
            cx,cy=clamp_camera_center(cx,cy,size,size,view_width,view_height)
        tile_at=lambda x,y: active_tile(terrain,x,y,size)
        canvas,x0,y0=self._render_base(tile_at,size,size,cx,cy,view_width,view_height)

        if draw_npcs:
            for c in extract_current_town_creatures(save_data):
                if c.active == 0 or not c.populated: continue
                vx,vy=c.x-x0,c.y-y0
                if not (0<=vx<view_width and 0<=vy<view_height):
                    continue
                if line_of_sight and not has_line_of_sight(tile_at,self.collision,(party_x,party_y),(c.x,c.y),size,size):
                    continue
                # 0.7 generalizes composition for the live record's width/height.
                for part in range(max(1,c.width*c.height)):
                    spr=load_monster_sprite(self.data_dir,c.monster_id,c.direction,part=part)
                    if spr is None: continue
                    px=part % max(1,c.width); py=part // max(1,c.width)
                    _paste_colorkey(canvas,spr,((vx+px)*W,(vy+py)*H))
        if draw_party:
            summary=parse_save_bytes(save_data)
            first=next((pc for pc in summary.characters if pc.main_status>0),None)
            if first is not None:
                facing=summary.direction if party_direction is None else party_direction
                spr=load_pc_sprite(self.data_dir,first.which_graphic,facing)
                if spr is not None:
                    pvx,pvy=party_x-x0,party_y-y0
                    if 0<=pvx<view_width and 0<=pvy<view_height:
                        _paste_colorkey(canvas,spr,(pvx*W,pvy*H))
        if scale != 1:
            canvas=canvas.resize((canvas.width*scale,canvas.height*scale),Image.Resampling.NEAREST)
        return canvas


class ClassicOutdoorRenderer(_ClassicMapRenderer):
    """Render the 96x96 four-sector outdoor working map used by Exile III."""

    def __init__(self, data_dir: Path, *, anim_frame: int = 2):
        super().__init__(data_dir, anim_frame=anim_frame)
        self._sectors = load_outdoor(self.data_dir / "OUTDOOR.DAT")
        self._working_cache: dict[tuple[int,int], bytes] = {}

    def render_from_save(self, save_data:bytes, *, view_width:int=9,view_height:int=9,
                         draw_party:bool=True,scale:int=1,
                         camera_center:tuple[int,int] | None=None,
                         party_position:tuple[int,int] | None=None,
                         party_direction:int | None=None,
                         apply_saved_visibility:bool=True,
                         outdoor_corner:tuple[int,int] | None=None,
                         visibility_info:bytes | bytearray | None=None,
                         clamp_camera:bool=False) -> Image.Image:
        loc=extract_outdoor_location(save_data)
        corner=outdoor_corner if outdoor_corner is not None else (loc.corner_x,loc.corner_y)
        key=corner
        terrain=self._working_cache.get(key)
        if terrain is None:
            terrain=build_working_map(self._sectors,corner[0],corner[1])
            self._working_cache[key]=terrain
        tile_at=lambda x,y: working_tile(terrain,x,y)
        party_x,party_y=party_position if party_position is not None else (loc.working_x,loc.working_y)
        cx,cy=camera_center if camera_center is not None else (party_x,party_y)
        if clamp_camera:
            cx,cy=clamp_camera_center(cx,cy,96,96,view_width,view_height)
        canvas,x0,y0=self._render_base(tile_at,96,96,cx,cy,view_width,view_height)
        # OUT_INFO is the original 96x96 x-major explored/visibility map.
        # A sandbox may supply its mutable visibility window after sector shifts.
        if apply_saved_visibility:
            info=visibility_info if visibility_info is not None else extract_outdoor_info(save_data)
            if len(info) != 96*96:
                raise ValueError("Expected a 96x96 outdoor visibility buffer")
            for vy in range(view_height):
                for vx in range(view_width):
                    wx,wy=x0+vx,y0+vy
                    if not (0<=wx<96 and 0<=wy<96) or outdoor_info_at(info,wx,wy) == 0:
                        canvas.paste((0,0,0),(vx*W,vy*H,(vx+1)*W,(vy+1)*H))
        if draw_party:
            summary=parse_save_bytes(save_data)
            first=next((pc for pc in summary.characters if pc.main_status>0),None)
            if first is not None:
                facing=summary.direction if party_direction is None else party_direction
                spr=load_pc_sprite(self.data_dir,first.which_graphic,facing)
                if spr is not None:
                    pvx,pvy=party_x-x0,party_y-y0
                    if 0<=pvx<view_width and 0<=pvy<view_height:
                        _paste_colorkey(canvas,spr,(pvx*W,pvy*H))
        if scale != 1:
            canvas=canvas.resize((canvas.width*scale,canvas.height*scale),Image.Resampling.NEAREST)
        return canvas
