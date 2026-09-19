import unittest
from openexile3.sprites import monster_picture_for_id,MONSTER_PICTURE_BY_ID,M_PIC_INDEX
class SpriteTests(unittest.TestCase):
    def test_guard_picture_mapping(self):
        self.assertEqual(monster_picture_for_id(12),11)
        self.assertEqual(M_PIC_INDEX[11],12)
    def test_tables_are_safely_sized(self):
        self.assertEqual(len(MONSTER_PICTURE_BY_ID),256)
        self.assertGreaterEqual(len(M_PIC_INDEX),199)
if __name__=='__main__':unittest.main()
