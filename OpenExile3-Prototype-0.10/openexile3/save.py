from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct

from .ne import decode_win16_string_resources

# Exile III Windows save layout recovered from a pair of saves made at the
# same game state, one of which was edited by the original EXILE3ED.EXE.
# Offsets are absolute, zero-based file offsets.
HEADER_SIZE = 6

PARTY_OFFSET = 6
PARTY_SIZE = 34_085
PARTY_END = PARTY_OFFSET + PARTY_SIZE
PARTY_XOR = 0x5C

SETUP_OFFSET = PARTY_END
SETUP_SIZE = 16_384  # 4 * 64 * 64
SETUP_END = SETUP_OFFSET + SETUP_SIZE

PC_OFFSET = SETUP_END
PC_COUNT = 6
PC_RECORD_SIZE = 1_826
PC_END = PC_OFFSET + PC_COUNT * PC_RECORD_SIZE
PC_XOR = 0x6B

OUT_INFO_OFFSET = PC_END
OUT_INFO_SIZE = 96 * 96
OUT_INFO_END = OUT_INFO_OFFSET + OUT_INFO_SIZE

CURRENT_TOWN_OFFSET = OUT_INFO_END

# Known offsets within the decoded party record.
PARTY_AGE = 0
PARTY_GOLD = 4
PARTY_UNKNOWN_06 = 6
PARTY_FOOD = 8

# Known offsets within each decoded PC record. These line up with the legacy
# Exile/Blades PC structure through the beginning of the inventory.
PC_MAIN_STATUS = 0
PC_NAME = 2
PC_NAME_SIZE = 20
PC_SKILLS = 22
PC_SKILL_COUNT = 30
PC_MAX_HEALTH = 82
PC_CUR_HEALTH = 84
PC_MAX_SP = 86
PC_CUR_SP = 88
PC_EXPERIENCE = 90
PC_SKILL_POINTS = 92
PC_LEVEL = 94
PC_STATUS = 96
PC_STATUS_COUNT = 15
PC_ITEMS = 126
PC_ITEM_COUNT = 24
PC_ITEM_SIZE = 63
PC_ITEM_DISPLAY_NAME = 23
PC_WHICH_GRAPHIC = 1786

# The first 19 skill slots line up with the published classic Exile/Blades
# structure. Remaining slots are preserved by index until E3-specific names
# are independently confirmed.
SKILL_NAMES = (
    "Strength", "Dexterity", "Intelligence", "Edged Weapon", "Bashing Weapon",
    "Pole Weapon", "Thrown Missile", "Archery", "Defense", "Mage Spells",
    "Priest Spells", "Mage Lore", "Alchemy", "Item Lore", "Disarm Traps",
    "Lockpicking", "Assassination", "Poison", "Luck",
) + tuple(f"Skill {i}" for i in range(19, PC_SKILL_COUNT))

# Confirmed by the one-tile-east save pair: decoded party direction changes
# from 6 to 2 while the town X coordinate changes 33 -> 34.
PARTY_DIRECTION = 33_562

# Exile III's Win16 resources store one 20-string town block per TOWN.DAT
# record. The first string in each block is the town name and the second is
# its nominal difficulty.
TOWN_STRING_BASE = 30_001
TOWN_STRING_STRIDE = 20


@dataclass(frozen=True)
class PlayerCharacterSummary:
    index: int
    name: str
    main_status: int
    max_health: int
    cur_health: int
    max_sp: int
    cur_sp: int
    experience: int
    skill_points: int
    level: int
    skills: tuple[int, ...]
    inventory_names: tuple[str, ...]
    which_graphic: int


@dataclass(frozen=True)
class SaveSummary:
    path: Path
    size: int
    header_hex: str
    age: int
    day: int
    gold: int
    party_unknown_06: int
    food: int
    current_town: int
    current_town_difficulty: int
    current_town_name: str | None
    direction: int
    characters: tuple[PlayerCharacterSummary, ...]


def _xor(data: bytes, key: int) -> bytes:
    return bytes(byte ^ key for byte in data)


def _cstring(data: bytes) -> str:
    raw = data.split(b"\x00", 1)[0]
    return raw.decode("cp1252", errors="replace").strip()


def decode_party_record(data: bytes) -> bytes:
    if len(data) < PARTY_END:
        raise ValueError("Save is too small to contain the Exile III party record")
    return _xor(data[PARTY_OFFSET:PARTY_END], PARTY_XOR)


def decode_pc_record(data: bytes, index: int) -> bytes:
    if not 0 <= index < PC_COUNT:
        raise IndexError(index)
    start = PC_OFFSET + index * PC_RECORD_SIZE
    end = start + PC_RECORD_SIZE
    if len(data) < end:
        raise ValueError("Save is too small to contain all six Exile III PC records")
    return _xor(data[start:end], PC_XOR)


def extract_town_name(exe_path: Path, town_number: int) -> str | None:
    if town_number < 0:
        return None
    strings = decode_win16_string_resources(exe_path)
    name = strings.get(TOWN_STRING_BASE + town_number * TOWN_STRING_STRIDE, "").strip()
    return name or None


def extract_town_resource_difficulty(exe_path: Path, town_number: int) -> int | None:
    strings = decode_win16_string_resources(exe_path)
    raw = strings.get(TOWN_STRING_BASE + town_number * TOWN_STRING_STRIDE + 1, "").strip()
    try:
        return int(raw)
    except ValueError:
        return None


