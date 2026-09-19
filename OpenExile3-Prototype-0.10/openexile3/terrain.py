from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct

from .ne import decode_win16_string_resources

TERRAIN_COUNT = 256

# This prefix is distinctive in the Exile III Win16 executable and is the
# beginning of the 256-entry terrain-type -> picture-number table.
_PICTURE_SIGNATURE = (
    0, 1, 2, 3, 4, 5, 6, 6, 7, 8, 8, 9, 10, 10, 11, 12,
    12, 13, 14, 15, 16, 17, 18, 19,
)

# Exile III encodes animated terrain pictures as 300..313. Each maps to one
# 4-frame, 28x36 animation strip in TERANIM.BMP.
ANIM_PICTURE_BASE = 300
ANIM_PICTURE_LAST = 313
ANIM_SLOT_COUNT = ANIM_PICTURE_LAST - ANIM_PICTURE_BASE + 1


@dataclass(frozen=True)
class TerrainDefinition:
    terrain_id: int
    name: str
    picture: int

    @property
    def is_animated(self) -> bool:
        return ANIM_PICTURE_BASE <= self.picture <= ANIM_PICTURE_LAST

    @property
    def animation_slot(self) -> int | None:
        if not self.is_animated:
            return None
        return self.picture - ANIM_PICTURE_BASE


def _find_picture_table(data: bytes) -> int:
    signature = struct.pack("<" + "H" * len(_PICTURE_SIGNATURE), *_PICTURE_SIGNATURE)
    offsets: list[int] = []
    start = 0
    while True:
        off = data.find(signature, start)
        if off < 0:
            break
        offsets.append(off)
        start = off + 1
    if len(offsets) != 1:
        raise ValueError(
            f"Expected exactly one Exile III terrain picture table signature; found {len(offsets)}"
        )
    off = offsets[0]
    if off + TERRAIN_COUNT * 2 > len(data):
        raise ValueError("Terrain picture table is truncated")
    values = struct.unpack_from("<" + "H" * TERRAIN_COUNT, data, off)
    if max(values) > 1000:
        raise ValueError("Terrain picture table candidate failed sanity check")
    return off


def extract_terrain_picture_map(exe_path: Path) -> tuple[int, tuple[int, ...]]:
    data = exe_path.read_bytes()
    off = _find_picture_table(data)
    values = struct.unpack_from("<" + "H" * TERRAIN_COUNT, data, off)
    return off, tuple(values)


def extract_terrain_names(exe_path: Path) -> tuple[int, tuple[str, ...]]:
    strings = decode_win16_string_resources(exe_path)
    signature = ("Cave Floor", "Cave Floor", "Grass", "Grass", "Grass", "Cave Wall")
    candidates: list[int] = []
    for start in sorted(strings):
        if tuple(strings.get(start + i, "") for i in range(len(signature))) == signature:
            candidates.append(start)
    if len(candidates) != 1:
        raise ValueError(
            f"Expected exactly one terrain-name STRINGTABLE signature; found {len(candidates)}"
        )
    start = candidates[0]
    names = tuple(strings.get(start + i, "") for i in range(TERRAIN_COUNT))
    return start, names


def load_terrain_definitions(exe_path: Path) -> tuple[int, int, tuple[TerrainDefinition, ...]]:
    picture_off, pictures = extract_terrain_picture_map(exe_path)
    string_start, names = extract_terrain_names(exe_path)
    definitions = tuple(
        TerrainDefinition(terrain_id=i, name=names[i], picture=pictures[i])
        for i in range(TERRAIN_COUNT)
    )
    return picture_off, string_start, definitions
