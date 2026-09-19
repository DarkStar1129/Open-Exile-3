from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .collision import CollisionTable, load_collision_table
from .location import SaveMode, parse_location_state
from .outdoor import (
    WORLD_SECTORS_H,
    WORLD_SECTORS_W,
    build_working_map,
    load_outdoor,
    sector_at,
    working_tile,
)
from .save import extract_outdoor_info, parse_save_bytes
from .town import (
    active_tile,
    extract_current_town_creatures,
    extract_current_town_position,
    extract_current_town_terrain,
    locate_active_town_map,
)
from .visibility import reveal_around

# Direction numbering recovered from the classic Exile/Blades set_direction()
# implementation and validated by the user's one-tile-east save (direction 2).
DIRECTION_BY_DELTA = {
    (0, -1): 0,   # N
    (1, -1): 1,   # NE
    (1, 0): 2,    # E
    (1, 1): 3,    # SE
    (0, 1): 4,    # S
    (-1, 1): 5,   # SW
    (-1, 0): 6,   # W
    (-1, -1): 7,  # NW
}
DIRECTION_NAMES = (
    "north", "northeast", "east", "southeast",
    "south", "southwest", "west", "northwest",
)


@dataclass(frozen=True)
class OutdoorStepWindow:
    corner: tuple[int, int]
    source: tuple[int, int]
    destination: tuple[int, int]
    shifted: tuple[str, ...]


def normalize_outdoor_step(
    corner: tuple[int,int],
    source: tuple[int,int],
    dx:int,
    dy:int,
    *,
    world_w:int=WORLD_SECTORS_W,
    world_h:int=WORLD_SECTORS_H,
) -> OutdoorStepWindow:
    """Apply the classic 96x96 outdoor window-shift rules for one attempted step.

    Exile III keeps a 2x2 sector (96x96 tile) window around the party. When an
    attempted destination gets within six tiles of a working-window edge, the
    top-left sector can shift and the party's working coordinates jump by 48.
    The absolute world tile remains unchanged until the actual step succeeds.
    """
    if (dx,dy) not in DIRECTION_BY_DELTA:
        raise ValueError("Movement delta must be one of the eight adjacent directions")
    cx,cy=corner
    sx,sy=source
    raw_dest=(sx+dx,sy+dy)
    shifts:list[str]=[]

    if raw_dest[0] < 6 and cx > 0:
        cx -= 1; sx += 48; shifts.append("left")
    if raw_dest[0] > 90 and cx < world_w - 1:
        cx += 1; sx -= 48; shifts.append("right")
    if raw_dest[1] < 6 and cy > 0:
        cy -= 1; sy += 48; shifts.append("up")
    elif raw_dest[1] > 90 and cy < world_h - 1:
        cy += 1; sy -= 48; shifts.append("down")

    return OutdoorStepWindow(
        corner=(cx,cy),
        source=(sx,sy),
        destination=(sx+dx,sy+dy),
        shifted=tuple(shifts),
    )


@dataclass(frozen=True)
class MoveResult:
    moved: bool
    source: tuple[int, int]
    destination: tuple[int, int]
    direction: int
    reason: str
    terrain_id: int | None = None
    blocking_code: int | None = None
    shifted: tuple[str, ...] = ()
    town_exit: int | None = None
    special_id: int | None = None
    world_source: tuple[int,int] | None = None
    world_destination: tuple[int,int] | None = None


