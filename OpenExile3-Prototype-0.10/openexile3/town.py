from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

TOWN_GRID_W = 64
TOWN_GRID_H = 64
TOWN_TERRAIN_SIZE = TOWN_GRID_W * TOWN_GRID_H

# Exile III current-town data recovered from the supplied Windows saves.
CURRENT_TOWN_CREATURES_OFFSET = 75_806
CURRENT_TOWN_CREATURE_COUNT = 60
CURRENT_TOWN_CREATURE_SIZE = 92
CURRENT_TOWN_X_OFFSET = 81_331
CURRENT_TOWN_Y_OFFSET = 81_332
CURRENT_TOWN_NAME_OFFSET = 81_333
CURRENT_TOWN_NAME_SIZE = 256
CURRENT_TOWN_TERRAIN_OFFSET = 81_589

@dataclass(frozen=True)
class TownSourceMatch:
    source_offset: int
    exact_bytes: int
    total_bytes: int
    exact_columns: int
    column_votes: int

    @property
    def similarity(self) -> float:
        return self.exact_bytes / self.total_bytes if self.total_bytes else 0.0

@dataclass(frozen=True)
class CreatureState:
    slot: int
    active: int
    attitude: int
    monster_id: int
    x: int
    y: int
    level: int
    health: int
    max_health: int
    direction: int
    # These fields are the most useful rendering fields recovered from the
    # compact 92-byte E3 live creature record. Width/height are strongly
    # validated; picture selection is currently derived from monster_id.
    width: int
    height: int

    @property
    def populated(self) -> bool:
        return self.monster_id != 0 and self.width > 0 and self.height > 0


def extract_current_town_position(data: bytes) -> tuple[int, int]:
    if len(data) <= CURRENT_TOWN_Y_OFFSET:
        raise ValueError("Save is too small to contain current-town coordinates")
    return data[CURRENT_TOWN_X_OFFSET], data[CURRENT_TOWN_Y_OFFSET]


def extract_current_town_name(data: bytes) -> str:
    end = CURRENT_TOWN_NAME_OFFSET + CURRENT_TOWN_NAME_SIZE
    if len(data) < end:
        raise ValueError("Save is too small to contain current-town name")
    raw = data[CURRENT_TOWN_NAME_OFFSET:end].split(b"\x00", 1)[0]
    return raw.decode("cp1252", errors="replace").strip()


def extract_current_town_terrain(data: bytes) -> bytes:
    end = CURRENT_TOWN_TERRAIN_OFFSET + TOWN_TERRAIN_SIZE
    if len(data) < end:
        raise ValueError(
            f"Save is {len(data):,} bytes; expected at least {end:,} bytes "
            "for an in-town Exile III save"
        )
    return data[CURRENT_TOWN_TERRAIN_OFFSET:end]


def load_current_town_terrain(save_path: Path) -> bytes:
    return extract_current_town_terrain(save_path.read_bytes())


def tile(terrain: bytes, x: int, y: int) -> int:
    """Return terrain[x][y].

    Exile III stores town terrain in C x-major order: terrain[64][64], so the
    on-disk index is x*64 + y, not y*64 + x.
    """
    if len(terrain) != TOWN_TERRAIN_SIZE:
        raise ValueError(f"Expected {TOWN_TERRAIN_SIZE} terrain bytes")
    if not 0 <= x < TOWN_GRID_W or not 0 <= y < TOWN_GRID_H:
        raise IndexError((x, y))
    return terrain[x * TOWN_GRID_H + y]


def extract_current_town_creatures(data: bytes) -> tuple[CreatureState, ...]:
    end = CURRENT_TOWN_CREATURES_OFFSET + CURRENT_TOWN_CREATURE_COUNT * CURRENT_TOWN_CREATURE_SIZE
    if len(data) < end:
        raise ValueError("Save is too small to contain current-town creature records")
    out: list[CreatureState] = []
    for slot in range(CURRENT_TOWN_CREATURE_COUNT):
        start = CURRENT_TOWN_CREATURES_OFFSET + slot * CURRENT_TOWN_CREATURE_SIZE
        r = data[start:start + CURRENT_TOWN_CREATURE_SIZE]
        active = int.from_bytes(r[0:2], "little", signed=True)
        attitude = int.from_bytes(r[2:4], "little", signed=True)
        monster_id = r[4]
        x, y = r[5], r[6]
        level = r[8]
        health = int.from_bytes(r[9:11], "little", signed=True)
        max_health = int.from_bytes(r[11:13], "little", signed=True)
        direction = r[71]
        width, height = r[73], r[74]
        out.append(CreatureState(slot, active, attitude, monster_id, x, y, level,
                                 health, max_health, direction, width, height))
    return tuple(out)


def _find_all(haystack: bytes, needle: bytes):
    start = 0
    while True:
        pos = haystack.find(needle, start)
        if pos < 0:
            return
        yield pos
        start = pos + 1


