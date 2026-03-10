# Input Module Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `src/input.h` — a header-only module with `prev_input`/`input` globals, `input_update()`, and `KEY_PRESSED`/`KEY_TICKED`/`KEY_RELEASED`/`KEY_DEBOUNCE` macros — and migrate all input consumers to Option B (no `uint8_t input` parameter anywhere in the state machine).

**Architecture:** `input.h` is header-only: `extern` globals + `static inline input_update()` + four macros. The two globals are **defined** in `main.c` (avoids a separate linker unit). `state_manager_update()` drops its `uint8_t input` parameter; `State.update` becomes `void (*update)(void)`. All state handlers and `player_update` read the `input` global directly via the macros.

**Tech Stack:** GBDK-2020 / SDCC, Unity (host-side tests via gcc), `make test` / `GBDK_HOME=~/gbdk make`

**Closes:** https://github.com/MatthieuGagne/gmb-wasteland-racer/issues/34

---

## Task 1: Write failing tests for `input.h`

**Files:**
- Create: `tests/test_input.c`

**Step 1: Create the test file**

```c
#include "unity.h"
#include <gb/gb.h>
#include "../src/input.h"

/* Define the globals here — main.c owns them in the ROM build,
 * but each test binary is standalone. */
uint8_t input     = 0;
uint8_t prev_input = 0;

void setUp(void)    { input = 0; prev_input = 0; }
void tearDown(void) {}

/* KEY_PRESSED --------------------------------------------------------- */

void test_key_pressed_true_when_button_held(void) {
    input = J_LEFT;
    TEST_ASSERT_TRUE(KEY_PRESSED(J_LEFT));
}

void test_key_pressed_false_when_button_not_held(void) {
    input = 0;
    TEST_ASSERT_FALSE(KEY_PRESSED(J_LEFT));
}

/* KEY_TICKED ---------------------------------------------------------- */

void test_key_ticked_true_on_first_press(void) {
    prev_input = 0;
    input      = J_START;
    TEST_ASSERT_TRUE(KEY_TICKED(J_START));
}

void test_key_ticked_false_while_held(void) {
    prev_input = J_START;
    input      = J_START;
    TEST_ASSERT_FALSE(KEY_TICKED(J_START));
}

void test_key_ticked_false_when_not_pressed(void) {
    prev_input = 0;
    input      = 0;
    TEST_ASSERT_FALSE(KEY_TICKED(J_START));
}

/* KEY_RELEASED -------------------------------------------------------- */

void test_key_released_true_on_first_release(void) {
    prev_input = J_A;
    input      = 0;
    TEST_ASSERT_TRUE(KEY_RELEASED(J_A));
}

void test_key_released_false_when_still_held(void) {
    prev_input = J_A;
    input      = J_A;
    TEST_ASSERT_FALSE(KEY_RELEASED(J_A));
}

void test_key_released_false_when_never_pressed(void) {
    prev_input = 0;
    input      = 0;
    TEST_ASSERT_FALSE(KEY_RELEASED(J_A));
}

/* KEY_DEBOUNCE -------------------------------------------------------- */

void test_key_debounce_true_when_held_both_frames(void) {
    prev_input = J_B;
    input      = J_B;
    TEST_ASSERT_TRUE(KEY_DEBOUNCE(J_B));
}

void test_key_debounce_false_on_first_press(void) {
    prev_input = 0;
    input      = J_B;
    TEST_ASSERT_FALSE(KEY_DEBOUNCE(J_B));
}

void test_key_debounce_false_after_release(void) {
    prev_input = J_B;
    input      = 0;
    TEST_ASSERT_FALSE(KEY_DEBOUNCE(J_B));
}

/* input_update -------------------------------------------------------- */

/* The mock joypad() in tests/mocks/gb/gb.h always returns 0.
 * So after input_update(): prev_input = old input, input = 0. */
void test_input_update_saves_input_to_prev(void) {
    input = J_LEFT;
    input_update();
    TEST_ASSERT_EQUAL_UINT8(J_LEFT, prev_input);
}

void test_input_update_reads_joypad_into_input(void) {
    input = J_LEFT;
    input_update();                 /* mock returns 0 */
    TEST_ASSERT_EQUAL_UINT8(0, input);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_key_pressed_true_when_button_held);
    RUN_TEST(test_key_pressed_false_when_button_not_held);
    RUN_TEST(test_key_ticked_true_on_first_press);
    RUN_TEST(test_key_ticked_false_while_held);
    RUN_TEST(test_key_ticked_false_when_not_pressed);
    RUN_TEST(test_key_released_true_on_first_release);
    RUN_TEST(test_key_released_false_when_still_held);
    RUN_TEST(test_key_released_false_when_never_pressed);
    RUN_TEST(test_key_debounce_true_when_held_both_frames);
    RUN_TEST(test_key_debounce_false_on_first_press);
    RUN_TEST(test_key_debounce_false_after_release);
    RUN_TEST(test_input_update_saves_input_to_prev);
    RUN_TEST(test_input_update_reads_joypad_into_input);
    return UNITY_END();
}
```

