# Player Square Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a moveable 8×8 sprite the player can control with the D-pad after pressing START on the title screen.

**Architecture:** Player domain lives in `src/player.c` + `src/player.h`. `main.c` owns frame timing and reads joypad, passing the bitmask into `player_update(input)`. `player_render()` must be called after `wait_vbl_done()`.

**Tech Stack:** GBDK-2020, SDCC, Unity test framework (gcc), existing `tests/mocks/` infrastructure.

---

### Task 1: Add sprite mocks to `tests/mocks/gb/gb.h`

**Files:**
- Modify: `tests/mocks/gb/gb.h`

The current mock is missing sprite functions. `player.c` will call these, so they must exist for host-side test compilation.

**Step 1: Add sprite stubs to the mock**

Append before `#endif /* MOCK_GB_H */`:

```c
/* Sprite mode / display control */
#define SPRITES_8x8  ((void)0)
#define SHOW_SPRITES ((void)0)

/* Sprite functions */
static inline void set_sprite_tile_data(uint8_t first_tile, uint8_t nb_tiles,
                                         const uint8_t *data) {
    (void)first_tile; (void)nb_tiles; (void)data;
}
static inline void set_sprite_tile(uint8_t nb, uint8_t tile) {
    (void)nb; (void)tile;
}
static inline void move_sprite(uint8_t nb, uint8_t x, uint8_t y) {
    (void)nb; (void)x; (void)y;
}
```

**Step 2: Verify existing tests still compile**

```bash
make test
```
Expected: no test files yet → prints nothing, exits 0.

**Step 3: Commit**

```bash
git add tests/mocks/gb/gb.h
git commit -m "test: add sprite mocks to gb.h"
```

---

### Task 2: Update Makefile to compile `src/*.c` (minus `main.c`) in test builds

**Files:**
- Modify: `Makefile`

Currently the test target only compiles `unity.c` + the test file. `player.c` (and any future domain module) must also be compiled. `main.c` is excluded because it defines `main()`, which conflicts with the test runner.

**Step 1: Edit the Makefile**

Replace:
```makefile
TEST_FLAGS := -Itests/mocks -Itests/unity/src -Wall -Wextra
```
With:
```makefile
TEST_FLAGS   := -Itests/mocks -Itests/unity/src -Isrc -Wall -Wextra
TEST_LIB_SRC := $(filter-out src/main.c,$(wildcard src/*.c))
```

Replace the `gcc` line inside the `test` target:
```makefile
		gcc $(TEST_FLAGS) $(UNITY_SRC) $$f -o build/$$name || exit 1; \
```
With:
```makefile
		gcc $(TEST_FLAGS) $(UNITY_SRC) $(TEST_LIB_SRC) $$f -o build/$$name || exit 1; \
```

**Step 2: Verify make test still works**

```bash
make test
```
Expected: exits 0 (no test files yet, `TEST_LIB_SRC` is empty).

**Step 3: Commit**

```bash
git add Makefile
git commit -m "build: include src lib files in test compilation"
```

---

### Task 3: Write failing tests in `tests/test_player.c`

**Files:**
- Create: `tests/test_player.c`

Write all tests first — they will fail to compile because `player.h` does not exist yet. That is the expected TDD red state.

**Step 1: Create `tests/test_player.c`**

```c
#include "unity.h"
#include "player.h"

void setUp(void)    { player_init(); }
void tearDown(void) {}

/* clamp_u8 ---------------------------------------------------------- */

void test_clamp_u8_returns_lo_when_below(void) {
    TEST_ASSERT_EQUAL_UINT8(8, clamp_u8(5, 8, 152));
}

void test_clamp_u8_returns_hi_when_above(void) {
    TEST_ASSERT_EQUAL_UINT8(152, clamp_u8(200, 8, 152));
}

void test_clamp_u8_returns_value_when_within(void) {
    TEST_ASSERT_EQUAL_UINT8(80, clamp_u8(80, 8, 152));
}

/* player_init ------------------------------------------------------- */

void test_player_init_sets_center_position(void) {
    TEST_ASSERT_EQUAL_UINT8(80, player_get_x());
    TEST_ASSERT_EQUAL_UINT8(72, player_get_y());
}

/* player_update movement -------------------------------------------- */

void test_player_update_moves_left(void) {
    player_update(J_LEFT);
    TEST_ASSERT_EQUAL_UINT8(79, player_get_x());
}

void test_player_update_moves_right(void) {
    player_update(J_RIGHT);
    TEST_ASSERT_EQUAL_UINT8(81, player_get_x());
}

void test_player_update_moves_up(void) {
    player_update(J_UP);
    TEST_ASSERT_EQUAL_UINT8(71, player_get_y());
}

void test_player_update_moves_down(void) {
    player_update(J_DOWN);
    TEST_ASSERT_EQUAL_UINT8(73, player_get_y());
}

/* player_update clamping -------------------------------------------- */

void test_player_update_clamps_at_left_boundary(void) {
    player_set_pos(8, 72);
    player_update(J_LEFT);
    TEST_ASSERT_EQUAL_UINT8(8, player_get_x());
}

void test_player_update_clamps_at_right_boundary(void) {
    player_set_pos(152, 72);
    player_update(J_RIGHT);
    TEST_ASSERT_EQUAL_UINT8(152, player_get_x());
}

void test_player_update_clamps_at_top_boundary(void) {
    player_set_pos(80, 16);
    player_update(J_UP);
    TEST_ASSERT_EQUAL_UINT8(16, player_get_y());
}

void test_player_update_clamps_at_bottom_boundary(void) {
    player_set_pos(80, 136);
    player_update(J_DOWN);
    TEST_ASSERT_EQUAL_UINT8(136, player_get_y());
}

/* runner ------------------------------------------------------------ */

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_clamp_u8_returns_lo_when_below);
    RUN_TEST(test_clamp_u8_returns_hi_when_above);
    RUN_TEST(test_clamp_u8_returns_value_when_within);
    RUN_TEST(test_player_init_sets_center_position);
    RUN_TEST(test_player_update_moves_left);
    RUN_TEST(test_player_update_moves_right);
    RUN_TEST(test_player_update_moves_up);
    RUN_TEST(test_player_update_moves_down);
    RUN_TEST(test_player_update_clamps_at_left_boundary);
    RUN_TEST(test_player_update_clamps_at_right_boundary);
    RUN_TEST(test_player_update_clamps_at_top_boundary);
    RUN_TEST(test_player_update_clamps_at_bottom_boundary);
    return UNITY_END();
}
```

