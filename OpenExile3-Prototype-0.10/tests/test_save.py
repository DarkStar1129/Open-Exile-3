from __future__ import annotations

import struct
import unittest

from openexile3.save import (
    CURRENT_TOWN_OFFSET,
    HEADER_SIZE,
    OUT_INFO_END,
    PARTY_END,
    PARTY_FOOD,
    PARTY_DIRECTION,
    PARTY_GOLD,
    PARTY_OFFSET,
    PARTY_SIZE,
    PARTY_UNKNOWN_06,
    PARTY_XOR,
    PC_COUNT,
    PC_CUR_HEALTH,
    PC_CUR_SP,
    PC_ITEMS,
    PC_ITEM_DISPLAY_NAME,
    PC_ITEM_SIZE,
    PC_MAX_HEALTH,
    PC_MAX_SP,
    PC_NAME,
    PC_WHICH_GRAPHIC,
    PC_OFFSET,
    PC_RECORD_SIZE,
    PC_XOR,
    SETUP_OFFSET,
    SETUP_SIZE,
    parse_save_bytes,
    set_gold_bytes,
)


def make_synthetic_save() -> bytes:
    data = bytearray(CURRENT_TOWN_OFFSET + 64)
    party = bytearray(PARTY_SIZE)
    struct.pack_into("<I", party, 0, 778)
    struct.pack_into("<H", party, PARTY_GOLD, 240)
    struct.pack_into("<H", party, PARTY_UNKNOWN_06, 0)
    struct.pack_into("<H", party, PARTY_FOOD, 130)
    struct.pack_into("<h", party, PARTY_DIRECTION, 2)
    data[PARTY_OFFSET:PARTY_END] = bytes(x ^ PARTY_XOR for x in party)

    for i in range(PC_COUNT):
        pc = bytearray(PC_RECORD_SIZE)
        name = f"PC{i+1}".encode()
        pc[PC_NAME:PC_NAME+len(name)] = name
        struct.pack_into("<h", pc, PC_MAX_HEALTH, 20+i)
        struct.pack_into("<h", pc, PC_CUR_HEALTH, 20+i)
        struct.pack_into("<h", pc, PC_MAX_SP, i)
        struct.pack_into("<h", pc, PC_CUR_SP, i)
        struct.pack_into("<h", pc, PC_WHICH_GRAPHIC, 3+i)
        item_name = b"Bronze Knife\x00"
        at = PC_ITEMS + PC_ITEM_DISPLAY_NAME
        pc[at:at+len(item_name)] = item_name
        start = PC_OFFSET + i * PC_RECORD_SIZE
        data[start:start+PC_RECORD_SIZE] = bytes(x ^ PC_XOR for x in pc)

    struct.pack_into("<Hh", data, CURRENT_TOWN_OFFSET, 21, 2)
    return bytes(data)


class SaveTests(unittest.TestCase):
    def test_layout_boundaries(self):
        self.assertEqual(HEADER_SIZE, 6)
        self.assertEqual(PARTY_END, 34091)
        self.assertEqual(SETUP_OFFSET, 34091)
        self.assertEqual(SETUP_SIZE, 16384)
        self.assertEqual(PC_OFFSET, 50475)
        self.assertEqual(OUT_INFO_END, CURRENT_TOWN_OFFSET)
        self.assertEqual(CURRENT_TOWN_OFFSET, 70647)

    def test_parse_known_fields(self):
        s = parse_save_bytes(make_synthetic_save())
        self.assertEqual(s.age, 778)
        self.assertEqual(s.day, 1)
        self.assertEqual(s.gold, 240)
        self.assertEqual(s.food, 130)
        self.assertEqual(s.current_town, 21)
        self.assertEqual(s.current_town_difficulty, 2)
        self.assertEqual(s.direction, 2)
        self.assertEqual(s.characters[0].name, "PC1")
        self.assertEqual(s.characters[0].max_health, 20)
        self.assertEqual(s.characters[0].inventory_names[0], "Bronze Knife")
        self.assertEqual(s.characters[0].which_graphic, 3)

    def test_set_gold_changes_only_two_encoded_bytes(self):
        before = make_synthetic_save()
        after = set_gold_bytes(before, 540)
        diffs = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
        self.assertEqual(diffs, [10, 11])
        self.assertEqual(parse_save_bytes(after).gold, 540)


if __name__ == "__main__":
    unittest.main()

class OutdoorInfoTests(unittest.TestCase):
    def test_outdoor_info_x_major_access(self):
        from openexile3.save import OUT_INFO_OFFSET, OUT_INFO_END, extract_outdoor_info, outdoor_info_at
        data=bytearray(OUT_INFO_END)
        data[OUT_INFO_OFFSET+84*96+85]=2
        info=extract_outdoor_info(bytes(data))
        self.assertEqual(outdoor_info_at(info,84,85),2)
