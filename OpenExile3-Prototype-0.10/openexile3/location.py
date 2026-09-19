from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .save import decode_party_record

SAVE_MODE_TOWN = 1342
SAVE_MODE_OUTDOOR = 5790

# Confirmed from the supplied Fort Emergence -> outdoor and New Cotra samples.
# These offsets are in the decoded XOR-0x5C party record.
PARTY_OUTDOOR_CORNER = 4_834
PARTY_I_W_C = 4_836
PARTY_P_LOC = 4_838
PARTY_LOC_IN_SEC = 4_840


class SaveMode(str, Enum):
    TOWN = "town"
    OUTDOOR = "outdoor"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class OutdoorLocation:
    corner_x: int
    corner_y: int
    quadrant_x: int
    quadrant_y: int
    working_x: int
    working_y: int
    local_x: int
    local_y: int

    @property
    def sector_x(self) -> int:
        return self.corner_x + self.quadrant_x

    @property
    def sector_y(self) -> int:
        return self.corner_y + self.quadrant_y

    @property
    def sector_index(self) -> int:
        return self.sector_y * 9 + self.sector_x

    @property
    def invariant_ok(self) -> bool:
        return (
            self.working_x == self.quadrant_x * 48 + self.local_x
            and self.working_y == self.quadrant_y * 48 + self.local_y
        )


@dataclass(frozen=True)
class LocationState:
    mode: SaveMode
    raw_mode: int
    outdoor: OutdoorLocation


def save_mode(data: bytes) -> tuple[SaveMode, int]:
    if len(data) < 2:
        raise ValueError("Save is too small")
    raw = int.from_bytes(data[0:2], "little")
    if raw == SAVE_MODE_TOWN:
        return SaveMode.TOWN, raw
    if raw == SAVE_MODE_OUTDOOR:
        return SaveMode.OUTDOOR, raw
    return SaveMode.UNKNOWN, raw


def extract_outdoor_location(data: bytes) -> OutdoorLocation:
    p = decode_party_record(data)
    need = PARTY_LOC_IN_SEC + 2
    if len(p) < need:
        raise ValueError("Decoded party record is too small for outdoor location fields")
    cx, cy = p[PARTY_OUTDOOR_CORNER:PARTY_OUTDOOR_CORNER + 2]
    qx, qy = p[PARTY_I_W_C:PARTY_I_W_C + 2]
    wx, wy = p[PARTY_P_LOC:PARTY_P_LOC + 2]
    lx, ly = p[PARTY_LOC_IN_SEC:PARTY_LOC_IN_SEC + 2]
    return OutdoorLocation(cx, cy, qx, qy, wx, wy, lx, ly)


def parse_location_state(data: bytes) -> LocationState:
    mode, raw = save_mode(data)
    return LocationState(mode=mode, raw_mode=raw, outdoor=extract_outdoor_location(data))


def parse_location_file(path: Path) -> LocationState:
    return parse_location_state(path.read_bytes())
