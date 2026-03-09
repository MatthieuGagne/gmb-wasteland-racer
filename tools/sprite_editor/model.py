import struct
import zlib


class Palette:
    """4-color CGB palette stored as 5-bit RGB tuples."""

    def __init__(self):
        # Default: black, dark-grey, light-grey, white (5-bit)
        self.colors = [(0, 0, 0), (10, 10, 10), (21, 21, 21), (31, 31, 31)]

    def set_color(self, index, r5, g5, b5):
        """Set palette entry `index` to 5-bit RGB values (0–31 each)."""
        assert 0 <= index < 4
        assert all(0 <= c <= 31 for c in (r5, g5, b5))
        self.colors[index] = (r5, g5, b5)

    def get_color_rgb888(self, index):
        """Return (r, g, b) in 0–255 range for the given palette index."""
        r5, g5, b5 = self.colors[index]
        return (
            (r5 * 255) // 31,
            (g5 * 255) // 31,
            (b5 * 255) // 31,
        )


class TileSheet:
    """4×4 grid of 8×8 tiles — 32×32 pixels total, 4-color indexed."""

    COLS = 4
    ROWS = 4
    TILE_SIZE = 8
    WIDTH = COLS * TILE_SIZE   # 32
    HEIGHT = ROWS * TILE_SIZE  # 32

    def __init__(self):
        self.palette = Palette()
        self.pixels = [[0] * self.WIDTH for _ in range(self.HEIGHT)]
        self.dirty = False

    def set_pixel(self, x, y, color_index):
        """Paint pixel (x, y) with palette index 0–3."""
        self.pixels[y][x] = color_index
        self.dirty = True

    def get_pixel(self, x, y):
        return self.pixels[y][x]

    def clear(self):
        """Reset all pixels to index 0 and clear dirty flag."""
        self.pixels = [[0] * self.WIDTH for _ in range(self.HEIGHT)]
        self.dirty = False
