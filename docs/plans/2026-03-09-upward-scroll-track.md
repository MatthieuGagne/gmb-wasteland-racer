# Upward-Only Scrolling Track Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the 40×36 oval-loop track with a 20×100 upward-only scrolling track where `cam_y` is monotonically increasing and horizontal scrolling is fully removed.

**Architecture:** The camera drops from 2D (cam_x + cam_y) to 1D (cam_y only). `stream_column()` and all left/right edge detection are removed. `stream_row()` simplifies (MAP_TILES_W=20 ≤ 32, no VRAM X-wrap). `cam_y` becomes `uint16_t` (max 656 > uint8_t). Player gains explicit screen-Y clamping so it can't drift above the camera.

**Tech Stack:** GBDK-2020, SDCC, Unity test framework (gcc host-side), Tiled + tmx_to_c.py pipeline

**Design doc:** `docs/plans/2026-03-09-upward-scroll-track-design.md`

**GitHub issue:** #24

---

### Task 1: Update map-dimension constants

**Files:**
- Modify: `src/config.h`
- Modify: `src/track.h`

**Step 1: Update `src/config.h`**

```c
#ifndef CONFIG_H
#define CONFIG_H

#define MAX_NPCS     6

#define MAP_TILES_W  20u
#define MAP_TILES_H  100u

#endif /* CONFIG_H */
```

**Step 2: Update `src/track.h`** — include config.h, remove old defines, update pixel dimensions

```c
#ifndef TRACK_H
#define TRACK_H

#include <stdint.h>
#include "config.h"

#define MAP_PX_W  160u   /* MAP_TILES_W * 8 */
#define MAP_PX_H  800u   /* MAP_TILES_H * 8 */

extern const uint8_t track_map[];

void    track_init(void);
uint8_t track_passable(int16_t world_x, int16_t world_y);

#endif /* TRACK_H */
```

**Step 3: Commit**

```bash
git add src/config.h src/track.h
git commit -m "chore: move MAP_TILES_W/H to config.h, update to 20x100"
```

> Note: `make test` will now fail — existing tests reference old map geometry. That's expected; fixed in subsequent tasks.

---

### Task 2: Author new 20×100 Tiled map and regenerate `track_map.c`

**Files:**
- Modify: `assets/maps/track.tmx`
- Modify: `src/track_map.c` (generated)

**Track geometry:**
- Rows 0–49: straight — road at cols 4–15 (12 tiles wide)
- Rows 50–74: curve right — road at cols 5–16 (shifted 1)
- Rows 75–99: straight — road at cols 6–17 (shifted 2 total)
- GID 1 = off-track (→ track_map value 0), GID 2 = road (→ track_map value 1)

**Step 1: Generate the new TMX**

```bash
python3 - << 'PYEOF'
straight = "1,1,1,1,2,2,2,2,2,2,2,2,2,2,2,2,1,1,1,1"
curve    = "1,1,1,1,1,2,2,2,2,2,2,2,2,2,2,2,2,1,1,1"
final    = "1,1,1,1,1,1,2,2,2,2,2,2,2,2,2,2,2,2,1,1"
rows = [straight]*50 + [curve]*25 + [final]*25
header = '''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" tiledversion="1.10.0"
     orientation="orthogonal" renderorder="right-down"
     width="20" height="100" tilewidth="8" tileheight="8"
     infinite="0" nextlayerid="2" nextobjectid="1">
 <tileset firstgid="1" source="track.tsx"/>
 <layer id="1" name="Track" width="20" height="100">
  <data encoding="csv">
'''
footer = "  </data>\n </layer>\n</map>\n"
with open("assets/maps/track.tmx", "w") as f:
    f.write(header)
    f.write(",\n".join(rows) + "\n")
    f.write(footer)
print("Written assets/maps/track.tmx")
PYEOF
```

**Step 2: Regenerate `src/track_map.c`**

```bash
python3 tools/tmx_to_c.py assets/maps/track.tmx src/track_map.c
```

Expected: `src/track_map.c` now has 100 rows, 20 values each. Verify:

```bash
grep -c "row" src/track_map.c
```

Expected output: `100`

**Step 3: Commit**