class MovementSandbox:
    """Read-only/in-memory movement model for recovered Exile III state.

    It never mutates the original save. Town movement currently models map
    bounds, native terrain blockage and live creature occupancy. Outdoor
    movement additionally reproduces the classic dynamic 2x2-sector window,
    world-edge checks, persistent in-session exploration and outdoor exit
    detection. Scripted specials, doors, boats/horses, wandering parties,
    damage terrain and automatic town loading remain separate layers.
    """

    def __init__(self, data_dir: Path, save_data: bytes):
        self.data_dir = Path(data_dir)
        self.save_data = bytes(save_data)
        self.location = parse_location_state(self.save_data)
        self.collision: CollisionTable = load_collision_table(self.data_dir / "EXILE3.EXE")
        summary = parse_save_bytes(self.save_data)
        self.direction = summary.direction
        self._start_direction = summary.direction

        self.mode = self.location.mode
        self._town_size: int | None = None
        self._town_terrain: bytes | None = None
        self._outdoor_terrain: bytes | None = None
        self._outdoor_corner: tuple[int,int] | None = None
        self._sectors = None
        self._sector_visibility: dict[tuple[int,int], bytearray] = {}
        self._occupied: set[tuple[int, int]] = set()

        if self.mode is SaveMode.TOWN:
            live = extract_current_town_terrain(self.save_data)
            match = locate_active_town_map(
                (self.data_dir / "TOWN.DAT").read_bytes(), live, require_confident=True
            )
            self._town_size = match.size
            self._town_terrain = live
            self.position = extract_current_town_position(self.save_data)
            for c in extract_current_town_creatures(self.save_data):
                if c.active == 0 or not c.populated:
                    continue
                for px in range(max(1, c.width)):
                    for py in range(max(1, c.height)):
                        self._occupied.add((c.x + px, c.y + py))
        elif self.mode is SaveMode.OUTDOOR:
            loc = self.location.outdoor
            self._sectors = load_outdoor(self.data_dir / "OUTDOOR.DAT")
            self._outdoor_corner = (loc.corner_x, loc.corner_y)
            self.position = (loc.working_x, loc.working_y)
            self._rebuild_outdoor_terrain()
            self._seed_visibility(extract_outdoor_info(self.save_data))
        else:
            raise ValueError(f"Unsupported/unknown save mode flag {self.location.raw_mode}")

        self.start_position = self.position
        self._start_corner = self._outdoor_corner
        self._start_sector_visibility = {
            key: bytearray(value) for key,value in self._sector_visibility.items()
        }

    @property
    def map_size(self) -> tuple[int, int]:
        if self.mode is SaveMode.TOWN:
            assert self._town_size is not None
            return self._town_size, self._town_size
        return 96, 96

    @property
    def occupied(self) -> frozenset[tuple[int, int]]:
        return frozenset(self._occupied)

    @property
    def outdoor_corner(self) -> tuple[int,int] | None:
        return self._outdoor_corner

    @property
    def outdoor_quadrant(self) -> tuple[int,int] | None:
        if self.mode is not SaveMode.OUTDOOR:
            return None
        return (1 if self.position[0] > 47 else 0, 1 if self.position[1] > 47 else 0)

    @property
    def outdoor_local_position(self) -> tuple[int,int] | None:
        q=self.outdoor_quadrant
        if q is None:
            return None
        return (self.position[0]-48*q[0], self.position[1]-48*q[1])

    @property
    def outdoor_sector(self) -> tuple[int,int] | None:
        if self.mode is not SaveMode.OUTDOOR or self._outdoor_corner is None:
            return None
        q=self.outdoor_quadrant
        assert q is not None
        return (self._outdoor_corner[0]+q[0], self._outdoor_corner[1]+q[1])

    @property
    def outdoor_world_position(self) -> tuple[int,int] | None:
        if self.mode is not SaveMode.OUTDOOR or self._outdoor_corner is None:
            return None
        return (
            self._outdoor_corner[0]*48 + self.position[0],
            self._outdoor_corner[1]*48 + self.position[1],
        )

    @property
    def region_label(self) -> str | None:
        if self.mode is not SaveMode.OUTDOOR or self._sectors is None:
            return None
        sec_xy=self.outdoor_sector
        assert sec_xy is not None
        sec=sector_at(self._sectors,*sec_xy)
        return sec.region_label if sec else None

    @property
    def visibility_buffer(self) -> bytes | None:
        if self.mode is not SaveMode.OUTDOOR or self._outdoor_corner is None:
            return None
        out=bytearray(96*96)
        cx,cy=self._outdoor_corner
        for qx in range(2):
            for qy in range(2):
                sec=self._sector_visibility.get((cx+qx,cy+qy))
                if sec is None:
                    continue
                for x in range(48):
                    for y in range(48):
                        out[(qx*48+x)*96+(qy*48+y)] = sec[x*48+y]
        return bytes(out)

    def _seed_visibility(self, info: bytes) -> None:
        if len(info) != 96*96 or self._outdoor_corner is None:
            raise ValueError("Expected a 96x96 outdoor visibility buffer")
        cx,cy=self._outdoor_corner
        for qx in range(2):
            for qy in range(2):
                sx,sy=cx+qx,cy+qy
                if not (0<=sx<WORLD_SECTORS_W and 0<=sy<WORLD_SECTORS_H):
                    continue
                local=bytearray(48*48)
                for x in range(48):
                    for y in range(48):
                        local[x*48+y]=info[(qx*48+x)*96+(qy*48+y)]
                self._sector_visibility[(sx,sy)]=local

    def _store_visibility_window(self, info: bytes | bytearray) -> None:
        if len(info) != 96*96 or self._outdoor_corner is None:
            raise ValueError("Expected a 96x96 outdoor visibility buffer")
        cx,cy=self._outdoor_corner
        for qx in range(2):
            for qy in range(2):
                sx,sy=cx+qx,cy+qy
                if not (0<=sx<WORLD_SECTORS_W and 0<=sy<WORLD_SECTORS_H):
                    continue
                local=self._sector_visibility.setdefault((sx,sy),bytearray(48*48))
                for x in range(48):
                    for y in range(48):
                        local[x*48+y]=info[(qx*48+x)*96+(qy*48+y)]

    def _rebuild_outdoor_terrain(self) -> None:
        assert self._sectors is not None and self._outdoor_corner is not None
        self._outdoor_terrain = build_working_map(
            self._sectors, self._outdoor_corner[0], self._outdoor_corner[1]
        )

    def _reveal_outdoor(self) -> None:
        if self.mode is not SaveMode.OUTDOOR:
            return
        info=bytearray(self.visibility_buffer or bytes(96*96))
        reveal_around(info,self.tile_at,self.collision,self.position,96,96,radius=4)
        self._store_visibility_window(info)

    def tile_at(self, x: int, y: int) -> int:
        w, h = self.map_size
        if not (0 <= x < w and 0 <= y < h):
            raise IndexError((x, y))
        if self.mode is SaveMode.TOWN:
            assert self._town_terrain is not None and self._town_size is not None
            return active_tile(self._town_terrain, x, y, self._town_size)
        assert self._outdoor_terrain is not None
        return working_tile(self._outdoor_terrain, x, y)

    def outdoor_exit_at_position(self) -> int | None:
        if self.mode is not SaveMode.OUTDOOR or self._sectors is None:
            return None
        sec_xy=self.outdoor_sector
        local=self.outdoor_local_position
        assert sec_xy is not None and local is not None
        sec=sector_at(self._sectors,*sec_xy)
        if sec is None:
            return None
        ex=sec.exit_at(*local)
        return ex.town if ex else None

    def outdoor_special_at_position(self) -> int | None:
        if self.mode is not SaveMode.OUTDOOR or self._sectors is None:
            return None
        sec_xy=self.outdoor_sector
        local=self.outdoor_local_position
        assert sec_xy is not None and local is not None
        sec=sector_at(self._sectors,*sec_xy)
        if sec is None:
            return None
        sp=sec.special_at(*local)
        return sp.special_id if sp else None

    def reset(self) -> None:
        self.position = self.start_position
        self.direction = self._start_direction
        if self.mode is SaveMode.OUTDOOR:
            self._outdoor_corner=self._start_corner
            self._sector_visibility={
                key: bytearray(value) for key,value in self._start_sector_visibility.items()
            }
            self._rebuild_outdoor_terrain()

    def _outdoor_world_edge_blocked(self, dest:tuple[int,int]) -> bool:
        assert self._outdoor_corner is not None
        x,y=dest; cx,cy=self._outdoor_corner
        if x < 4 and cx <= 0:
            return True
        if (x > 92 and cx >= WORLD_SECTORS_W-2) or (x > 44 and cx >= WORLD_SECTORS_W-1):
            return True
        if y < 4 and cy <= 0:
            return True
        if (y > 92 and cy >= WORLD_SECTORS_H-2) or (y > 44 and cy >= WORLD_SECTORS_H-1):
            return True
        return False

    def attempt(self, dx: int, dy: int) -> MoveResult:
        if (dx, dy) not in DIRECTION_BY_DELTA:
            raise ValueError("Movement delta must be one of the eight adjacent directions")
        original_source = self.position
        direction = DIRECTION_BY_DELTA[(dx, dy)]
        world_source=self.outdoor_world_position
        shifts:tuple[str,...]=()

        if self.mode is SaveMode.OUTDOOR:
            assert self._outdoor_corner is not None
            step=normalize_outdoor_step(self._outdoor_corner,self.position,dx,dy)
            if step.corner != self._outdoor_corner:
                self._outdoor_corner=step.corner
                self.position=step.source
                self._rebuild_outdoor_terrain()
            destination=step.destination
            shifts=step.shifted
            if self._outdoor_world_edge_blocked(destination):
                return MoveResult(
                    False,original_source,destination,direction,"world edge",
                    shifted=shifts,world_source=world_source,
                    world_destination=(world_source[0]+dx,world_source[1]+dy) if world_source else None,
                )
        else:
            destination = (original_source[0] + dx, original_source[1] + dy)

        w, h = self.map_size
        if not (0 <= destination[0] < w and 0 <= destination[1] < h):
            return MoveResult(False, original_source, destination, direction, "map boundary", shifted=shifts)

        terrain_id = self.tile_at(*destination)
        code = self.collision.blocking_code(terrain_id)
        if self.collision.blocks_party(terrain_id):
            return MoveResult(
                False, original_source, destination, direction, "terrain blocked", terrain_id, code,
                shifted=shifts,world_source=world_source,
                world_destination=(world_source[0]+dx,world_source[1]+dy) if world_source else None,
            )

        if self.mode is SaveMode.TOWN and destination in self._occupied:
            return MoveResult(False, original_source, destination, direction, "creature occupied", terrain_id, code)

        self.position = destination
        self.direction = direction
        if self.mode is SaveMode.OUTDOOR:
            self._reveal_outdoor()
        town_exit=self.outdoor_exit_at_position()
        special_id=self.outdoor_special_at_position()
        world_destination=self.outdoor_world_position
        return MoveResult(
            True, original_source, destination, direction, "moved", terrain_id, code,
            shifted=shifts,town_exit=town_exit,special_id=special_id,world_source=world_source,
            world_destination=world_destination,
        )


def direction_for_delta(dx: int, dy: int) -> int:
    try:
        return DIRECTION_BY_DELTA[(dx, dy)]
    except KeyError as exc:
        raise ValueError((dx, dy)) from exc
