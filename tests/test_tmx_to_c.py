#!/usr/bin/env python3
"""Unit tests for tools/tmx_to_c.py"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import tmx_to_c as conv
from tmx_to_c import gid_to_tile_id

# 3×2 map: Tiled IDs 1,2,1 / 2,1,2  →  GB values 0,1,0 / 1,0,1
MINIMAL_TMX = """\
<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" orientation="orthogonal"
     width="3" height="2" tilewidth="8" tileheight="8">
 <tileset firstgid="1" source="track.tsx"/>
 <layer id="1" name="Track" width="3" height="2">
  <data encoding="csv">
1,2,1,
2,1,2
  </data>
 </layer>
</map>
"""


class TestTmxToC(unittest.TestCase):

    def _convert(self, tmx_text):
        with tempfile.NamedTemporaryFile('w', suffix='.tmx', delete=False) as tf:
            tf.write(tmx_text)
            tmx_path = tf.name
        out_path = tmx_path.replace('.tmx', '.c')
        try:
            conv.tmx_to_c(tmx_path, out_path)
            with open(out_path) as f:
                return f.read()
        finally:
            os.unlink(tmx_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_generated_header_comment(self):
        result = self._convert(MINIMAL_TMX)
        self.assertIn('GENERATED', result)
        self.assertIn('do not edit by hand', result)

    def test_subtracts_one_from_tile_ids(self):
        result = self._convert(MINIMAL_TMX)
        # IDs 1,2,1 → 0,1,0 and 2,1,2 → 1,0,1
        self.assertIn('0,1,0', result)
        self.assertIn('1,0,1', result)

    def test_includes_track_header(self):
        result = self._convert(MINIMAL_TMX)
        self.assertIn('#include "track.h"', result)

    def test_defines_track_map_array(self):
        result = self._convert(MINIMAL_TMX)
        self.assertIn('track_map[MAP_TILES_H * MAP_TILES_W]', result)

    def test_wrong_encoding_raises(self):
        bad = MINIMAL_TMX.replace('encoding="csv"', 'encoding="base64"')
        with self.assertRaises(ValueError):
            self._convert(bad)


class TestGidToTileId(unittest.TestCase):

    def test_normal_tile_firstgid_1(self):
        # GID 1 with firstgid=1 → tile index 0
        self.assertEqual(gid_to_tile_id(1, 1), 0)

    def test_normal_tile_firstgid_2(self):
        # GID 3 with firstgid=2 → tile index 1
        self.assertEqual(gid_to_tile_id(3, 2), 1)

    def test_empty_cell_returns_zero(self):
        # GID 0 = empty cell → always 0 regardless of firstgid
        self.assertEqual(gid_to_tile_id(0, 1), 0)
        self.assertEqual(gid_to_tile_id(0, 2), 0)

    def test_hflip_stripped(self):
        # GID with H-flip bit set (0x80000001) and firstgid=1 → tile 0
        self.assertEqual(gid_to_tile_id(0x80000001, 1), 0)

    def test_vflip_stripped(self):
        # GID with V-flip bit set (0x40000002) and firstgid=1 → tile 1
        self.assertEqual(gid_to_tile_id(0x40000002, 1), 1)

    def test_all_flags_stripped(self):
        # GID with all flip bits set (0xF0000003) and firstgid=1 → tile 2
        self.assertEqual(gid_to_tile_id(0xF0000003, 1), 2)


if __name__ == '__main__':
    unittest.main()
