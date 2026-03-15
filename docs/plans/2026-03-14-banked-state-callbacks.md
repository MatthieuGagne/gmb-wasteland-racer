# BANKED State Callbacks Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Mark all state callback functions as `BANKED` so state code can live in any ROM bank, permanently eliminating bank 1 pressure and allowing all assets to use `#pragma bank 255`.

**Architecture:** Add `BANKED` to the three `State` struct fn pointer fields in `state_manager.h`. Update each call site in `state_manager.c` to copy the pointer to a local `BANKED` variable before calling (copy-to-local workaround required by SDCC even in 4.4.1). Add `BANKED` to the 12 state callback functions across the 4 state files. Revert portrait generation to `--bank 255` in Makefile.

**Tech Stack:** GBDK-2020, SDCC 4.4.1, SM83/Game Boy, MBC5

---

## Context

`state_manager` dispatches state callbacks via plain (non-BANKED) function pointers. This forced all state code into bank 1 (which is ~100% full). SDCC 4.4.1 fixes the BANKED fn-pointer-in-struct bug, but the copy-to-local pattern is still required for correct bank switching. After this change, bankpack can freely distribute state code across banks 2+.

**CRITICAL pattern — copy-to-local before every call:**
```c
// ❌ Broken even in SDCC 4.4.1 — calls fn pointer directly from struct
s->enter();

// ✅ Correct — copy to local BANKED variable first
void (*fn)(void) BANKED = s->enter;
fn();
```

**Do NOT touch:**
- `music.c` — no `#pragma bank`, stays in bank 0, do not add BANKED
- `hub_data.c` — no `#pragma bank`, stays in bank 0, do not add BANKED
- Any non-state helper functions inside state files (only touch `enter`, `update`, `exit` callbacks)

---

## Task 1: Update `State` struct and `state_manager.c` call sites

**Files:**
- Modify: `src/state_manager.h`
- Modify: `src/state_manager.c`

**Step 1: Update the `State` struct in `state_manager.h`**

Change the three fn pointer fields to `BANKED`:

```c
typedef struct {
    void (*enter)(void) BANKED;
    void (*update)(void) BANKED;
    void (*exit)(void) BANKED;
} State;
```

**Step 2: Update all 5 call sites in `state_manager.c`**

Apply copy-to-local pattern at every call site. Full updated file:

```c
#pragma bank 255
#include <gb/gb.h>
#include "state_manager.h"

#define STACK_MAX 2

static const State *stack[STACK_MAX];
static uint8_t depth = 0;

void state_manager_init(void) BANKED {
    depth = 0;
}

void state_manager_update(void) BANKED {
    if (depth == 0) return;
    void (*fn)(void) BANKED = stack[depth - 1]->update;
    fn();
}

void state_push(const State *s) BANKED {
    if (depth >= STACK_MAX) return;
    stack[depth++] = s;
    void (*fn)(void) BANKED = s->enter;
    fn();
}

void state_pop(void) BANKED {
    if (depth == 0) return;
    void (*fn)(void) BANKED = stack[depth - 1]->exit;
    fn();
    depth--;
    if (depth > 0) {
        void (*fn2)(void) BANKED = stack[depth - 1]->enter;
        fn2();
    }
}

void state_replace(const State *s) BANKED {
    if (depth == 0) {
        stack[depth++] = s;
        void (*fn)(void) BANKED = s->enter;
        fn();
        return;
    }
    void (*fn)(void) BANKED = stack[depth - 1]->exit;
    fn();
    stack[depth - 1] = s;
    void (*fn2)(void) BANKED = s->enter;
    fn2();
}
```

**Step 3: Build to check for compile errors**

```sh
GBDK_HOME=/home/mathdaman/gbdk make 2>&1 | grep -E "error|warning" | grep -v "EVELYN\|NULL.*redefin"
```

Expected: no errors (warnings about BANKED on static fns are OK at this stage).

**Step 4: Commit**

```sh
git add src/state_manager.h src/state_manager.c
git commit -m "refactor: add BANKED to State struct fields, copy-to-local at all call sites"
```

---

## Task 2: Add `BANKED` to all state callback functions

**Files:**
- Modify: `src/state_title.c`
- Modify: `src/state_hub.c`
- Modify: `src/state_overmap.c`
- Modify: `src/state_playing.c`

For each file, add `BANKED` to the three functions that are assigned to the `State` struct. Only the functions directly referenced in the `const State` initializer get `BANKED` — do NOT add it to other helper functions.

**Step 1: Update `state_title.c`**

```c
// Line 10 — add BANKED
static void enter(void) BANKED {
// Line 18 — add BANKED
static void update(void) BANKED {
// Line 24 — add BANKED
static void st_exit(void) BANKED {
```

**Step 2: Update `state_hub.c`**

```c
// Line 332 — add BANKED
static void enter(void) BANKED {
// Line 357 — add BANKED
static void update(void) BANKED {
// Line 362 — add BANKED
static void hub_exit(void) BANKED {}
```

**Step 3: Update `state_overmap.c`**

```c
// Line 87 — add BANKED
static void enter(void) BANKED {
// Line 108 — add BANKED
static void update(void) BANKED {
// Line 147 — add BANKED
static void om_exit(void) BANKED {
```

**Step 4: Update `state_playing.c`**

```c
// Line 12 — add BANKED
static void enter(void) BANKED {
// Line 22 — add BANKED
static void update(void) BANKED {
// Line 41 — add BANKED
static void sp_exit(void) BANKED {
```

**Step 5: Build and verify state code can now live in any bank**

