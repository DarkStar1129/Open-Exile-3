from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from openexile3.terrain import TERRAIN_COUNT, extract_terrain_picture_map


class TerrainTableTests(unittest.TestCase):
    def test_picture_signature_scanner(self) -> None:
        prefix = [0, 1, 2, 3, 4, 5, 6, 6, 7, 8, 8, 9, 10, 10, 11, 12, 12, 13, 14, 15, 16, 17, 18, 19]
        values = prefix + list(range(len(prefix), TERRAIN_COUNT))
        # Keep all values sane and distinct enough for the test.
        values = [v % 314 for v in values]
        payload = b"header-junk" + struct.pack("<" + "H" * TERRAIN_COUNT, *values) + b"tail"
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "fake.exe"
            path.write_bytes(payload)
            off, decoded = extract_terrain_picture_map(path)
        self.assertEqual(off, len(b"header-junk"))
        self.assertEqual(decoded[:24], tuple(prefix))
        self.assertEqual(len(decoded), TERRAIN_COUNT)


if __name__ == "__main__":
    unittest.main()
