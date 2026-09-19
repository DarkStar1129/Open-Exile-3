import unittest
from openexile3.outdoor import (
    OUTDOOR_RECORD_SIZE,OUTDOOR_TERRAIN_BYTES,SPECIAL_LOCS_OFFSET,SPECIAL_IDS_OFFSET,
    EXIT_LOCS_OFFSET,EXIT_DESTS_OFFSET,SIGN_LOCS_OFFSET,LABEL_BASE,REGION_LABEL_OFFSET,
    parse_outdoor_record,build_working_map,working_tile,OutdoorSector,
)

class OutdoorTests(unittest.TestCase):
    def test_compact_record_landmarks(self):
        raw=bytearray(OUTDOOR_RECORD_SIZE)
        # x-major tile (3,4)
        raw[3*48+4]=77
        raw[SPECIAL_LOCS_OFFSET:SPECIAL_LOCS_OFFSET+2]=bytes((11,12));raw[SPECIAL_IDS_OFFSET]=9
        raw[EXIT_LOCS_OFFSET:EXIT_LOCS_OFFSET+2]=bytes((36,36));raw[EXIT_DESTS_OFFSET]=21
        raw[SIGN_LOCS_OFFSET:SIGN_LOCS_OFFSET+2]=bytes((35,39))
        raw[LABEL_BASE:LABEL_BASE+9]=b'Near Fort'
        raw[REGION_LABEL_OFFSET:REGION_LABEL_OFFSET+5]=b'Upper'
        s=parse_outdoor_record(bytes(raw),89)
        self.assertEqual(s.tile(3,4),77)
        self.assertEqual((s.specials[0].x,s.specials[0].y,s.specials[0].special_id),(11,12,9))
        self.assertEqual((s.exits[0].x,s.exits[0].y,s.exits[0].town),(36,36,21))
        self.assertEqual((s.signs[0].x,s.signs[0].y),(35,39))
        self.assertEqual(s.labels[0],'Near Fort');self.assertEqual(s.region_label,'Upper')

    def test_working_map_stitches_four_x_major_sectors(self):
        sectors=[]
        for i in range(90):
            terr=bytes([i%256])*OUTDOOR_TERRAIN_BYTES
            sectors.append(OutdoorSector(i,terr,tuple('' for _ in range(8)),'',(),(),(),b''))
        w=build_working_map(sectors,7,8)
        self.assertEqual(working_tile(w,0,0),79)
        self.assertEqual(working_tile(w,48,0),80)
        self.assertEqual(working_tile(w,0,48),88)
        self.assertEqual(working_tile(w,48,48),89)

if __name__=='__main__':unittest.main()