def parse_save_bytes(data: bytes, *, path: Path | None = None, exe_path: Path | None = None) -> SaveSummary:
    if len(data) < CURRENT_TOWN_OFFSET + 4:
        raise ValueError(
            f"Save is {len(data):,} bytes; expected at least {CURRENT_TOWN_OFFSET + 4:,}"
        )

    party = decode_party_record(data)
    age = struct.unpack_from("<I", party, PARTY_AGE)[0]
    gold = struct.unpack_from("<H", party, PARTY_GOLD)[0]
    unknown_06 = struct.unpack_from("<H", party, PARTY_UNKNOWN_06)[0]
    food = struct.unpack_from("<H", party, PARTY_FOOD)[0]

    characters: list[PlayerCharacterSummary] = []
    for i in range(PC_COUNT):
        pc = decode_pc_record(data, i)
        inventory: list[str] = []
        for item_index in range(PC_ITEM_COUNT):
            item_start = PC_ITEMS + item_index * PC_ITEM_SIZE
            item = pc[item_start:item_start + PC_ITEM_SIZE]
            if len(item) != PC_ITEM_SIZE:
                break
            # The long/display name begins at byte 23 in the E3 item record.
            # We deliberately only decode the first NUL-terminated string here;
            # the remainder of the 63-byte item layout is not yet claimed.
            item_name = _cstring(item[PC_ITEM_DISPLAY_NAME:])
            if item_name:
                inventory.append(item_name)

        characters.append(
            PlayerCharacterSummary(
                index=i + 1,
                name=_cstring(pc[PC_NAME:PC_NAME + PC_NAME_SIZE]),
                main_status=struct.unpack_from("<h", pc, PC_MAIN_STATUS)[0],
                max_health=struct.unpack_from("<h", pc, PC_MAX_HEALTH)[0],
                cur_health=struct.unpack_from("<h", pc, PC_CUR_HEALTH)[0],
                max_sp=struct.unpack_from("<h", pc, PC_MAX_SP)[0],
                cur_sp=struct.unpack_from("<h", pc, PC_CUR_SP)[0],
                experience=struct.unpack_from("<h", pc, PC_EXPERIENCE)[0],
                skill_points=struct.unpack_from("<h", pc, PC_SKILL_POINTS)[0],
                level=struct.unpack_from("<h", pc, PC_LEVEL)[0],
                skills=tuple(struct.unpack_from(f"<{PC_SKILL_COUNT}h", pc, PC_SKILLS)),
                inventory_names=tuple(inventory),
                which_graphic=struct.unpack_from("<h", pc, PC_WHICH_GRAPHIC)[0],
            )
        )

    current_town, current_difficulty = struct.unpack_from("<Hh", data, CURRENT_TOWN_OFFSET)
    town_name = extract_town_name(exe_path, current_town) if exe_path else None

    return SaveSummary(
        path=path or Path("<memory>"),
        size=len(data),
        header_hex=data[:HEADER_SIZE].hex(" "),
        age=age,
        day=(age // 3700) + 1,
        gold=gold,
        party_unknown_06=unknown_06,
        food=food,
        current_town=current_town,
        current_town_difficulty=current_difficulty,
        current_town_name=town_name,
        direction=struct.unpack_from("<h", party, PARTY_DIRECTION)[0],
        characters=tuple(characters),
    )


def parse_save(path: Path, *, exe_path: Path | None = None) -> SaveSummary:
    return parse_save_bytes(path.read_bytes(), path=path, exe_path=exe_path)


def set_gold_bytes(data: bytes, gold: int) -> bytes:
    """Return a new save image with only the encoded gold field changed.

    This does not mutate the input bytes. The known gold field is a little-endian
    unsigned 16-bit value in the XOR-0x5C party record, at absolute offsets 10-11.
    """
    if not 0 <= gold <= 0xFFFF:
        raise ValueError("gold must be between 0 and 65535")
    if len(data) < PARTY_OFFSET + PARTY_GOLD + 2:
        raise ValueError("Save is too small")
    out = bytearray(data)
    plain = struct.pack("<H", gold)
    absolute = PARTY_OFFSET + PARTY_GOLD
    out[absolute:absolute + 2] = bytes(byte ^ PARTY_XOR for byte in plain)
    return bytes(out)


def extract_outdoor_info(data: bytes) -> bytes:
    """Return the 96x96 x-major outdoor explored/visibility buffer.

    In the supplied outdoor save, 0-valued cells exactly correspond to the
    black/unexplored cells in the original 9x9 viewport; nonzero cells are
    drawable. Values 1 and 2 both occur and are preserved verbatim.
    """
    if len(data) < OUT_INFO_END:
        raise ValueError("Save is too small to contain outdoor map/info data")
    return data[OUT_INFO_OFFSET:OUT_INFO_END]


def outdoor_info_at(info: bytes, x: int, y: int) -> int:
    if len(info) != OUT_INFO_SIZE:
        raise ValueError(f"Expected {OUT_INFO_SIZE} outdoor info bytes")
    if not 0 <= x < 96 or not 0 <= y < 96:
        raise IndexError((x, y))
    return info[x * 96 + y]
