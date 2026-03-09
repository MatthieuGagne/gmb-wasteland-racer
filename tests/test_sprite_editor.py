import unittest
import tempfile
import os

from tools.sprite_editor.model import Palette, TileSheet


class TestPalette(unittest.TestCase):

    def test_default_has_4_colors(self):
        p = Palette()
        self.assertEqual(len(p.colors), 4)

    def test_set_color_stores_5bit_rgb(self):
        p = Palette()
        p.set_color(1, 31, 0, 15)
        self.assertEqual(p.colors[1], (31, 0, 15))

    def test_get_color_rgb888_max_red(self):
        p = Palette()
        p.set_color(0, 31, 0, 0)
        r, g, b = p.get_color_rgb888(0)
        self.assertEqual(r, 255)
        self.assertEqual(g, 0)
        self.assertEqual(b, 0)

    def test_get_color_rgb888_zero_is_black(self):
        p = Palette()
        p.set_color(0, 0, 0, 0)
        self.assertEqual(p.get_color_rgb888(0), (0, 0, 0))

    def test_get_color_rgb888_mid_value(self):
        # 20 * 255 // 31 = 164
        p = Palette()
        p.set_color(2, 20, 10, 5)
        r, g, b = p.get_color_rgb888(2)
        self.assertEqual(r, (20 * 255) // 31)
        self.assertEqual(g, (10 * 255) // 31)
        self.assertEqual(b, (5 * 255) // 31)


class TestTileSheet(unittest.TestCase):

    def test_initial_all_pixels_zero(self):
        ts = TileSheet()
        for y in range(TileSheet.HEIGHT):
            for x in range(TileSheet.WIDTH):
                self.assertEqual(ts.get_pixel(x, y), 0)

    def test_set_get_pixel(self):
        ts = TileSheet()
        ts.set_pixel(5, 3, 2)
        self.assertEqual(ts.get_pixel(5, 3), 2)

    def test_set_pixel_marks_dirty(self):
        ts = TileSheet()
        self.assertFalse(ts.dirty)
        ts.set_pixel(0, 0, 1)
        self.assertTrue(ts.dirty)

    def test_clear_resets_pixels(self):
        ts = TileSheet()
        ts.set_pixel(0, 0, 3)
        ts.clear()
        self.assertEqual(ts.get_pixel(0, 0), 0)

    def test_clear_clears_dirty_flag(self):
        ts = TileSheet()
        ts.set_pixel(0, 0, 1)
        ts.clear()
        self.assertFalse(ts.dirty)

    def test_dimensions(self):
        self.assertEqual(TileSheet.WIDTH, 32)
        self.assertEqual(TileSheet.HEIGHT, 32)


if __name__ == '__main__':
    unittest.main()