```bash
git add assets/maps/track.tmx src/track_map.c
git commit -m "feat: author 20x100 upward track with one right-shift curve"
```

---

### Task 3: Rewrite camera — tests, implementation, main.c update

**Files:**
- Modify: `tests/test_camera.c`
- Modify: `src/camera.h`
- Modify: `src/camera.c`
- Modify: `src/main.c`

**Step 1: Write new `tests/test_camera.c`** (replaces old file entirely)

Key behavioral changes under test:
- `cam_y` is `uint16_t`, max 656 (= 100×8 − 144), never negative
- `camera_init` preloads exactly 18 rows (not all 100)
- `camera_update` never decreases `cam_y`
- No cam_x, no column streaming

```c
#include "unity.h"
#include <gb/gb.h>
#include "camera.h"
#include "track.h"

void setUp(void)    { mock_vram_clear(); }
void tearDown(void) {}

/* --- camera_init: cam_y from player world Y ----------------------------- */

/* Player at world y=80: cam_y = max(80-72, 0) = 8 */
void test_camera_init_sets_cam_y(void) {
    camera_init(80, 80);
    TEST_ASSERT_EQUAL_UINT16(8, cam_y);
}

/* --- camera_init: clamp at edges ---------------------------------------- */

/* Player near top: cam_y cannot go negative */
void test_camera_init_clamps_cam_y_to_zero(void) {
    camera_init(80, 40);  /* 40-72 = -32 → 0 */
    TEST_ASSERT_EQUAL_UINT16(0, cam_y);
}

/* Player past bottom: cam_y capped at CAM_MAX_Y = 656 */
void test_camera_init_clamps_cam_y_to_max(void) {
    camera_init(80, 800);  /* 800-72=728 > 656 → 656 */
    TEST_ASSERT_EQUAL_UINT16(656, cam_y);
}

/* --- camera_init: preloads exactly 18 rows, not all 100 ----------------- */

void test_camera_init_preloads_18_rows(void) {
    /* cam_y=8 → first_row=1; preloads rows 1-18 = 18 set_bkg_tiles calls */
    camera_init(80, 80);
    TEST_ASSERT_EQUAL_INT(18, mock_set_bkg_tiles_call_count);
}

/* --- camera_update: monotonically increasing cam_y --------------------- */

/* Moving player backward must not decrease cam_y */
void test_camera_update_cam_y_never_decreases(void) {
    camera_init(80, 80);    /* cam_y = 8 */
    camera_update(80, 40);  /* desired 40-72=-32→0 ≤ 8 → no change */
    TEST_ASSERT_EQUAL_UINT16(8, cam_y);
}

/* Moving player forward advances cam_y */
void test_camera_update_cam_y_advances(void) {
    camera_init(80, 80);     /* cam_y = 8 */
    camera_update(80, 200);  /* 200-72=128 > 8 → cam_y = 128 */
    TEST_ASSERT_EQUAL_UINT16(128, cam_y);
}

/* cam_y never exceeds CAM_MAX_Y */
void test_camera_update_cam_y_clamped_at_max(void) {
    camera_init(80, 80);
    camera_update(80, 9999);  /* clamped to 656 */
    TEST_ASSERT_EQUAL_UINT16(656, cam_y);
}

/* --- camera_update: buffers rows, does NOT write VRAM directly ---------- */

void test_camera_update_does_not_write_vram(void) {
    int count_after_init;
    camera_init(80, 80);
    count_after_init = mock_set_bkg_tiles_call_count;
    camera_update(80, 200);  /* buffers new rows */
    TEST_ASSERT_EQUAL_INT(count_after_init, mock_set_bkg_tiles_call_count);
}

/* --- camera_flush_vram: drains pending row streams --------------------- */

/* Crossing tile boundary → flush writes exactly one new row */
void test_camera_flush_streams_new_bottom_row(void) {
    int count_after_update;
    /* cam_y=8, old_bot=(8+143)/8=18; advance to cam_y=16, new_bot=(16+143)/8=19 */
    camera_init(80, 80);
    camera_update(80, 88);  /* cam_y→16, buffers row 19 */
    count_after_update = mock_set_bkg_tiles_call_count;
    camera_flush_vram();
    TEST_ASSERT_GREATER_THAN_INT(count_after_update, mock_set_bkg_tiles_call_count);
}

/* Second flush must be a no-op */
void test_camera_flush_clears_buffer(void) {
    int count_after_first;
    camera_init(80, 80);
    camera_update(80, 88);
    camera_flush_vram();
    count_after_first = mock_set_bkg_tiles_call_count;
    camera_flush_vram();
    TEST_ASSERT_EQUAL_INT(count_after_first, mock_set_bkg_tiles_call_count);
}

/* No-op when buffer is empty */
void test_camera_flush_noop_on_empty_buffer(void) {
    camera_init(80, 80);
    mock_set_bkg_tiles_call_count = 0;
    camera_flush_vram();
    TEST_ASSERT_EQUAL_INT(0, mock_set_bkg_tiles_call_count);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_camera_init_sets_cam_y);
    RUN_TEST(test_camera_init_clamps_cam_y_to_zero);
    RUN_TEST(test_camera_init_clamps_cam_y_to_max);
    RUN_TEST(test_camera_init_preloads_18_rows);
    RUN_TEST(test_camera_update_cam_y_never_decreases);
    RUN_TEST(test_camera_update_cam_y_advances);
    RUN_TEST(test_camera_update_cam_y_clamped_at_max);
    RUN_TEST(test_camera_update_does_not_write_vram);
    RUN_TEST(test_camera_flush_streams_new_bottom_row);
    RUN_TEST(test_camera_flush_clears_buffer);
    RUN_TEST(test_camera_flush_noop_on_empty_buffer);
    return UNITY_END();
}
```

