from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

OUTDOOR_RECORD_SIZE = 3220
OUTDOOR_SECTOR_COUNT = 90
OUTDOOR_GRID_W = 48
OUTDOOR_GRID_H = 48
OUTDOOR_TERRAIN_BYTES = OUTDOOR_GRID_W * OUTDOOR_GRID_H
WORLD_SECTORS_W = 9
WORLD_SECTORS_H = 10
# The first seven columns are the contiguous Valorim surface map. Columns
# 7-8 are auxiliary outdoor spaces (Vahnatai/Upper Exile/cave regions).
SURFACE_SECTORS_W = 7
SURFACE_SECTORS_H = 10

# E3's compact outdoor record retains the same early layout as the later
# Blades outdoor record: terrain, 18 specials, 8 exits, and 8 signs.
SPECIAL_LOCS_OFFSET = OUTDOOR_TERRAIN_BYTES
SPECIAL_COUNT = 18
SPECIAL_IDS_OFFSET = SPECIAL_LOCS_OFFSET + SPECIAL_COUNT * 2
EXIT_LOCS_OFFSET = SPECIAL_IDS_OFFSET + SPECIAL_COUNT
EXIT_COUNT = 8
EXIT_DESTS_OFFSET = EXIT_LOCS_OFFSET + EXIT_COUNT * 2
SIGN_LOCS_OFFSET = EXIT_DESTS_OFFSET + EXIT_COUNT
SIGN_COUNT = 8

# Eight fixed 30-byte local labels followed by a 30-byte region label.
LABEL_BASE = 2566
LABEL_SIZE = 30
LABEL_COUNT = 8
REGION_LABEL_OFFSET = 2806


@dataclass(frozen=True)
class OutdoorSpecial:
    slot: int
    x: int
    y: int
    special_id: int


@dataclass(frozen=True)
class OutdoorExit:
    slot: int
    x: int
    y: int
    town: int


@dataclass(frozen=True)
class OutdoorSign:
    slot: int
    x: int
    y: int


@dataclass(frozen=True)
class OutdoorSector:
    index: int
    terrain: bytes
    labels: tuple[str, ...]
    region_label: str
    specials: tuple[OutdoorSpecial, ...]
    exits: tuple[OutdoorExit, ...]
    signs: tuple[OutdoorSign, ...]
    raw: bytes

    @property
    def world_x(self) -> int:
        return self.index % WORLD_SECTORS_W

    @property
    def world_y(self) -> int:
        return self.index // WORLD_SECTORS_W

    def tile(self, x: int, y: int, *, storage: str = "x-major") -> int:
        if not 0 <= x < OUTDOOR_GRID_W or not 0 <= y < OUTDOOR_GRID_H:
            raise IndexError((x, y))
        if storage == "x-major":
            return self.terrain[x * OUTDOOR_GRID_H + y]
        if storage == "row-major":
            return self.terrain[y * OUTDOOR_GRID_W + x]
        raise ValueError("storage must be 'x-major' or 'row-major'")

    def special_at(self, x: int, y: int) -> OutdoorSpecial | None:
        return next((sp for sp in self.specials if (sp.x, sp.y) == (x, y)), None)

    def exit_at(self, x: int, y: int) -> OutdoorExit | None:
        return next((ex for ex in self.exits if (ex.x, ex.y) == (x, y)), None)

    def sign_at(self, x: int, y: int) -> OutdoorSign | None:
        return next((sg for sg in self.signs if (sg.x, sg.y) == (x, y)), None)


def _fixed_string(buf: bytes, offset: int, size: int) -> str:
    field = buf[offset : offset + size]
    field = field.split(b"\0", 1)[0]
    return field.decode("cp1252", errors="replace").strip()


def _pair(buf: bytes, offset: int) -> tuple[int, int]:
    return buf[offset], buf[offset + 1]


def parse_outdoor_record(raw: bytes, index: int) -> OutdoorSector:
    if len(raw) != OUTDOOR_RECORD_SIZE:
        raise ValueError(f"Outdoor record is {len(raw)} bytes; expected {OUTDOOR_RECORD_SIZE}")

    labels = tuple(
        _fixed_string(raw, LABEL_BASE + n * LABEL_SIZE, LABEL_SIZE)
        for n in range(LABEL_COUNT)
    )
    region = _fixed_string(raw, REGION_LABEL_OFFSET, LABEL_SIZE)

    specials: list[OutdoorSpecial] = []
    for slot in range(SPECIAL_COUNT):
        x, y = _pair(raw, SPECIAL_LOCS_OFFSET + slot * 2)
        special_id = raw[SPECIAL_IDS_OFFSET + slot]
        if (x, y) != (0, 0) or special_id != 0:
            specials.append(OutdoorSpecial(slot, x, y, special_id))

    exits: list[OutdoorExit] = []
    for slot in range(EXIT_COUNT):
        x, y = _pair(raw, EXIT_LOCS_OFFSET + slot * 2)
        town = raw[EXIT_DESTS_OFFSET + slot]
        if (x, y) != (0, 0) or town != 0:
            exits.append(OutdoorExit(slot, x, y, town))

    signs: list[OutdoorSign] = []
    for slot in range(SIGN_COUNT):
        x, y = _pair(raw, SIGN_LOCS_OFFSET + slot * 2)
        if (x, y) != (0, 0):
            signs.append(OutdoorSign(slot, x, y))

    return OutdoorSector(
        index=index,
        terrain=raw[:OUTDOOR_TERRAIN_BYTES],
        labels=labels,
        region_label=region,
        specials=tuple(specials),
        exits=tuple(exits),
        signs=tuple(signs),
        raw=raw,
    )


def load_outdoor(path: Path) -> list[OutdoorSector]:
    data = path.read_bytes()
    expected = OUTDOOR_RECORD_SIZE * OUTDOOR_SECTOR_COUNT
    if len(data) != expected:
        raise ValueError(f"Unexpected OUTDOOR.DAT size {len(data):,}; expected {expected:,}")

    return [
        parse_outdoor_record(data[i * OUTDOOR_RECORD_SIZE : (i + 1) * OUTDOOR_RECORD_SIZE], i)
        for i in range(OUTDOOR_SECTOR_COUNT)
    ]


def sector_at(sectors: list[OutdoorSector] | tuple[OutdoorSector, ...], x: int, y: int) -> OutdoorSector | None:
    if not (0 <= x < WORLD_SECTORS_W and 0 <= y < WORLD_SECTORS_H):
        return None
    return sectors[y * WORLD_SECTORS_W + x]


def build_working_map(
    sectors: list[OutdoorSector] | tuple[OutdoorSector, ...],
    corner_x: int,
    corner_y: int,
) -> bytes:
    """Build the original engine's 96x96 four-sector outdoor working map.

    The returned buffer is x-major: terrain[x][y], index x*96+y.
    Out-of-world quadrants are filled with terrain ID 0.
    """
    size = 96
    out = bytearray(size * size)
    for qx in range(2):
        for qy in range(2):
            sector = sector_at(sectors, corner_x + qx, corner_y + qy)
            if sector is None:
                continue
            for x in range(48):
                for y in range(48):
                    out[(qx * 48 + x) * size + (qy * 48 + y)] = sector.tile(x, y)
    return bytes(out)


def working_tile(terrain: bytes, x: int, y: int) -> int:
    if len(terrain) != 96 * 96:
        raise ValueError("Expected a 96x96 outdoor working map")
    if not (0 <= x < 96 and 0 <= y < 96):
        raise IndexError((x, y))
    return terrain[x * 96 + y]
