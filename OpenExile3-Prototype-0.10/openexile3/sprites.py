from __future__ import annotations

from pathlib import Path
from PIL import Image

from .ne import decode_win16_string_resources

CELL_W = 28
CELL_H = 36
MONSTER_NAME_BASE = 600

# Monster ID -> logical picture number. This table follows the classic
# Blades/Exile monster set; for the Fort Emergence validation set it selects
# the exact Guard graphic (monster 12 -> picture 11) seen in Exile III.
# Entries not present in the classic base set are -1 and are skipped.
_MONSTER_PICTURE_BY_ID = (
-1,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,21,22,23,23,24,25,26,27,28,29,30,31,3,32,33,34,35,36,37,38,39,40,41,43,44,45,46,47,46,47,48,49,50,51,52,53,54,55,42,57,58,58,56,59,60,61,62,63,64,65,66,67,68,69,68,70,70,70,71,72,73,74,75,76,76,77,78,79,80,81,82,83,84,85,86,87,88,88,89,89,90,90,91,91,92,93,94,95,96,97,98,99,100,106,101,102,102,103,56,149,104,71,56,60,66,105,69,107,108,109,110,71,111,112,113,114,115,116,117,118,119,120,121,120,121,119,123,124,125,126,127,128,49,51,50,51,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,55,68,140,157,156,158,159,166,165,170,155,155,171,
)
MONSTER_PICTURE_BY_ID = _MONSTER_PICTURE_BY_ID + (-1,) * (256 - len(_MONSTER_PICTURE_BY_ID))

# Logical monster picture -> packed graphics index. Derived from the GPLv2
# classic Blades of Exile Windows graphics table. Each sheet contains 20
# packed picture parts, with left/right facings in adjacent 28px columns.
_M_PIC_INDEX = (
1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,
21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,
41,42,43,44,46,47,48,49,50,51,53,55,57,59,60,61,62,63,64,65,
66,67,68,69,70,71,72,73,74,75,76,77,78,79,81,82,83,85,86,87,
88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,
108,109,111,112,113,114,116,117,118,119,120,122,123,125,127,128,129,130,131,135,
136,137,139,140,141,142,143,144,145,146,147,148,149,150,151,152,152,154,155,159,
160,164,166,168,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,185,
186,187,188,189,190,191,192,193,194,195,196,197,198,
)
M_PIC_INDEX = _M_PIC_INDEX + (0,) * (200 - len(_M_PIC_INDEX))

# Width/height of classic logical monster pictures. Most are 1x1; the full
# fidelity multi-tile cases can be expanded as additional validation samples
# become available. Fort Emergence creatures in the supplied sample are 1x1.


def _rgba_colorkey(im: Image.Image, key=(255,255,255)) -> Image.Image:
    src = im.convert("RGBA")
    px = src.load()
    for y in range(src.height):
        for x in range(src.width):
            r,g,b,a = px[x,y]
            if (r,g,b) == key:
                px[x,y] = (r,g,b,0)
    return src


def load_pc_sprite(data_dir: Path, which_graphic: int, direction: int) -> Image.Image | None:
    if which_graphic < 0 or which_graphic >= 100:
        return None
    with Image.open(data_dir / "PCS.BMP") as src:
        im = src.convert("RGB")
        col = 2 * (which_graphic // 8)
        row = which_graphic % 8
        if direction >= 4:
            col += 1
        box = (col*CELL_W, row*CELL_H, (col+1)*CELL_W, (row+1)*CELL_H)
        if box[2] > im.width or box[3] > im.height:
            return None
        return _rgba_colorkey(im.crop(box))


def monster_picture_for_id(monster_id: int) -> int | None:
    if not 0 <= monster_id < len(MONSTER_PICTURE_BY_ID):
        return None
    p = MONSTER_PICTURE_BY_ID[monster_id]
    return p if p >= 0 else None


def load_monster_sprite(data_dir: Path, monster_id: int, direction: int,
                        *, part: int = 0) -> Image.Image | None:
    pic = monster_picture_for_id(monster_id)
    if pic is None or not 0 <= pic < len(M_PIC_INDEX):
        return None
    packed = M_PIC_INDEX[pic] + part
    sheet = packed // 20 + 1
    local = packed % 20
    if not 1 <= sheet <= 9:
        return None
    # Original Windows code: mode 0 for directions <4, mode 1 otherwise.
    # In the original packed monster sheets, mode 0 is the first adjacent
    # facing column and mode 1 is the second. Screenshot validation against
    # Fort Emergence and New Cotra confirms this ordering.
    adj = 0 if direction < 4 else 1
    col = 2 * (local // 10) + adj
    row = local % 10
    path = data_dir / f"MONST{sheet}.BMP"
    if not path.exists():
        return None
    with Image.open(path) as src:
        im = src.convert("RGB")
        box = (col*CELL_W, row*CELL_H, (col+1)*CELL_W, (row+1)*CELL_H)
        if box[2] > im.width or box[3] > im.height:
            return None
        return _rgba_colorkey(im.crop(box))


def monster_name(exe_path: Path, monster_id: int) -> str:
    strings = decode_win16_string_resources(exe_path)
    value = strings.get(MONSTER_NAME_BASE + monster_id, "").strip()
    return value or f"Monster {monster_id}"
