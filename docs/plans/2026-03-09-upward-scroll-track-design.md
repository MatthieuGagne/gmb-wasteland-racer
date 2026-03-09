# Upward-Only Scrolling Track Design

**Date:** 2026-03-09
**Status:** Approved

## Summary

Replace the current 2D oval loop track with a fixed-length, upward-only scrolling track. The race always progresses upward; the camera never scrolls horizontally or backward. The player steers freely within the screen area but cannot push the camera down.

## Map Format

- **Dimensions:** 20 tiles wide × 100 tiles tall (160 × 800 px)
  - Width = screen width (160 px) — no horizontal camera movement needed
  - Height constant `MAP_TILES_H = 100` lives in `src/config.h` (tunable)
  - `MAP_TILES_W = 20` updated in `src/config.h`
- **Authoring:** Tiled (.tmx), same `tmx_to_c.py` pipeline — no new tools needed
- **ROM cost:** 20 × 100 = 2 000 bytes

## Camera (`camera.c`)

- `cam_x` removed; `move_bkg()` called with X = 0, Y = `cam_y` only
- All column-streaming code removed: `stream_column()`, left/right edge detection
- `cam_y` is monotonically increasing — `camera_update()` ignores any new Y ≤ current `cam_y`
- `camera_init()` preloads only the first 18 visible rows (not the full map)
- `CAM_MAX_X` constant removed; `CAM_MAX_Y` updated for new map height

## Player (`player.c`)

- Player X: clamped to screen bounds `[0, 159]` px
- Player screen Y: clamped to `[0, 143]` px — can move to the bottom edge but no further
- Camera Y never decreases, so moving down means falling behind — natural speed penalty

## Collision (`track.c`)

- `track_passable()` updated for `MAP_TILES_W = 20`
- Bounds check: `tx >= 20` or `ty >= 100` → impassable

## What Is Removed

- Horizontal camera scrolling (cam_x, CAM_MAX_X, column streaming)
- Backward camera movement
- Oval/loop map geometry

## What Is Unchanged

- `stream_row()` and VRAM ring buffer approach
- `tmx_to_c.py` asset pipeline
- Tile data / tileset
- Collision passability logic (just new bounds)
