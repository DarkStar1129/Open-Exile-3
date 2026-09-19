from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image

TERRAIN_CELL_W = 28
TERRAIN_CELL_H = 36
TERRAIN_SHEETS = ("TER1.BMP", "TER2.BMP", "TER3.BMP", "TER4.BMP", "TER5.BMP")
TERRAIN_ANIM_SHEET = "TERANIM.BMP"
TERRAIN_ANIM_FRAMES = 4
TERRAIN_ANIM_STRIP_W = TERRAIN_CELL_W * TERRAIN_ANIM_FRAMES


@dataclass(frozen=True)
class BitmapInfo:
    name: str
    width: int
    height: int
    mode: str
    palette_entries: int | None


def bitmap_info(path: Path) -> BitmapInfo:
    with Image.open(path) as im:
        palette_entries = None
        if im.mode == "P" and im.getpalette() is not None:
            palette_entries = len(im.getpalette()) // 3
        return BitmapInfo(path.name, im.width, im.height, im.mode, palette_entries)


def iter_bitmap_info(data_dir: Path) -> Iterable[BitmapInfo]:
    for path in sorted(data_dir.glob("*.BMP")):
        yield bitmap_info(path)


def load_terrain_cells(data_dir: Path) -> list[Image.Image]:
    """Load Exile III's 240 static 28x36 terrain graphics in picture order."""
    cells: list[Image.Image] = []
    for name in TERRAIN_SHEETS:
        path = data_dir / name
        if not path.exists():
            raise FileNotFoundError(path)
        with Image.open(path) as src:
            im = src.convert("RGB")
            if im.width % TERRAIN_CELL_W or im.height % TERRAIN_CELL_H:
                raise ValueError(f"{name} is not aligned to 28x36 cells: {im.size}")
            for y in range(0, im.height, TERRAIN_CELL_H):
                for x in range(0, im.width, TERRAIN_CELL_W):
                    cells.append(im.crop((x, y, x + TERRAIN_CELL_W, y + TERRAIN_CELL_H)))
    return cells


def load_terrain_animation_frames(data_dir: Path) -> list[tuple[Image.Image, ...]]:
    """Load animated terrain strips from TERANIM.BMP.

    Exile III stores each animation as four 28x36 frames (112x36 total).
    Animation slots are arranged in columns of five strips:
        x = 112 * (slot // 5)
        y =  36 * (slot % 5)
    The game's used slots are 300..313 => slots 0..13.
    """
    path = data_dir / TERRAIN_ANIM_SHEET
    if not path.exists():
        raise FileNotFoundError(path)
    with Image.open(path) as src:
        im = src.convert("RGB")
        if im.width % TERRAIN_ANIM_STRIP_W or im.height % TERRAIN_CELL_H:
            raise ValueError(f"{TERRAIN_ANIM_SHEET} has unexpected dimensions: {im.size}")
        columns = im.width // TERRAIN_ANIM_STRIP_W
        rows = im.height // TERRAIN_CELL_H
        slots = columns * rows
        result: list[tuple[Image.Image, ...]] = []
        for slot in range(slots):
            strip_x = TERRAIN_ANIM_STRIP_W * (slot // rows)
            strip_y = TERRAIN_CELL_H * (slot % rows)
            frames = tuple(
                im.crop(
                    (
                        strip_x + frame * TERRAIN_CELL_W,
                        strip_y,
                        strip_x + (frame + 1) * TERRAIN_CELL_W,
                        strip_y + TERRAIN_CELL_H,
                    )
                )
                for frame in range(TERRAIN_ANIM_FRAMES)
            )
            result.append(frames)
        return result