```sh
GBDK_HOME=/home/mathdaman/gbdk make clean && GBDK_HOME=/home/mathdaman/gbdk make 2>&1 | tail -5
```

Expected: clean build.

```sh
grep "_CODE_" build/nuke-raider.map
```

Expected: bank 1 now has breathing room (less than 16,370 bytes), state code may appear in bank 2+.

**Step 6: Commit**

```sh
git add src/state_title.c src/state_hub.c src/state_overmap.c src/state_playing.c
git commit -m "refactor: mark state callbacks BANKED so state code can live in any bank"
```

---

## Task 3: Revert portraits to `--bank 255` and verify

**Files:**
- Modify: `Makefile`

**Step 1: Change portrait generation back to `--bank 255`**

In `Makefile`, update all three portrait rules:

```makefile
src/npc_mechanic_portrait.c: assets/sprites/npc_mechanic.png tools/png_to_tiles.py
	python3 tools/png_to_tiles.py --bank 255 assets/sprites/npc_mechanic.png src/npc_mechanic_portrait.c npc_mechanic_portrait

src/npc_trader_portrait.c: assets/sprites/npc_trader.png tools/png_to_tiles.py
	python3 tools/png_to_tiles.py --bank 255 assets/sprites/npc_trader.png src/npc_trader_portrait.c npc_trader_portrait

src/npc_drifter_portrait.c: assets/sprites/npc_drifter.png tools/png_to_tiles.py
	python3 tools/png_to_tiles.py --bank 255 assets/sprites/npc_drifter.png src/npc_drifter_portrait.c npc_drifter_portrait
```

**Step 2: Delete stale portrait `.c` files and rebuild clean**

Portrait `.c` files are generated — `make` only regenerates them if the PNG is newer. Delete them to force regeneration:

```sh
rm src/npc_mechanic_portrait.c src/npc_trader_portrait.c src/npc_drifter_portrait.c
GBDK_HOME=/home/mathdaman/gbdk make clean && GBDK_HOME=/home/mathdaman/gbdk make 2>&1 | tail -5
```

Expected: portrait files regenerated with `#pragma bank 255`, clean build.

**Step 3: Verify no state code in wrong bank AND portraits are autobanked**

```sh
head -2 src/npc_mechanic_portrait.c
```
Expected: `#pragma bank 255`

```sh
grep "_CODE_" build/nuke-raider.map
```
Expected: bank 1 no longer at 99.9% — state code and data distributed across banks.

```sh
grep "024[0-9A-Fa-f]\{3\}" build/nuke-raider.map | grep state_
```
State code in bank 2+ is now **fine** — BANKED callbacks handle the bank switch correctly.

**Step 4: Commit**

```sh
git add Makefile src/npc_mechanic_portrait.c src/npc_trader_portrait.c src/npc_drifter_portrait.c
git commit -m "refactor: portraits back to --bank 255 now that state callbacks are BANKED"
```

---

## Task 4: Update CLAUDE.md and rom-banking skill

**Files:**
- Modify: `CLAUDE.md`
- Modify: `.claude/skills/rom-banking/SKILL.md`

**Step 1: Update CLAUDE.md — replace the CRITICAL BANKED warning**

Find the existing paragraph starting with `**CRITICAL — BANKED function pointers in structs are BROKEN on SDCC/SM83:**` and replace it with:

```
**BANKED function pointers in structs — copy-to-local pattern required:**
SDCC 4.4.1 supports `void (*fn)(void) BANKED` in struct fields correctly. However, calling directly from the struct (`s->fn()`) still generates incorrect code. Always copy to a local `BANKED` variable first:
```c
void (*fn)(void) BANKED = s->enter;
fn();
```
Named cross-bank calls via `BANKED` functions work correctly without this workaround. Only struct field fn pointers require it. State callbacks (`enter`, `update`, `exit` in `State` struct) all use this pattern via `state_manager.c`.
```

**Step 2: Update rom-banking skill**

In `.claude/skills/rom-banking/SKILL.md`, update the "Critical Constraint" section:

Replace:
```
**All state code (`state_*.c`, `state_manager.c`) must stay in bank 1.**
```

With:
```
**State callbacks are BANKED — state code may live in any bank.** `state_manager.c` uses copy-to-local pattern before every fn pointer call, which triggers correct bank switching. Bank 1 pressure is no longer a concern for state code.
```

Also update the Bank Budget table to reflect the new reality.

**Step 3: Commit**

```sh
git add CLAUDE.md .claude/skills/rom-banking/SKILL.md
git commit -m "docs: update BANKED fn pointer guidance, state code no longer bank-1-bound"
```

---

## Task 5: Smoketest and push PR

**Step 1: Run unit tests**

```sh
make test 2>&1 | tail -5
```
Expected: `27 Tests 0 Failures 0 Ignored`

**Step 2: Fetch and merge latest master**

```sh
git fetch origin && git merge origin/master
```

**Step 3: Rebuild**

```sh
GBDK_HOME=/home/mathdaman/gbdk make clean && GBDK_HOME=/home/mathdaman/gbdk make 2>&1 | tail -5
```

**Step 4: Launch emulator smoketest**

```sh
java -jar /home/mathdaman/.local/share/emulicious/Emulicious.jar build/nuke-raider.gb
```

Verify: title screen → hub dialog (portraits visible) → overmap navigation → race launches → game over flow.

**Step 5: Push and create PR**

```sh
git push -u origin <branch-name>
gh pr create --title "refactor: BANKED state callbacks, all assets autobanked" --body "..."
```

Include `Closes #103` in the PR body.
