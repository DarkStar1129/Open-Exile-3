from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .location import parse_location_state
from .outdoor import load_outdoor, sector_at
from .ne import decode_win16_string_resources
from .save import (
    TOWN_STRING_BASE, TOWN_STRING_STRIDE,
    extract_town_name, extract_town_resource_difficulty, parse_save_bytes,
)


@dataclass(frozen=True)
class TownEntranceAnchor:
    town_id: int
    town_name: str | None
    resource_difficulty: int | None
    sector_x: int
    sector_y: int
    sector_index: int
    region_label: str
    local_x: int
    local_y: int

    @property
    def world_position(self) -> tuple[int, int]:
        return self.sector_x * 48 + self.local_x, self.sector_y * 48 + self.local_y


def build_town_entrance_index(data_dir: Path) -> dict[int, tuple[TownEntranceAnchor, ...]]:
    """Join OUTDOOR.DAT exit records to executable town metadata."""
    data_dir = Path(data_dir)
    exe = data_dir / "EXILE3.EXE"
    strings = decode_win16_string_resources(exe)
    found: dict[int, list[TownEntranceAnchor]] = {}
    for sector in load_outdoor(data_dir / "OUTDOOR.DAT"):
        for exit_record in sector.exits:
            base = TOWN_STRING_BASE + exit_record.town * TOWN_STRING_STRIDE
            name = strings.get(base, "").strip() or None
            try:
                difficulty = int(strings.get(base + 1, "").strip())
            except ValueError:
                difficulty = None
            anchor = TownEntranceAnchor(
                town_id=exit_record.town,
                town_name=name,
                resource_difficulty=difficulty,
                sector_x=sector.world_x,
                sector_y=sector.world_y,
                sector_index=sector.index,
                region_label=sector.region_label,
                local_x=exit_record.x,
                local_y=exit_record.y,
            )
            found.setdefault(exit_record.town, []).append(anchor)
    return {town: tuple(anchors) for town, anchors in found.items()}


def retained_town_entrance(data_dir: Path, save_data: bytes) -> TownEntranceAnchor | None:
    """Resolve a town save's retained outdoor location back to its entrance.

    Exile III keeps the previous outdoor 2x2-window coordinates while the
    party is in a town. When those retained coordinates point at an
    OUTDOOR.DAT exit for the save's current town, they form a strong reverse
    transition anchor without mutating or guessing any save state.
    """
    state = parse_location_state(save_data)
    summary = parse_save_bytes(save_data)
    loc = state.outdoor
    sector = sector_at(load_outdoor(Path(data_dir) / "OUTDOOR.DAT"), loc.sector_x, loc.sector_y)
    if sector is None:
        return None
    matching = [
        e for e in sector.exits
        if e.town == summary.current_town and e.x == loc.local_x and e.y == loc.local_y
    ]
    if not matching:
        return None
    return TownEntranceAnchor(
        town_id=summary.current_town,
        town_name=extract_town_name(Path(data_dir) / "EXILE3.EXE", summary.current_town),
        resource_difficulty=extract_town_resource_difficulty(
            Path(data_dir) / "EXILE3.EXE", summary.current_town
        ),
        sector_x=sector.world_x,
        sector_y=sector.world_y,
        sector_index=sector.index,
        region_label=sector.region_label,
        local_x=matching[0].x,
        local_y=matching[0].y,
    )
