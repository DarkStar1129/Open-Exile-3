import unittest
from openexile3.location import (
    SAVE_MODE_OUTDOOR,SAVE_MODE_TOWN,SaveMode,
    PARTY_OUTDOOR_CORNER,PARTY_I_W_C,PARTY_P_LOC,PARTY_LOC_IN_SEC,
    parse_location_state,
)
from openexile3.save import PARTY_OFFSET,PARTY_SIZE,PARTY_END,PARTY_XOR


def make_save(mode:int,corner=(7,8),quad=(1,1),p=(84,85),local=(36,37)) -> bytes:
    data=bytearray(PARTY_END)
    data[0:2]=mode.to_bytes(2,'little')
    party=bytearray(PARTY_SIZE)
    for off,val in ((PARTY_OUTDOOR_CORNER,corner),(PARTY_I_W_C,quad),(PARTY_P_LOC,p),(PARTY_LOC_IN_SEC,local)):
        party[off:off+2]=bytes(val)
    data[PARTY_OFFSET:PARTY_END]=bytes(x^PARTY_XOR for x in party)
    return bytes(data)

class LocationTests(unittest.TestCase):
    def test_outdoor_location_invariant(self):
        s=parse_location_state(make_save(SAVE_MODE_OUTDOOR))
        self.assertIs(s.mode,SaveMode.OUTDOOR)
        self.assertEqual((s.outdoor.sector_x,s.outdoor.sector_y,s.outdoor.sector_index),(8,9,89))
        self.assertTrue(s.outdoor.invariant_ok)

    def test_town_mode_retains_outdoor_anchor(self):
        s=parse_location_state(make_save(SAVE_MODE_TOWN,quad=(0,0),p=(27,25),local=(27,25)))
        self.assertIs(s.mode,SaveMode.TOWN)
        self.assertEqual((s.outdoor.sector_x,s.outdoor.sector_y),(7,8))
        self.assertTrue(s.outdoor.invariant_ok)

if __name__=='__main__':unittest.main()