**Step 2: Run test to verify it fails**

```bash
make test 2>&1 | grep -A5 "test_input"
```

Expected: compile error — `../src/input.h: No such file or directory`

**Step 3: Commit the failing test**

```bash
git add tests/test_input.c
git commit -m "test: add failing tests for input module (KEY_TICKED/PRESSED/RELEASED/DEBOUNCE)"
```

---

## Task 2: Create `src/input.h`

**Files:**
- Create: `src/input.h`

**Step 1: Create the header**

```c
#ifndef INPUT_H
#define INPUT_H

#include <gb/gb.h>
#include <stdint.h>

/* Globals are DEFINED in main.c; all other TUs get extern declarations. */
extern uint8_t input;
extern uint8_t prev_input;

/* Called once per frame in main.c before state_manager_update().
 * static inline: no linker unit; SDCC may not always inline but
 * the function is tiny (2 assignments) so code size impact is negligible. */
static inline void input_update(void) {
    prev_input = input;
    input = joypad();
}

#define KEY_PRESSED(k)   ((input)      & (k))
#define KEY_TICKED(k)    (((input) & (k)) && !((prev_input) & (k)))
#define KEY_RELEASED(k)  (!((input) & (k)) && ((prev_input) & (k)))
#define KEY_DEBOUNCE(k)  (((input) & (k)) && ((prev_input) & (k)))

#endif /* INPUT_H */
```

**Step 2: Run tests**

```bash
make test 2>&1 | grep -E "(test_input|PASS|FAIL|OK)"
```

Expected: 13 tests, 0 failures, OK

**Step 3: Commit**

```bash
git add src/input.h
git commit -m "feat: add input.h with input_update and KEY_TICKED/PRESSED/RELEASED/DEBOUNCE macros"
```

---

## Task 3: Update `state_manager` — drop `uint8_t input` parameter (Option B)

**Files:**
- Modify: `src/state_manager.h`
- Modify: `src/state_manager.c`
- Modify: `tests/test_state_manager.c`

**Step 1: Update `src/state_manager.h`**

Change the `State` struct and `state_manager_update` signature:

```c
/* Before */
typedef struct {
    void (*enter)(void);
    void (*update)(uint8_t input);
    void (*exit)(void);
} State;

void state_manager_update(uint8_t input);

/* After */
typedef struct {
    void (*enter)(void);
    void (*update)(void);
    void (*exit)(void);
} State;

void state_manager_update(void);
```

Remove the `#include <stdint.h>` only if nothing else in the header needs it (it doesn't after this change — but leave it for safety, it's harmless).

**Step 2: Update `src/state_manager.c`**

```c
/* Before */
void state_manager_update(uint8_t input) {
    if (depth == 0) return;
    stack[depth - 1]->update(input);
}

/* After */
void state_manager_update(void) {
    if (depth == 0) return;
    stack[depth - 1]->update();
}
```

**Step 3: Update `tests/test_state_manager.c`**

Change mock function signatures and all `state_manager_update(0)` calls:

