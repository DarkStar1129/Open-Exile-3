from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

TERRAIN_COUNT = 256

# Unique prefix of the 256-byte terrain blocking table in Exile III v1.0.3
# Windows. We search for it rather than relying on a hard-coded file offset.
_COLLISION_SIGNATURE = bytes([
    0,0,0,0,0,5,5,1,5,5,1,5,5,1,5,5,
    1,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,
])

BLOCKING_NAMES = {
    0: "none",
    1: "sight",
    2: "monsters",
    3: "move",
    4: "move-and-shoot",
    5: "move-and-sight",
}

@dataclass(frozen=True)
class CollisionTable:
    file_offset: int
    values: tuple[int, ...]

    def blocking_code(self, terrain_id: int) -> int:
        if not 0 <= terrain_id < TERRAIN_COUNT:
            raise IndexError(terrain_id)
        return self.values[terrain_id]

    def blocking_name(self, terrain_id: int) -> str:
        return BLOCKING_NAMES.get(self.blocking_code(terrain_id), "unknown")

    def blocks_party(self, terrain_id: int) -> bool:
        # Confirmed from the Exile III table plus one-step movement validation.
        return self.blocking_code(terrain_id) in (3, 4, 5)

    def blocks_sight(self, terrain_id: int) -> bool:
        return self.blocking_code(terrain_id) in (1, 5)

    def blocks_projectiles(self, terrain_id: int) -> bool:
        return self.blocking_code(terrain_id) == 4

    def blocks_monsters(self, terrain_id: int) -> bool:
        return self.blocking_code(terrain_id) in (2, 3, 4, 5)


def _find_collision_table(data: bytes) -> int:
    hits: list[int] = []
    start = 0
    while True:
        at = data.find(_COLLISION_SIGNATURE, start)
        if at < 0:
            break
        if at + TERRAIN_COUNT <= len(data):
            candidate = data[at:at + TERRAIN_COUNT]
            if max(candidate) <= 5:
                hits.append(at)
        start = at + 1
    if len(hits) != 1:
        raise ValueError(f"Expected one Exile III collision table; found {len(hits)}")
    return hits[0]


def load_collision_table(exe_path: Path) -> CollisionTable:
    data = exe_path.read_bytes()
    off = _find_collision_table(data)
    values = tuple(data[off:off + TERRAIN_COUNT])
    return CollisionTable(off, values)