**Step 2: Run and confirm compile failure (TDD red)**

```bash
make test
```
Expected: `fatal error: player.h: No such file or directory`

---

### Task 4: Create `src/player.h`

**Files:**
- Create: `src/player.h`

**Step 1: Create the header**

```c
#ifndef PLAYER_H
#define PLAYER_H

#include <gb/gb.h>
#include <stdint.h>

/* Player domain API */
void    player_init(void);
void    player_update(uint8_t input);
void    player_render(void);
void    player_set_pos(uint8_t x, uint8_t y);
uint8_t player_get_x(void);
uint8_t player_get_y(void);

/* Clamping helper — static inline for zero call overhead on Z80 */
static inline uint8_t clamp_u8(uint8_t v, uint8_t lo, uint8_t hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

#endif /* PLAYER_H */
```

**Step 2: Run tests — clamp tests will pass, rest fail (no .c yet)**

```bash
make test
```
Expected: compiles but fails with `undefined reference to player_init` (or similar linker error).

---

### Task 5: Create `src/player.c`

**Files:**
- Create: `src/player.c`

**Step 1: Create the implementation**

```c
#include <gb/gb.h>
#include "player.h"

/* Solid 8x8 tile: all pixels set (GBDK 2bpp planar format, 2 bytes/row) */
static const uint8_t player_tile_data[] = {
    0xFF, 0xFF,   /* row 0 */
    0xFF, 0xFF,   /* row 1 */
    0xFF, 0xFF,   /* row 2 */
    0xFF, 0xFF,   /* row 3 */
    0xFF, 0xFF,   /* row 4 */
    0xFF, 0xFF,   /* row 5 */
    0xFF, 0xFF,   /* row 6 */
    0xFF, 0xFF    /* row 7 */
};

/* Screen bounds — GB sprite hardware: x+8 offset, y+16 offset */
#define PX_MIN  8u
#define PX_MAX  152u
#define PY_MIN  16u
#define PY_MAX  136u

#define PLAYER_START_X  80u
#define PLAYER_START_Y  72u

static uint8_t px;
static uint8_t py;

void player_init(void) {
    SPRITES_8x8;
    set_sprite_tile_data(0, 1, player_tile_data);
    set_sprite_tile(0, 0);
    px = PLAYER_START_X;
    py = PLAYER_START_Y;
    SHOW_SPRITES;
}

void player_update(uint8_t input) {
    if (input & J_LEFT)  px = clamp_u8(px - 1u, PX_MIN, PX_MAX);
    if (input & J_RIGHT) px = clamp_u8(px + 1u, PX_MIN, PX_MAX);
    if (input & J_UP)    py = clamp_u8(py - 1u, PY_MIN, PY_MAX);
    if (input & J_DOWN)  py = clamp_u8(py + 1u, PY_MIN, PY_MAX);
}

void player_render(void) {
    move_sprite(0, px, py);
}

void player_set_pos(uint8_t x, uint8_t y) {
    px = x;
    py = y;
}

uint8_t player_get_x(void) { return px; }
uint8_t player_get_y(void) { return py; }
```

**Step 2: Run tests — all 12 must pass**

```bash
make test
```
Expected output:
```
tests/test_player.c:12 tests/test_player.c:... OK
...
12 Tests 0 Failures 0 Ignored
OK
```

**Step 3: Commit**

```bash
git add src/player.h src/player.c tests/test_player.c
git commit -m "feat: add player domain module with movement and clamping"
```

---

### Task 6: Integrate player into `main.c`

**Files:**
- Modify: `src/main.c`

**Step 1: Add the include**

After the existing includes at the top of `main.c`, add:
```c
#include "player.h"
```

**Step 2: Initialize player on entering STATE_PLAYING**

Replace the `STATE_TITLE` case:
```c
case STATE_TITLE:
    if (joypad() & J_START) {
        cls();
        player_init();
        state = STATE_PLAYING;
    }
    break;
```

**Step 3: Update and render player each frame in STATE_PLAYING**

Replace the `STATE_PLAYING` case:
```c
case STATE_PLAYING:
    player_update(joypad());
    player_render();
    break;
```

Note: `wait_vbl_done()` is already called at the top of the `while(1)` loop, so `player_render()` executes within the VBlank window — correct.

**Step 4: Build the ROM**

```bash
GBDK_HOME=/home/mathdaman/gbdk make
```
Expected: `build/wasteland-racer.gb` produced with no errors.

**Step 5: Commit**

```bash
git add src/main.c
git commit -m "feat: wire player into main game loop"
```

---

### Task 7: Smoke test in emulator

```bash
mgba-qt build/wasteland-racer.gb
```

Verify:
1. Title screen shows "WASTELAND RACER" and "Press START"
2. Pressing START clears the screen and a white square appears at center
3. D-pad moves the square in all four directions
4. Square stops at all four screen edges and does not disappear