```c
/* Before */
static void a_update(uint8_t input) { (void)input; calls_a_update++; }
static void b_update(uint8_t input) { (void)input; calls_b_update++; }

/* After */
static void a_update(void) { calls_a_update++; }
static void b_update(void) { calls_b_update++; }
```

Replace every `state_manager_update(0)` with `state_manager_update()` (4 occurrences).

**Step 4: Run tests**

```bash
make test 2>&1 | grep -E "(test_state_manager|PASS|FAIL|OK)"
```

Expected: 8 tests, 0 failures, OK

**Step 5: Commit**

```bash
git add src/state_manager.h src/state_manager.c tests/test_state_manager.c
git commit -m "feat: drop uint8_t input param from state_manager_update and State.update (option B)"
```

---

## Task 4: Update `state_title.c` and `state_playing.c`

**Files:**
- Modify: `src/state_title.c`
- Modify: `src/state_playing.c`

**Step 1: Update `src/state_title.c`**

```c
/* Add include at top */
#include "input.h"

/* Before */
static void update(uint8_t input) {
    if (input & J_START) {
        state_replace(&state_playing);
    }
}

/* After — KEY_TICKED fires only on the first frame, satisfying AC2 */
static void update(void) {
    if (KEY_TICKED(J_START)) {
        state_replace(&state_playing);
    }
}
```

**Step 2: Update `src/state_playing.c`**

```c
/* Before */
static void update(uint8_t input) {
#ifdef DEBUG
    ...
#endif
    player_render();
    camera_flush_vram();
    move_bkg(0u, (uint8_t)cam_y);
    player_update(input);
    camera_update(player_get_x(), player_get_y());
}

/* After */
static void update(void) {
#ifdef DEBUG
    ...
#endif
    player_render();
    camera_flush_vram();
    move_bkg(0u, (uint8_t)cam_y);
    player_update();
    camera_update(player_get_x(), player_get_y());
}
```

The `#ifdef DEBUG` block inside `update` does not use `input` — only `frame_count` and `player_get_*()`. No other changes needed in that block.

**Step 3: Run all tests**

```bash
make test 2>&1 | tail -5
```

Expected: all test suites pass (state_title and state_playing have no direct unit tests — errors will surface at build time in Task 7).

**Step 4: Commit**

```bash
git add src/state_title.c src/state_playing.c
git commit -m "feat: update state handlers to void update(void), use KEY_TICKED for START"
```

---

## Task 5: Update `player.h`, `player.c`, and `test_player.c`

**Files:**
- Modify: `src/player.h`
- Modify: `src/player.c`
- Modify: `tests/test_player.c`

**Step 1: Update `src/player.h`**

```c
/* Before */
void player_update(uint8_t input);

/* After */
void player_update(void);
```

**Step 2: Update `src/player.c`**

Add `#include "input.h"` after the existing includes. Replace the function signature and swap `input &` checks for `KEY_PRESSED` macros:

```c
/* Add after existing includes */
#include "input.h"

/* Before */
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
        if (new_py <= (int16_t)(cam_y + 143u) && corners_passable(px, new_py)) py = new_py;
    }
}

/* After */
void player_update(void) {
    int16_t new_px;
    int16_t new_py;
    if (KEY_PRESSED(J_LEFT)) {
        new_px = px - 1;
        if (new_px >= 0 && corners_passable(new_px, py)) px = new_px;
    }
    if (KEY_PRESSED(J_RIGHT)) {
        new_px = px + 1;
        if (new_px <= 159 && corners_passable(new_px, py)) px = new_px;
    }
    if (KEY_PRESSED(J_UP)) {
        new_py = py - 1;
        if (new_py >= (int16_t)cam_y && corners_passable(px, new_py)) py = new_py;
    }
    if (KEY_PRESSED(J_DOWN)) {
        new_py = py + 1;
        if (new_py <= (int16_t)(cam_y + 143u) && corners_passable(px, new_py)) py = new_py;
    }
}
```

**Step 3: Update `tests/test_player.c`**

Add `#include "../src/input.h"`, define the globals, update `setUp`, and change all `player_update(J_*)` calls to set `input` then call `player_update()`:

