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
