#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openexile3.assets import load_terrain_animation_frames, load_terrain_cells
from openexile3.outdoor import (
    OUTDOOR_GRID_H,
    OUTDOOR_GRID_W,
    WORLD_SECTORS_H,
    WORLD_SECTORS_W,
    SURFACE_SECTORS_W,
    load_outdoor,
)
from openexile3.terrain import ANIM_PICTURE_BASE, load_terrain_definitions


def main() -> int:
    ap = argparse.ArgumentParser(description="Render an overview of Exile III outdoor sectors")
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--tile-width", type=int, default=7)
    ap.add_argument("--tile-height", type=int, default=9)
    ap.add_argument("--anim-frame", type=int, default=0, choices=range(4))
    ap.add_argument("--surface-only", action="store_true", help="render the contiguous 7x10 Valorim surface columns only")
    ap.add_argument("--output", type=Path, default=Path("outdoor-overview.png"))
    args = ap.parse_args()

    if args.tile_width < 1 or args.tile_height < 1:
        raise SystemExit("tile dimensions must be >= 1")

    d = args.data_dir.expanduser().resolve()
    static_cells = load_terrain_cells(d)
    anim_slots = load_terrain_animation_frames(d)
    _off, _sid, definitions = load_terrain_definitions(d / "EXILE3.EXE")
    sectors = load_outdoor(d / "OUTDOOR.DAT")

    cache: dict[int, Image.Image] = {}
    for tid, definition in enumerate(definitions):
        pic = definition.picture
        src = None
        if 0 <= pic < len(static_cells):
            src = static_cells[pic]
        elif pic >= ANIM_PICTURE_BASE:
            slot = pic - ANIM_PICTURE_BASE
            if 0 <= slot < len(anim_slots):
                src = anim_slots[slot][args.anim_frame]
        if src is not None:
            cache[tid] = src.resize((args.tile_width, args.tile_height), Image.Resampling.NEAREST)

    columns = SURFACE_SECTORS_W if args.surface_only else WORLD_SECTORS_W
    sector_px_w = OUTDOOR_GRID_W * args.tile_width
    sector_px_h = OUTDOOR_GRID_H * args.tile_height
    canvas = Image.new("RGB", (columns * sector_px_w, WORLD_SECTORS_H * sector_px_h), "black")
    draw = ImageDraw.Draw(canvas)

    for sector in sectors:
        if args.surface_only and sector.world_x >= SURFACE_SECTORS_W:
            continue
        sx = sector.world_x * sector_px_w
        sy = sector.world_y * sector_px_h
        for y in range(OUTDOOR_GRID_H):
            for x in range(OUTDOOR_GRID_W):
                tid = sector.tile(x, y, storage="x-major")
                tile = cache.get(tid)
                px = sx + x * args.tile_width
                py = sy + y * args.tile_height
                if tile is not None:
                    canvas.paste(tile, (px, py))
        draw.rectangle((sx, sy, sx + sector_px_w - 1, sy + sector_px_h - 1), outline=(0, 0, 0))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output)
    kind = "Valorim surface" if args.surface_only else "9x10 logical outdoor storage"
    print(f"Wrote {args.output} ({canvas.width}x{canvas.height}) - {kind}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