```c
/* Add after existing includes */
#include "../src/input.h"

/* Add after includes, before setUp */
uint8_t input     = 0;
uint8_t prev_input = 0;

/* Update setUp to reset input */
void setUp(void) {
    input = 0;
    prev_input = 0;
    mock_vram_clear();
    camera_init(88, 720);
    player_init();
}
```

For each test that calls `player_update(J_X)`, replace with two lines:

```c
/* Before */
player_update(J_LEFT);

/* After */
input = J_LEFT;
player_update();
```

Apply this pattern to all 11 `player_update(...)` call sites in the test file.

**Step 4: Run tests**

```bash
make test 2>&1 | grep -E "(test_player|test_input|PASS|FAIL|OK)"
```

Expected: `test_player` 11 tests OK, `test_input` 13 tests OK.

**Step 5: Commit**

```bash
git add src/player.h src/player.c tests/test_player.c
git commit -m "feat: player_update(void) reads input global via KEY_PRESSED macros"
```

---

## Task 6: Update `main.c` — define globals, call `input_update()`

**Files:**
- Modify: `src/main.c`

**Step 1: Update `src/main.c`**

```c
/* Before */
#include <gb/gb.h>
#include <gb/cgb.h>
#include "player.h"
#include "state_manager.h"
#include "state_title.h"

/* After — add input.h include */
#include <gb/gb.h>
#include <gb/cgb.h>
#include "input.h"
#include "player.h"
#include "state_manager.h"
#include "state_title.h"

/* Add global definitions after includes, before static palettes */
uint8_t input     = 0;
uint8_t prev_input = 0;
```

Update the main loop:

```c
/* Before */
while (1) {
    wait_vbl_done();
    state_manager_update(joypad());
}

/* After */
while (1) {
    wait_vbl_done();
    input_update();           /* saves prev frame, reads joypad() */
    state_manager_update();   /* no longer passes raw joypad byte */
}
```

**Step 2: Run all tests**

```bash
make test 2>&1 | tail -5
```

Expected: all suites pass.

**Step 3: Commit**

```bash
git add src/main.c
git commit -m "feat: wire input_update() into main loop; define input/prev_input globals"
```

---

## Task 7: ROM build verification

**Step 1: Full build**

```bash
GBDK_HOME=/home/mathdaman/gbdk make 2>&1
```

Expected: `build/wasteland-racer.gb` produced, zero warnings (the "EVELYN" optimizer warning is harmless if it appears).

**Step 2: If build fails**

Common causes:
- Forgot to update a `state_title.h` or `state_playing.h` if those exist and declare `update` with old signature — check with `grep -r "uint8_t input" src/`
- Missing `#include "input.h"` in a `.c` that uses `KEY_*` macros

**Step 3: Smoketest**

```bash
java -jar /home/mathdaman/.local/share/emulicious/Emulicious.jar build/wasteland-racer.gb &
```

Verify: title screen appears, START transitions to game, player moves with D-pad, player stays on track.

**Step 4: Commit build confirmation**

No separate commit needed — build artifacts are gitignored.

---

## Task 8: Open PR

```bash
gh pr create \
  --title "feat: input module — KEY_TICKED/PRESSED/RELEASED/DEBOUNCE (#34)" \
  --body "Closes #34

## Summary
- Adds \`src/input.h\`: header-only module with \`input_update()\`, \`KEY_PRESSED\`, \`KEY_TICKED\`, \`KEY_RELEASED\`, \`KEY_DEBOUNCE\`
- \`State.update\` and \`state_manager_update\` now take \`void\` (Option B)
- \`player_update(void)\` reads \`input\` global via \`KEY_PRESSED\` macros
- \`state_title\` uses \`KEY_TICKED(J_START)\` — fires exactly once on press

## Test plan
- [ ] \`make test\` passes (13 new input tests + all existing tests)
- [ ] \`GBDK_HOME=~/gbdk make\` builds without warnings
- [ ] Smoketest: title → START → game, D-pad movement, track collision all work
" \
  --repo MatthieuGagne/gmb-wasteland-racer
```
