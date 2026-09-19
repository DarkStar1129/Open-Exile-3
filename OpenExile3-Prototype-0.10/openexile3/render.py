from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .assets import (
    TERRAIN_CELL_H,
    TERRAIN_CELL_W,
    load_terrain_animation_frames,
    load_terrain_cells,
)
from .terrain import ANIM_PICTURE_BASE, load_terrain_definitions


class TerrainRenderer:
    def __init__(self, data_dir: Path, *, anim_frame: int = 0):
        self.data_dir = data_dir
        self.static = load_terrain_cells(data_dir)
        self.anim = load_terrain_animation_frames(data_dir)
        self.definitions = load_terrain_definitions(data_dir / "EXILE3.EXE")[2]
        self.anim_frame = anim_frame % 4

    def tile_image(self, terrain_id: int) -> Image.Image | None:
        definition = self.definitions[terrain_id]
        pic = definition.picture
        if 0 <= pic < len(self.static):
            return self.static[pic]
        if pic >= ANIM_PICTURE_BASE:
            slot = pic - ANIM_PICTURE_BASE
            if 0 <= slot < len(self.anim):
                return self.anim[slot][self.anim_frame]
        return None

    def render_grid(
        self,
        terrain: bytes,
        width: int,
        height: int,
        *,
        scale: int = 1,
        grid: bool = False,
    ) -> Image.Image:
        if len(terrain) < width * height:
            raise ValueError("Terrain buffer is smaller than the requested grid")
        canvas = Image.new(
            "RGB",
            (width * TERRAIN_CELL_W, height * TERRAIN_CELL_H),
            "black",
        )
        draw = ImageDraw.Draw(canvas)
        for y in range(height):
            for x in range(width):
                tid = terrain[y * width + x]
                px, py = x * TERRAIN_CELL_W, y * TERRAIN_CELL_H
                tile = self.tile_image(tid)
                if tile is None:
                    draw.rectangle(
                        (px, py, px + TERRAIN_CELL_W - 1, py + TERRAIN_CELL_H - 1),
                        fill=(32, 32, 32),
                    )
                    draw.text((px + 1, py + 1), str(tid), fill=(255, 255, 255))
                else:
                    canvas.paste(tile, (px, py))
                if grid:
                    draw.rectangle(
                        (px, py, px + TERRAIN_CELL_W - 1, py + TERRAIN_CELL_H - 1),
                        outline=(255, 0, 255),
                    )
        if scale != 1:
            canvas = canvas.resize(
                (canvas.width * scale, canvas.height * scale),
                Image.Resampling.NEAREST,
            )
        return canvas

    def render_viewport(
        self,
        terrain: bytes,
        map_width: int,
        map_height: int,
        *,
        center_x: int,
        center_y: int,
        view_width: int = 9,
        view_height: int = 9,
        scale: int = 1,
        grid: bool = False,
    ) -> Image.Image:
        x0 = center_x - view_width // 2
        y0 = center_y - view_height // 2
        buf = bytearray(view_width * view_height)
        for vy in range(view_height):
            for vx in range(view_width):
                x, y = x0 + vx, y0 + vy
                if 0 <= x < map_width and 0 <= y < map_height:
                    buf[vy * view_width + vx] = terrain[y * map_width + x]
                else:
                    buf[vy * view_width + vx] = 0
        return self.render_grid(bytes(buf), view_width, view_height, scale=scale, grid=grid)
