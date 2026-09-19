import unittest

from openexile3.movement import (
    DIRECTION_BY_DELTA, DIRECTION_NAMES, direction_for_delta, normalize_outdoor_step
)
from openexile3.classic_render import clamp_camera_center


class DirectionTests(unittest.TestCase):
    def test_classic_direction_numbering(self):
        expected = {
            (0,-1):0,(1,-1):1,(1,0):2,(1,1):3,
            (0,1):4,(-1,1):5,(-1,0):6,(-1,-1):7,
        }
        self.assertEqual(DIRECTION_BY_DELTA, expected)
        self.assertEqual(DIRECTION_NAMES[2], "east")
        self.assertEqual(direction_for_delta(1,0), 2)
        self.assertEqual(direction_for_delta(-1,0), 6)

    def test_camera_clamp_for_wide_view_near_edge(self):
        # New Formello is 48x48; a 45-wide view centered at x=43 would spill
        # ten columns off-map. The clamped center is 25, covering x=3..47.
        self.assertEqual(clamp_camera_center(43,24,48,48,45,19),(25,24))
        self.assertEqual(clamp_camera_center(24,24,48,48,9,9),(24,24))

    def test_classic_outdoor_window_shift_math(self):
        # Near the left edge, a westward attempt shifts the 2x2 sector window
        # left and remaps the same absolute source tile by +48 working pixels.
        step=normalize_outdoor_step((3,4),(5,40),-1,0)
        self.assertEqual(step.corner,(2,4))
        self.assertEqual(step.source,(53,40))
        self.assertEqual(step.destination,(52,40))
        self.assertEqual(step.shifted,("left",))
        old_world=(3*48+5,4*48+40)
        new_world=(step.corner[0]*48+step.source[0],step.corner[1]*48+step.source[1])
        dest_world=(step.corner[0]*48+step.destination[0],step.corner[1]*48+step.destination[1])
        self.assertEqual(new_world,old_world)
        self.assertEqual(dest_world,(old_world[0]-1,old_world[1]))

    def test_diagonal_outdoor_window_shift_math(self):
        step=normalize_outdoor_step((3,4),(91,91),1,1)
        self.assertEqual(step.corner,(4,5))
        self.assertEqual(step.source,(43,43))
        self.assertEqual(step.destination,(44,44))
        self.assertEqual(step.shifted,("right","down"))

    def test_invalid_direction(self):
        with self.assertRaises(ValueError):
            direction_for_delta(0,0)
        with self.assertRaises(ValueError):
            direction_for_delta(2,0)


if __name__ == '__main__':
    unittest.main()
