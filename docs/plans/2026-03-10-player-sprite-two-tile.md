# Player Car Sprite — 8×16 Two-Tile Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the solid 8×8 square with a two-tile 8×16 top-down car graphic using two stacked OAM entries.

**Architecture:** `player_init()` claims two sprite slots and loads two tiles (32 bytes); `player_render()` moves both slots in sync — top at `(hw_x, hw_y)`, bottom at `(hw_x, hw_y+8)`. The collision box stays 8×8 (top tile bounds, unchanged in `corners_passable`).

**Asset pipeline:** The sprite is defined in `assets/sprites/player_car.png` (8×16, 2-bit indexed). `tools/png_to_tiles.py` converts it to `src/player_sprite.c` which defines `player_tile_data[]`. `player.c` references it via `extern`. Both the PNG and the generated `.c` are checked into git (same pattern as `track_tiles.c`).

**Tech Stack:** GBDK-2020, SDCC, Unity (host tests), mock GBDK headers in `tests/mocks/`

---

### Task 1: Expand sprite mock to track per-slot positions ✅ DONE

Committed: `test: track per-slot sprite positions in mock`

---

### Task 2: Write failing tests for 2-slot init and 2-sprite render ✅ DONE

Committed: `test: failing tests for 2-slot OAM and aligned render`

---

### Task 3: Create sprite PNG and generate player_sprite.c

**Files:**
- Create: `assets/sprites/player_car.png`
- Create: `src/player_sprite.c` (generated, checked into git)
- Modify: `Makefile`
- Modify: `src/player.c`

**Step 1: Create `assets/sprites/player_car.png`**

Already done. The 8×16 PNG was generated programmatically — 2-bit indexed, 4 colors:
`0=transparent, 1=light body, 2=window, 3=dark outline`

Car layout:
- Rows 0–7 (tile 0, front): bumper taper → full body → windshield rows → body
- Rows 8–15 (tile 1, rear): body → rear taper → bumper taper

**Step 2: Run `png_to_tiles.py` to generate `src/player_sprite.c`**

```bash
python3 tools/png_to_tiles.py assets/sprites/player_car.png src/player_sprite.c player_tile_data
```

Already done. Produces:
```c
const uint8_t player_tile_data[] = { /* 32 bytes, 2 tiles */ };
const uint8_t player_tile_data_count = 2u;
```

**Step 3: Add Makefile rule for `src/player_sprite.c`**

After the existing `src/track_tiles.c` rule, add:

```makefile
# src/player_sprite.c is checked into git so CI works without Python.
src/player_sprite.c: assets/sprites/player_car.png tools/png_to_tiles.py
	python3 tools/png_to_tiles.py assets/sprites/player_car.png src/player_sprite.c player_tile_data

$(TARGET): src/player_sprite.c
```

**Step 4: Update `player.c` to use extern + 2 slots**

Replace the static `player_tile_data` array and update `player_init`:

Remove:
```c
/* Solid 8x8 sprite: all pixels color index 3 */
static const uint8_t player_tile_data[] = {
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF
};
```

Add after includes (following `track.c` pattern):
```c
extern const uint8_t player_tile_data[];
extern const uint8_t player_tile_data_count;
```

Add after existing `static uint8_t player_sprite_slot = 0;`:
```c
static uint8_t player_sprite_slot_bot = 0;
```

Replace the body of `player_init`:
```c
void player_init(void) {
    SPRITES_8x8;
    sprite_pool_init();
    player_sprite_slot     = get_sprite();  /* OAM slot for top half    */
    player_sprite_slot_bot = get_sprite();  /* OAM slot for bottom half */
    set_sprite_data(0, 2, player_tile_data); /* load 2 tiles (32 bytes)  */
    set_sprite_tile(player_sprite_slot,     0); /* top    half = tile 0 */
    set_sprite_tile(player_sprite_slot_bot, 1); /* bottom half = tile 1 */
    px = track_start_x;
    py = track_start_y;
    vx = 0;
    vy = 0;
    SHOW_SPRITES;
}
```

**Step 5: Run tests — slot-count test should pass; render tests still fail**

```
make test
```
Expected: `test_player_init_claims_two_sprite_slots` PASS; 2 render tests still FAIL.

**Step 6: Commit**

```bash
git add assets/sprites/player_car.png src/player_sprite.c Makefile src/player.c
git commit -m "feat: 8x16 two-tile player car sprite, PNG asset + generated C"
```

---

### Task 4: Update `player_render()` to move both OAM slots

**Files:**
- Modify: `src/player.c`

**Step 1: Update `player_render()`**

Replace the existing `player_render` function:

```c
void player_render(void) {
    /* cam_x is always 0; cam_y is uint16_t but py >= cam_y is enforced so offset fits uint8_t */
    uint8_t hw_x = (uint8_t)(px + 8);
    uint8_t hw_y = (uint8_t)((int16_t)py - (int16_t)cam_y + 16);
    move_sprite(player_sprite_slot,     hw_x, hw_y);
    move_sprite(player_sprite_slot_bot, hw_x, (uint8_t)(hw_y + 8u));
    /* Log when sprite is near or outside visible bounds */
    if (hw_x < 8u || hw_x > 167u || hw_y < 16u || hw_y > 159u) {
        DBG_INT("hw_x_oob", hw_x);
        DBG_INT("hw_y_oob", hw_y);
    }
}
```

**Step 2: Run all tests — expect all to pass**

```
make test
```
Expected: ALL tests PASS (including the 3 new ones).

**Step 3: Commit**

```bash
git add src/player.c
git commit -m "feat: player_render moves both OAM slots in sync"
```

---

### Task 5: Update OAM budget comment in config.h

**Files:**
- Modify: `src/config.h`

**Step 1: Update the MAX_SPRITES comment**

Replace:
```c
#define MAX_SPRITES  40
```

With:
```c
/* OAM budget: player=2 (top+bottom half), remaining=38 for enemies/projectiles/HUD */
#define MAX_SPRITES  40
```

**Step 2: Run tests to confirm nothing broke**

```
make test
```
Expected: all tests PASS.

**Step 3: Build the ROM**

```
GBDK_HOME=/home/mathdaman/gbdk make
```
Expected: clean build, `build/wasteland-racer.gb` produced.

**Step 4: Commit**

```bash
git add src/config.h
git commit -m "docs: document OAM budget in config.h (player=2, remaining=38)"
```

---

## Finishing Up

After all tasks pass tests and build:

1. Run smoketest in Emulicious (see CLAUDE.md for command)
2. Confirm car shape is visible and both halves move in sync
3. Use `/finishing-a-development-branch` skill to create the PR