def locate_source_map(town_data: bytes, live_terrain: bytes) -> TownSourceMatch:
    """Locate the live 64x64 x-major town map inside original TOWN.DAT.

    The live save differs slightly from the source because doors and scripted
    terrain can change. Exact 64-byte *columns* therefore vote for their source
    block and the best candidate is rescored byte-for-byte.
    """
    if len(live_terrain) != TOWN_TERRAIN_SIZE:
        raise ValueError(f"Expected {TOWN_TERRAIN_SIZE} live terrain bytes")
    votes: Counter[int] = Counter()
    occurrence_cap = 64
    for x in range(TOWN_GRID_W):
        col = live_terrain[x * 64:(x + 1) * 64]
        if len(set(col)) <= 1:
            continue
        occurrences = []
        for pos in _find_all(town_data, col):
            occurrences.append(pos)
            if len(occurrences) > occurrence_cap:
                break
        if len(occurrences) > occurrence_cap:
            continue
        for pos in occurrences:
            candidate = pos - x * 64
            if 0 <= candidate <= len(town_data) - TOWN_TERRAIN_SIZE:
                votes[candidate] += 1
    if not votes:
        raise ValueError("Could not locate a matching town map in TOWN.DAT")
    best = None
    for candidate, column_votes in votes.most_common(64):
        source = town_data[candidate:candidate + TOWN_TERRAIN_SIZE]
        exact_bytes = sum(a == b for a, b in zip(source, live_terrain))
        exact_cols = sum(source[x*64:(x+1)*64] == live_terrain[x*64:(x+1)*64]
                         for x in range(64))
        score = (exact_bytes, exact_cols, column_votes, -candidate)
        match = TownSourceMatch(candidate, exact_bytes, TOWN_TERRAIN_SIZE,
                                exact_cols, column_votes)
        if best is None or score > best[0]:
            best = (score, match)
    assert best is not None
    return best[1]

@dataclass(frozen=True)
class TownMapMatch:
    size: int
    source_offset: int
    exact_bytes: int
    total_bytes: int
    exact_columns: int
    column_votes: int

    @property
    def similarity(self) -> float:
        return self.exact_bytes / self.total_bytes if self.total_bytes else 0.0

    @property
    def confident(self) -> bool:
        """Whether the source-map match is strong enough for simulation bounds.

        Known reference towns score 99-100%. A much weaker result can occur
        when inactive rows/columns in the fixed 64x64 live save buffer retain
        data from a previously visited town. Such a match can still be useful
        diagnostically, but should not silently define movement bounds.
        """
        return self.similarity >= 0.75


class UncertainTownMapError(ValueError):
    def __init__(self, match: TownMapMatch):
        self.match = match
        super().__init__(
            f"Best TOWN.DAT source match is only {match.similarity:.2%} "
            f"({match.exact_bytes}/{match.total_bytes}) for {match.size}x{match.size}; "
            "active town size is not safe to use for movement yet"
        )


def compact_live_terrain(live_terrain: bytes, size: int) -> bytes:
    """Extract an active 32/48/64 town from the 64x64 live save buffer.

    The save always uses a 64-byte x stride, even when the original town is
    only 48x48 or 32x32.
    """
    if len(live_terrain) != TOWN_TERRAIN_SIZE:
        raise ValueError(f"Expected {TOWN_TERRAIN_SIZE} live terrain bytes")
    if size not in (32, 48, 64):
        raise ValueError("Town size must be 32, 48, or 64")
    return bytes(live_terrain[x * 64 + y] for x in range(size) for y in range(size))


def _locate_compact_source(town_data: bytes, compact: bytes, size: int) -> TownMapMatch:
    votes: Counter[int] = Counter()
    occurrence_cap = 96
    for x in range(size):
        col = compact[x * size:(x + 1) * size]
        if len(set(col)) <= 1:
            continue
        occurrences = []
        for pos in _find_all(town_data, col):
            occurrences.append(pos)
            if len(occurrences) > occurrence_cap:
                break
        if len(occurrences) > occurrence_cap:
            continue
        for pos in occurrences:
            candidate = pos - x * size
            if 0 <= candidate <= len(town_data) - size * size:
                votes[candidate] += 1
    if not votes:
        raise ValueError(f"Could not locate a matching {size}x{size} town map")
    best = None
    for candidate, column_votes in votes.most_common(96):
        source = town_data[candidate:candidate + size * size]
        exact_bytes = sum(a == b for a, b in zip(source, compact))
        exact_cols = sum(
            source[x*size:(x+1)*size] == compact[x*size:(x+1)*size]
            for x in range(size)
        )
        score = (exact_bytes / (size * size), exact_cols, column_votes, size, -candidate)
        match = TownMapMatch(size, candidate, exact_bytes, size * size, exact_cols, column_votes)
        if best is None or score > best[0]:
            best = (score, match)
    assert best is not None
    return best[1]


def locate_active_town_map(
    town_data: bytes,
    live_terrain: bytes,
    *,
    require_confident: bool = False,
) -> TownMapMatch:
    """Infer whether the current E3 town is 32x32, 48x48, or 64x64.

    Scores each legacy map size against TOWN.DAT. This is validated by the
    supplied Fort Emergence (64x64), New Cotra (48x48), and New Formello
    (48x48) saves. If ``require_confident`` is true, weak matches are rejected
    instead of allowing stale inactive save-buffer data to define simulation
    bounds.
    """
    candidates: list[TownMapMatch] = []
    for size in (64, 48, 32):
        compact = compact_live_terrain(live_terrain, size)
        try:
            candidates.append(_locate_compact_source(town_data, compact, size))
        except ValueError:
            pass
    if not candidates:
        raise ValueError("Could not locate current town source map at any legacy size")
    # Similarity first; exact-byte count breaks ties in favor of larger maps.
    best = max(candidates, key=lambda m: (m.similarity, m.exact_bytes, m.size))
    if require_confident and not best.confident:
        raise UncertainTownMapError(best)
    return best


def active_tile(live_terrain: bytes, x: int, y: int, size: int) -> int:
    if not 0 <= x < size or not 0 <= y < size:
        raise IndexError((x, y))
    # Live buffer always has a 64-byte x stride.
    return live_terrain[x * 64 + y]
