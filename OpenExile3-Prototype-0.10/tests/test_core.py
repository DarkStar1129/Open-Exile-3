from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openexile3.outdoor import (
    LABEL_BASE,
    LABEL_SIZE,
    OUTDOOR_RECORD_SIZE,
    OUTDOOR_SECTOR_COUNT,
    REGION_LABEL_OFFSET,
    load_outdoor,
)


class OutdoorTests(unittest.TestCase):
    def test_synthetic_outdoor_records(self):
        records = []
        for i in range(OUTDOOR_SECTOR_COUNT):
            r = bytearray(OUTDOOR_RECORD_SIZE)
            r[: 48 * 48] = bytes([i % 255]) * (48 * 48)
            label = f"Label {i}".encode("ascii")
            r[LABEL_BASE : LABEL_BASE + len(label)] = label
            region = f"Region {i}".encode("ascii")
            r[REGION_LABEL_OFFSET : REGION_LABEL_OFFSET + len(region)] = region
            records.append(r)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "OUTDOOR.DAT"
            p.write_bytes(b"".join(records))
            sectors = load_outdoor(p)
            self.assertEqual(len(sectors), 90)
            self.assertEqual(sectors[0].labels[0], "Label 0")
            self.assertEqual(sectors[89].region_label, "Region 89")
            self.assertEqual(sectors[10].world_x, 1)
            self.assertEqual(sectors[10].world_y, 1)
            self.assertEqual(sectors[2].tile(3, 4), 2)

    def test_wrong_size_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "OUTDOOR.DAT"
            p.write_bytes(b"bad")
            with self.assertRaises(ValueError):
                load_outdoor(p)


if __name__ == "__main__":
    unittest.main()
