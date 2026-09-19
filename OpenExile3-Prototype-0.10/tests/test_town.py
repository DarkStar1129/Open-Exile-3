import unittest
from openexile3.town import (
    CURRENT_TOWN_CREATURES_OFFSET,CURRENT_TOWN_CREATURE_SIZE,CURRENT_TOWN_TERRAIN_OFFSET,
    CURRENT_TOWN_X_OFFSET,CURRENT_TOWN_Y_OFFSET,TOWN_TERRAIN_SIZE,
    extract_current_town_creatures,extract_current_town_position,extract_current_town_terrain,
    locate_source_map,tile,
)

class TownTests(unittest.TestCase):
    def test_x_major_tile_access(self):
        terr=bytearray(TOWN_TERRAIN_SIZE);terr[3*64+4]=77
        self.assertEqual(tile(bytes(terr),3,4),77)

    def test_extract_current_town_terrain_synthetic(self):
        data=bytearray(CURRENT_TOWN_TERRAIN_OFFSET+TOWN_TERRAIN_SIZE)
        expected=bytes((i*7)&255 for i in range(TOWN_TERRAIN_SIZE))
        data[CURRENT_TOWN_TERRAIN_OFFSET:CURRENT_TOWN_TERRAIN_OFFSET+TOWN_TERRAIN_SIZE]=expected
        self.assertEqual(extract_current_town_terrain(bytes(data)),expected)

    def test_position_and_creature_record(self):
        data=bytearray(CURRENT_TOWN_TERRAIN_OFFSET+TOWN_TERRAIN_SIZE)
        data[CURRENT_TOWN_X_OFFSET]=34;data[CURRENT_TOWN_Y_OFFSET]=28
        at=CURRENT_TOWN_CREATURES_OFFSET+38*CURRENT_TOWN_CREATURE_SIZE
        r=bytearray(CURRENT_TOWN_CREATURE_SIZE)
        r[0:2]=(1).to_bytes(2,'little',signed=True);r[2:4]=(2).to_bytes(2,'little',signed=True)
        r[4]=12;r[5]=37;r[6]=24;r[8]=30;r[9:11]=(140).to_bytes(2,'little',signed=True);r[11:13]=(140).to_bytes(2,'little',signed=True)
        r[71]=4;r[73]=1;r[74]=1;data[at:at+len(r)]=r
        self.assertEqual(extract_current_town_position(bytes(data)),(34,28))
        c=extract_current_town_creatures(bytes(data))[38]
        self.assertEqual((c.monster_id,c.x,c.y,c.direction,c.health),(12,37,24,4,140))
        self.assertTrue(c.populated)

    def test_locate_source_map_with_live_changes(self):
        prefix=bytes([17])*123
        source=bytes(((x//8)+(y//8)*11)&255 for x in range(64) for y in range(64))
        town_data=prefix+source+bytes([33])*211
        live=bytearray(source)
        for pos in (5,500,999,1700,2600,3500):live[pos]^=0x3F
        match=locate_source_map(town_data,bytes(live))
        self.assertEqual(match.source_offset,len(prefix));self.assertEqual(match.exact_bytes,TOWN_TERRAIN_SIZE-6)
        self.assertGreater(match.similarity,.99)

if __name__=='__main__':unittest.main()

class VariableTownTests(unittest.TestCase):
    def test_compact_live_48_stride(self):
        from openexile3.town import compact_live_terrain
        live=bytearray(TOWN_TERRAIN_SIZE)
        expected=bytearray()
        for x in range(48):
            for y in range(48):
                v=(x*3+y*5)&255;live[x*64+y]=v;expected.append(v)
        self.assertEqual(compact_live_terrain(bytes(live),48),bytes(expected))
