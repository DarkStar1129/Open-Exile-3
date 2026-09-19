from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from openexile3.collision import _COLLISION_SIGNATURE, TERRAIN_COUNT, load_collision_table

class CollisionTests(unittest.TestCase):
    def test_scanner_and_semantics(self):
        vals=bytearray([0]*TERRAIN_COUNT)
        vals[:len(_COLLISION_SIGNATURE)]=_COLLISION_SIGNATURE
        vals[71]=3;vals[77]=4;vals[100]=5;vals[7]=1;vals[75]=2
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'fake.exe';p.write_bytes(b'abc'+vals+b'xyz')
            t=load_collision_table(p)
        self.assertEqual(t.file_offset,3)
        self.assertTrue(t.blocks_party(71));self.assertFalse(t.blocks_sight(71))
        self.assertTrue(t.blocks_projectiles(77));self.assertTrue(t.blocks_sight(100))
        self.assertFalse(t.blocks_party(7));self.assertTrue(t.blocks_monsters(75))

if __name__=='__main__':unittest.main()
