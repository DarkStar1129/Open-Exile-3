#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openexile3.assets import (
    TERRAIN_CELL_H,
    TERRAIN_CELL_W,
    load_terrain_animation_frames,
    load_terrain_cells,
)
from openexile3.outdoor import OUTDOOR_GRID_H, OUTDOOR_GRID_W, load_outdoor
from openexile3.terrain import ANIM_PICTURE_BASE, load_terrain_definitions


def main() -> int:
    ap = argparse.ArgumentParser(description="Render an Exile III outdoor sector with decoded terrain pictures")
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--sector", type=int, default=0, choices=range(90))
    ap.add_argument("--storage", choices=("row-major", "x-major"), default="x-major")
    ap.add_argument("--anim-frame", type=int, default=0, choices=range(4))
    ap.add_argument("--scale", type=int, default=1, choices=range(1, 9))
    ap.add_argument("--output", type=Path, default=Path("sector.png"))
    args = ap.parse_args()

    d = args.data_dir.expanduser().resolve()
    static_cells = load_terrain_cells(d)
    anim_slots = load_terrain_animation_frames(d)
    picture_offset, string_start, definitions = load_terrain_definitions(d / "EXILE3.EXE")
    sector = load_outdoor(d / "OUTDOOR.DAT")[args.sector]

    canvas = Image.new("RGB", (OUTDOOR_GRID_W * TERRAIN_CELL_W, OUTDOOR_GRID_H * TERRAIN_CELL_H), "black")
    draw = ImageDraw.Draw(canvas)
    unknown = 0

    for y in range(OUTDOOR_GRID_H):
        for x in range(OUTDOOR_GRID_W):
            tid = sector.tile(x, y, storage=args.storage)
            definition = definitions[tid]
            pic = definition.picture
            px, py = x * TERRAIN_CELL_W, y * TERRAIN_CELL_H

            tile = None
            if 0 <= pic < len(static_cells):
                tile = static_cells[pic]
            elif pic >= ANIM_PICTURE_BASE:
                slot = pic - ANIM_PICTURE_BASE
                if 0 <= slot < len(anim_slots):
                    tile = anim_slots[slot][args.anim_frame]

            if tile is not None:
                canvas.paste(tile, (px, py))
            else:
                unknown += 1
                draw.rectangle((px, py, px + TERRAIN_CELL_W - 1, py + TERRAIN_CELL_H - 1), fill=(32, 32, 32))
                draw.text((px + 1, py + 1), f"{tid}:{pic}", fill=(255, 255, 255))

    if args.scale != 1:
        canvas = canvas.resize((canvas.width * args.scale, canvas.height * args.scale), Image.Resampling.NEAREST)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output)
    print(f"Wrote {args.output}")
    print(f"Sector {sector.index} ({sector.world_x},{sector.world_y}) region={sector.region_label!r}")
    print("Labels:", [s for s in sector.labels if s])
    print(f"Terrain picture table: EXILE3.EXE file offset 0x{picture_offset:X}")
    print(f"Terrain names: Win16 STRINGTABLE IDs {string_start}..{string_start + 255}")
    print(f"Storage orientation: {args.storage}; animation frame: {args.anim_frame}")
    if unknown:
        print(f"WARNING: {unknown} cells could not be resolved to a terrain picture")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