**Step 2: Run tests — expect camera tests to FAIL**

```bash
GBDK_HOME=/home/mathdaman/gbdk make test 2>&1 | grep -E "(test_camera|FAIL|PASS|OK)"
```

Expected: camera tests fail (old implementation doesn't match new behavior).

**Step 3: Rewrite `src/camera.h`** — remove `cam_x`, change `cam_y` to `uint16_t`

```c
#ifndef CAMERA_H
#define CAMERA_H

#include <stdint.h>

/* Current camera scroll Y in world pixels. Range [0, 656] — requires uint16_t. */
extern uint16_t cam_y;

/* Call once when entering STATE_PLAYING (after track_init).
 * Preloads the 18 initial visible rows and sets cam_y. */
void camera_init(int16_t player_world_x, int16_t player_world_y);

/* Call every frame in game-logic phase. Advances cam_y monotonically and
 * buffers any new bottom-row streams. Does NOT write VRAM directly. */
void camera_update(int16_t player_world_x, int16_t player_world_y);

/* Call in VBlank phase after wait_vbl_done(). Drains buffered row streams. */
void camera_flush_vram(void);

#endif /* CAMERA_H */
```

**Step 4: Rewrite `src/camera.c`**

```c
#include <gb/gb.h>
#include "camera.h"
#include "track.h"

uint16_t cam_y;

/* CAM_MAX_Y = (MAP_TILES_H * 8) - 144 = (100*8) - 144 = 656 */
#define CAM_MAX_Y  656u

/* Write one full world row into the VRAM ring buffer.
 * VRAM y slot = world_ty % 32. MAP_TILES_W=20 <= 32: no X wrapping needed. */
static void stream_row(uint8_t world_ty) {
    static uint8_t row_buf[MAP_TILES_W];
    uint8_t tx;
    uint8_t vram_y = world_ty & 31u;

    for (tx = 0u; tx < MAP_TILES_W; tx++) {
        row_buf[tx] = track_map[(uint16_t)world_ty * MAP_TILES_W + tx];
    }
    set_bkg_tiles(0u, vram_y, MAP_TILES_W, 1u, row_buf);
}

#define STREAM_BUF_SIZE 4u

static uint8_t stream_buf[STREAM_BUF_SIZE];
static uint8_t stream_buf_len = 0u;

/* Clamp signed v to [0, max]. */
static uint16_t clamp_cam(int16_t v, uint16_t max) {
    if (v < 0) return 0u;
    if ((uint16_t)v > max) return max;
    return (uint16_t)v;
}

void camera_init(int16_t player_world_x, int16_t player_world_y) {
    uint8_t ty;
    uint8_t first_row;
    (void)player_world_x;  /* cam_x is always 0; no horizontal scroll */

    cam_y = clamp_cam(player_world_y - 72, CAM_MAX_Y);
    first_row = (uint8_t)(cam_y >> 3u);

    /* Preload only the 18 initially visible rows, not all 100 */
    for (ty = first_row; ty < first_row + 18u && ty < MAP_TILES_H; ty++) {
        stream_row(ty);
    }

    move_bkg(0u, (uint8_t)cam_y);
}

void camera_update(int16_t player_world_x, int16_t player_world_y) {
    uint16_t ncy;
    (void)player_world_x;

    ncy = clamp_cam(player_world_y - 72, CAM_MAX_Y);
    if (ncy <= cam_y) return;  /* monotonic: never scroll backward */

    /* Buffer bottom row when bottom viewport edge crosses a tile boundary */
    {
        uint8_t old_bot = (uint8_t)((cam_y + 143u) >> 3u);
        uint8_t new_bot = (uint8_t)((ncy  + 143u) >> 3u);
        if (new_bot != old_bot && new_bot < MAP_TILES_H
                && stream_buf_len < STREAM_BUF_SIZE) {
            stream_buf[stream_buf_len] = new_bot;
            stream_buf_len++;
        }
    }

    cam_y = ncy;
}

void camera_flush_vram(void) {
    uint8_t i;
    for (i = 0u; i < stream_buf_len; i++) {
        stream_row(stream_buf[i]);
    }
    stream_buf_len = 0u;
}
```

**Step 5: Update `src/main.c`** — remove `cam_x` reference

Change line `move_bkg(cam_x, cam_y);` to:

```c
move_bkg(0u, (uint8_t)cam_y);
```

**Step 6: Run camera tests — expect PASS**

```bash
GBDK_HOME=/home/mathdaman/gbdk make test 2>&1 | grep -E "(test_camera|FAIL|OK)"
```

Expected: all camera tests PASS. (track/player tests still failing — fixed next.)

**Step 7: Commit**

```bash
git add tests/test_camera.c src/camera.h src/camera.c src/main.c
git commit -m "feat: rewrite camera for upward-only 1D scroll, cam_y uint16_t"
```

---

### Task 4: Update `tests/test_track.c` for new map geometry

**Files:**
- Modify: `tests/test_track.c`

Track geometry reminder (from Task 2 TMX):
- Rows 0–49: road at cols 4–15. On-track: x ∈ [32, 127], y ∈ [0, 399]
- Rows 50–74: road at cols 5–16. On-track: x ∈ [40, 135], y ∈ [400, 599]
- Rows 75–99: road at cols 6–17. On-track: x ∈ [48, 143], y ∈ [600, 799]
- Off-track: x=24 (col 3) at any row; x=128 (col 16) in rows 0-49; x=160 (OOB); y=800 (OOB)

**Step 1: Replace `tests/test_track.c`**

```c
#include "unity.h"
#include "track.h"

void setUp(void)    {}
void tearDown(void) {}

/* --- on-track: straight section (rows 0-49, road cols 4-15) ------------ */

/* Center of road: tile (10, 10) = world (80, 80) */
void test_track_passable_straight_center(void) {
    TEST_ASSERT_EQUAL_UINT8(1, track_passable(80, 80));
}

/* Left road edge: tile (4, 10) = world (32, 80) */
void test_track_passable_straight_left_edge(void) {
    TEST_ASSERT_EQUAL_UINT8(1, track_passable(32, 80));
}

/* Right road edge: tile (15, 10) = world (120, 80) */
void test_track_passable_straight_right_edge(void) {
    TEST_ASSERT_EQUAL_UINT8(1, track_passable(120, 80));
}

/* --- off-track: straight section --------------------------------------- */

/* Left sand: tile (3, 10) = world (24, 80) */
void test_track_impassable_straight_left_sand(void) {
    TEST_ASSERT_EQUAL_UINT8(0, track_passable(24, 80));
}

/* Right sand: tile (16, 10) = world (128, 80) */
void test_track_impassable_straight_right_sand(void) {
    TEST_ASSERT_EQUAL_UINT8(0, track_passable(128, 80));
}

/* --- on-track: curve section (rows 50-74, road cols 5-16) -------------- */

/* Center of curve: tile (11, 51) = world (88, 408) */
void test_track_passable_curve_center(void) {
    TEST_ASSERT_EQUAL_UINT8(1, track_passable(88, 408));
}

/* --- off-track: curve section (col 17 = x=136 is sand) ---------------- */

void test_track_impassable_curve_right_sand(void) {
    TEST_ASSERT_EQUAL_UINT8(0, track_passable(136, 408));
}

/* --- off-track: bounds checks ------------------------------------------ */

/* Beyond map width: tx = 20 >= MAP_TILES_W */
void test_track_impassable_out_of_bounds_x(void) {
    TEST_ASSERT_EQUAL_UINT8(0, track_passable(160, 80));
}

/* Beyond map height: ty = 100 >= MAP_TILES_H */
void test_track_impassable_out_of_bounds_y(void) {
    TEST_ASSERT_EQUAL_UINT8(0, track_passable(80, 800));
}

/* Negative world coords */
void test_track_impassable_negative_x(void) {
    TEST_ASSERT_EQUAL_UINT8(0, track_passable(-1, 80));
}

void test_track_impassable_negative_y(void) {
    TEST_ASSERT_EQUAL_UINT8(0, track_passable(80, -1));
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_track_passable_straight_center);
    RUN_TEST(test_track_passable_straight_left_edge);
    RUN_TEST(test_track_passable_straight_right_edge);
    RUN_TEST(test_track_impassable_straight_left_sand);
    RUN_TEST(test_track_impassable_straight_right_sand);
    RUN_TEST(test_track_passable_curve_center);
    RUN_TEST(test_track_impassable_curve_right_sand);
    RUN_TEST(test_track_impassable_out_of_bounds_x);
    RUN_TEST(test_track_impassable_out_of_bounds_y);
    RUN_TEST(test_track_impassable_negative_x);
    RUN_TEST(test_track_impassable_negative_y);
    return UNITY_END();
}
```

**Step 2: Run tests — expect track + camera tests to PASS**

```bash
GBDK_HOME=/home/mathdaman/gbdk make test 2>&1 | grep -E "(test_camera|test_track|FAIL|OK)"
```

Expected: all camera and track tests PASS. (player tests still failing.)

**Step 3: Commit**

```bash
git add tests/test_track.c
git commit -m "test: update track tests for 20x100 map geometry"
```

---

### Task 5: Update player — tests first, then implementation

**Files:**
- Modify: `tests/test_player.c`
- Modify: `src/player.c`

Player changes:
- Start: `PLAYER_START_X = 80`, `PLAYER_START_Y = 80` (visible in initial viewport)
- X clamp: `new_px ∈ [0, 159]` explicit guard in `player_update`
- Y clamp: `new_py ∈ [cam_y, cam_y + 143]` guard using `cam_y` from `camera.h`
- `player_render`: remove `cam_x` term; handle `uint16_t cam_y`

**Step 1: Write new `tests/test_player.c`** (replaces old file)

setUp calls `camera_init(80, 80)` so `cam_y = 8` for all tests.

```c
#include "unity.h"
#include <gb/gb.h>
#include "player.h"
#include "camera.h"

void setUp(void) {
    mock_vram_clear();
    camera_init(80, 80);  /* cam_y = 8 */
    player_init();
}
void tearDown(void) {}

/* --- start position ---------------------------------------------------- */

void test_player_init_sets_start_position(void) {
    TEST_ASSERT_EQUAL_INT16(80, player_get_x());
    TEST_ASSERT_EQUAL_INT16(80, player_get_y());
}

/* --- basic movement from start (80,80) on road (cols 4-15, row 10) ----- */

void test_player_update_moves_left(void) {
    player_update(J_LEFT);
    TEST_ASSERT_EQUAL_INT16(79, player_get_x());
}

void test_player_update_moves_right(void) {
    player_update(J_RIGHT);
    TEST_ASSERT_EQUAL_INT16(81, player_get_x());
}

void test_player_update_moves_up(void) {
    player_update(J_UP);
    TEST_ASSERT_EQUAL_INT16(79, player_get_y());
}

void test_player_update_moves_down(void) {
    player_update(J_DOWN);
    TEST_ASSERT_EQUAL_INT16(81, player_get_y());
}

/* --- track collision (new map geometry) -------------------------------- */

/* Left wall: tile col 3 (x=24-31) is off-track for rows 0-49 */
void test_player_blocked_by_left_wall(void) {
    player_set_pos(32, 80);   /* leftmost road tile (col 4, x=32) */
    player_update(J_LEFT);    /* new_px=31 → col 3 → off-track → blocked */
    TEST_ASSERT_EQUAL_INT16(32, player_get_x());
}

/* Right wall: corner px+7=128 → tile col 16 → off-track */
void test_player_blocked_by_right_wall(void) {
    player_set_pos(120, 80);  /* rightmost safe: corner at 127 (col 15, road) */
    player_update(J_RIGHT);   /* new_px=121 → corner at 128 (col 16) → off-track */
    TEST_ASSERT_EQUAL_INT16(120, player_get_x());
}

/* --- screen X clamp [0, 159] ------------------------------------------- */

void test_player_clamped_at_screen_left(void) {
    player_set_pos(0, 80);
    player_update(J_LEFT);    /* new_px=-1 < 0 → blocked */
    TEST_ASSERT_EQUAL_INT16(0, player_get_x());
}

void test_player_clamped_at_screen_right(void) {
    player_set_pos(159, 80);
    player_update(J_RIGHT);   /* new_px=160 > 159 → blocked */
    TEST_ASSERT_EQUAL_INT16(159, player_get_x());
}

/* --- screen Y clamp [cam_y, cam_y+143] ---------------------------------- */

/* cam_y=8. Player at py=8 (top of screen). Track at (80,7) IS passable
 * (col 10, row 0 = road), so ONLY screen clamp prevents upward movement. */
void test_player_clamped_at_screen_top(void) {
    player_set_pos(80, 8);    /* py == cam_y: at top of viewport */
    player_update(J_UP);      /* new_py=7 < cam_y=8 → blocked */
    TEST_ASSERT_EQUAL_INT16(8, player_get_y());
}

/* cam_y=8, cam_y+143=151. Track at (80,152) IS passable (col 10, row 19 = road),
 * so ONLY screen clamp prevents downward movement past screen bottom. */
void test_player_clamped_at_screen_bottom(void) {
    player_set_pos(80, 151);  /* py == cam_y+143: at bottom of viewport */
    player_update(J_DOWN);    /* new_py=152 > cam_y+143=151 → blocked */
    TEST_ASSERT_EQUAL_INT16(151, player_get_y());
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_player_init_sets_start_position);
    RUN_TEST(test_player_update_moves_left);
    RUN_TEST(test_player_update_moves_right);
    RUN_TEST(test_player_update_moves_up);
    RUN_TEST(test_player_update_moves_down);
    RUN_TEST(test_player_blocked_by_left_wall);
    RUN_TEST(test_player_blocked_by_right_wall);
    RUN_TEST(test_player_clamped_at_screen_left);
    RUN_TEST(test_player_clamped_at_screen_right);
    RUN_TEST(test_player_clamped_at_screen_top);
    RUN_TEST(test_player_clamped_at_screen_bottom);
    return UNITY_END();
}
```

**Step 2: Run tests — expect player tests to FAIL**

```bash
GBDK_HOME=/home/mathdaman/gbdk make test 2>&1 | grep -E "(test_player|FAIL)"
```

Expected: player tests fail (old start pos 160,256; no screen clamp).

**Step 3: Update `src/player.c`**

```c
#include <gb/gb.h>
#include "player.h"
#include "track.h"
#include "camera.h"

/* Solid 8x8 sprite: all pixels color index 3 */
static const uint8_t player_tile_data[] = {
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF
};

/* Player start: center of initial viewport, on road (tile col 10, row 10) */
#define PLAYER_START_X  80
#define PLAYER_START_Y  80

static int16_t px;
static int16_t py;

/* Returns 1 if all 4 corners of a player at world (wx, wy) are on track. */
static uint8_t corners_passable(int16_t wx, int16_t wy) {
    return track_passable(wx,       wy) &&
           track_passable(wx + 7,   wy) &&
           track_passable(wx,       wy + 7) &&
           track_passable(wx + 7,   wy + 7);
}

void player_init(void) {
    SPRITES_8x8;
    set_sprite_data(0, 1, player_tile_data);
    set_sprite_tile(0, 0);
    px = PLAYER_START_X;
    py = PLAYER_START_Y;
    SHOW_SPRITES;
}

void player_update(uint8_t input) {
    int16_t new_px;
    int16_t new_py;
    if (input & J_LEFT) {
        new_px = px - 1;
        if (new_px >= 0 && corners_passable(new_px, py)) px = new_px;
    }
    if (input & J_RIGHT) {
        new_px = px + 1;
        if (new_px <= 159 && corners_passable(new_px, py)) px = new_px;
    }
    if (input & J_UP) {
        new_py = py - 1;
        if (new_py >= (int16_t)cam_y && corners_passable(px, new_py)) py = new_py;
    }
    if (input & J_DOWN) {
        new_py = py + 1;
        if (new_py <= (int16_t)cam_y + 143 && corners_passable(px, new_py)) py = new_py;
    }
}

void player_render(void) {
    /* cam_x is always 0; use uint16_t cam_y safely since py >= cam_y is enforced */
    uint8_t hw_x = (uint8_t)(px + 8);
    uint8_t hw_y = (uint8_t)((int16_t)py - (int16_t)cam_y + 16);
    move_sprite(0, hw_x, hw_y);
}

void player_set_pos(int16_t x, int16_t y) {
    px = x;
    py = y;
}

int16_t player_get_x(void) { return px; }
int16_t player_get_y(void) { return py; }
```

**Step 4: Run all tests — expect ALL PASS**

```bash
GBDK_HOME=/home/mathdaman/gbdk make test
```

Expected output ends with something like:

```
OK (11 tests, 11 ran, 11 passed, 0 failed, 0 ignored)
OK (11 tests, 11 ran, 11 passed, 0 failed, 0 ignored)
OK (11 tests, 11 ran, 11 passed, 0 failed, 0 ignored)
```

If any test fails, diagnose before continuing.

**Step 5: Commit**

```bash
git add tests/test_player.c src/player.c
git commit -m "feat: update player start pos and add screen-bound clamping"
```

---

### Task 6: Build ROM and smoketest gate

**Step 1: Build the ROM**

```bash
GBDK_HOME=/home/mathdaman/gbdk make
```

Expected: `build/wasteland-racer.gb` produced with no errors. Warnings about "EVELYN" are harmless.

If build fails, check for:
- `cam_x` still referenced anywhere: `grep -r "cam_x" src/`
- `uint8_t cam_y` usage: `grep -r "cam_y" src/` — all uses should accept uint16_t

**Step 2: Smoketest gate — STOP and wait for user confirmation**

> **DO NOT commit or create a PR until the user confirms the smoketest.**

Ask the user:
> "Please run `mgba-qt build/wasteland-racer.gb` and confirm: (1) title screen appears, (2) pressing START shows the track scrolling upward, (3) player can steer left/right, (4) pressing DOWN makes the track fall behind, (5) no graphical corruption."

**Step 3: After smoketest confirmation — push and create PR**

```bash
git push -u origin HEAD
gh pr create --title "feat: upward-only scrolling track (20×100)" --body "$(cat <<'EOF'
## Summary
- Replaces 40×36 oval loop with 20×100 fixed-length upward-scrolling track
- `cam_y` is now `uint16_t`, monotonically increasing (max 656 px)
- `cam_x`, `stream_column()`, and all horizontal scroll code removed
- `camera_init()` preloads only 18 rows instead of the full map
- Player gains explicit screen-Y clamping via `cam_y` reference
- New Tiled map with straight + right-curve + straight sections

## Acceptance criteria
- [x] AC1: cam_y only ever increases
- [x] AC2: move_bkg called with X=0 every frame
- [x] AC3: stream_column and left/right edge detection removed
- [x] AC4: MAP_TILES_W=20, MAP_TILES_H=100 in config.h
- [x] AC5: Player X clamped [0,159]; screen Y clamped [0,143]
- [x] AC6: track_passable uses updated bounds
- [x] AC7: New 20×100 TMX with one curve section
- [x] AC8: Build passes and smoketest confirmed

Closes #24

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
