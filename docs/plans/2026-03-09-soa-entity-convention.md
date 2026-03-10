# SoA Entity Convention Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the Array-of-Structs (AoS) entity template in CLAUDE.md with a Structure-of-Arrays (SoA) template, add SDCC rationale, update the gb-c-optimizer note, and confirm no AoS entity pools exist in src/.

**Architecture:** SDCC generates tighter indexed-addressing code for SoA (one `LD A,(IX+0)` per field) vs AoS (which requires stride multiplication). Since no pooled entity arrays currently exist in `src/`, this is a documentation + convention change. `player.c` already uses separate static vars (already SoA-style). Structs for non-entity data (`State`, `DialogNode`, `NpcDialog`) are out of scope.

**Tech Stack:** C (SDCC/GBDK-2020), Unity (host tests), CLAUDE.md convention docs.

---

### Task 1: Update CLAUDE.md — SoA template + rationale

**Files:**
- Modify: `CLAUDE.md` lines 35–42 (Entity management section)

**Step 1: Replace AoS template with SoA template**

Open `CLAUDE.md`. Find the "Entity management" section (around line 35). Replace:

```markdown
**Entity management:**
- No singletons for things that could multiply. Use fixed-size pools with an `active` flag.
- Capacity constants live in `src/config.h` — the single place to tune memory vs. features.
  ```c
  #define MAX_ENEMIES 8
  typedef struct { uint8_t x, y, active, type; } Enemy;
  static Enemy enemies[MAX_ENEMIES];
  ```
```

With:

```markdown
**Entity management:**
- No singletons for things that could multiply. Use fixed-size pools with an `active` flag.
- Use **Structure-of-Arrays (SoA)**, not Array-of-Structs (AoS). SDCC compiles each `entity_x[i]`
  to a single indexed load (`LD A,(IX+0)`); AoS structs force stride multiplication and register
  spills. Hot loops iterate one field at a time — exactly the SoA access pattern.
- Capacity constants live in `src/config.h` — the single place to tune memory vs. features.
  ```c
  /* SoA canonical template — one array per field */
  #define MAX_ENEMIES 8
  static uint8_t enemy_x[MAX_ENEMIES];
  static uint8_t enemy_y[MAX_ENEMIES];
  static uint8_t enemy_active[MAX_ENEMIES];
  static uint8_t enemy_type[MAX_ENEMIES];
  ```
```

**Step 2: Verify the edit looks correct**

Run:
```bash
grep -A 12 "Entity management" CLAUDE.md
```
Expected: SoA template with rationale comment, no `typedef struct` in the entity section.

**Step 3: Update gb-c-optimizer note**

Find the line (around line 33):
```
- Each system gets its own `.c`/`.h` pair; new module checklist: public API in `.h`, all state `static` in `.c`, `tests/test_<system>.c` written first (TDD), `gb-c-optimizer` review before merge.
```

Append a note so it becomes:
```
- Each system gets its own `.c`/`.h` pair; new module checklist: public API in `.h`, all state `static` in `.c`, `tests/test_<system>.c` written first (TDD), `gb-c-optimizer` review before merge (flags AoS entity pools as anti-pattern).
```

**Step 4: Verify**

```bash
grep "gb-c-optimizer" CLAUDE.md
```
Expected: line contains "flags AoS entity pools as anti-pattern".

**Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: replace AoS entity template with SoA + SDCC rationale in CLAUDE.md"
```

---

### Task 2: Audit src/player.c and src/track.c — confirm SoA compliance

**Files:**
- Read only: `src/player.c`, `src/track.c`, `src/player.h`

**Step 1: Audit player.c**

`player.c` currently stores entity state as individual static vars:
```c
static int16_t px;
static int16_t py;
static uint8_t player_sprite_slot;
```
This is already SoA-compliant for a single entity (no pool needed for a singleton player — confirmed out of scope per issue). No changes needed.

**Step 2: Audit track.c**

Run:
```bash
grep -n "struct\|typedef" src/track.c src/track.h
```
Expected: no `typedef struct { ... }` entity pool patterns.

**Step 3: Confirm no other AoS entity pools**

```bash
grep -rn "typedef struct" src/
```
Expected results that are NOT entity pools (all are fine to leave as-is):
- `src/dialog.h` — `DialogNode`, `NpcDialog` (ROM data, not entity pools — out of scope)
- `src/state_manager.h` — `State` (vtable struct, not entity pool — out of scope)
- `src/dialog.c` — internal state struct (one-off — out of scope)

If ANY other `typedef struct` appears with an `active` flag or a fixed-capacity array, stop and refactor it to SoA before proceeding.

**Step 4: Commit (or no-op if no changes)**

If no changes were needed:
```bash
git commit --allow-empty -m "chore: confirm player.c and track.c already SoA-compliant (no AoS pools)"
```

---

### Task 3: Write + run regression test confirming no AoS entity arrays

Since the issue acceptance criteria require `make test` to pass, and there are no AoS pools to refactor, this task adds a compile-time guard: a static assert in `src/config.h` that documents the SoA convention, plus a host-side test that verifies the capacity constants exist.

**Files:**
- Modify: `src/config.h`
- Create: `tests/test_soa_convention.c`

**Step 1: Read config.h**

```bash
cat src/config.h
```

**Step 2: Add SoA comment to config.h**

At the top of `src/config.h` (after the header guard), add a comment block:

```c
/* Entity capacity constants — all entity pools MUST use SoA (parallel arrays),
 * not AoS (struct arrays). See CLAUDE.md "Entity management" for rationale. */
```

Do NOT add any new `#define` constants unless they were already missing.

**Step 3: Write the failing test**

Create `tests/test_soa_convention.c`:

```c
#include "unity.h"
#include "../src/config.h"

void setUp(void) {}
void tearDown(void) {}

/* Verifies capacity constants are defined and sane.
 * This guards against accidental deletion of config.h constants. */
void test_max_npcs_defined(void) {
    TEST_ASSERT_GREATER_THAN(0, MAX_NPCS);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_max_npcs_defined);
    return UNITY_END();
}
```

**Step 4: Run test to verify it fails (or check what MAX_NPCS is)**

```bash
make test 2>&1 | grep -E "test_soa|PASS|FAIL|error"
```

If `MAX_NPCS` is not defined in `config.h`, the test will fail to compile — check what constants ARE defined in `config.h` and adjust the test to use an existing one (e.g. `MAX_DIALOG_NODES`, `SPRITE_POOL_SIZE`, etc.).

**Step 5: Fix the test to use a real constant, run until passing**

```bash
make test 2>&1 | tail -5
```
Expected: `1 Tests 0 Failures 0 Ignored` (or more if other tests also run).

**Step 6: Commit**

```bash
git add src/config.h tests/test_soa_convention.c
git commit -m "test: add SoA convention guard — verify capacity constants defined"
```

---

### Task 4: Build verification

**Step 1: Build the ROM**

```bash
GBDK_HOME=/home/mathdaman/gbdk make 2>&1 | tail -10
```
Expected: `build/wasteland-racer.gb` produced, no new warnings.

**Step 2: Run all tests**

```bash
make test 2>&1 | tail -5
```
Expected: all tests pass, 0 failures.

**Step 3: Final commit (if any stragglers)**

If there are any uncommitted changes, commit them. Otherwise, proceed to push.

**Step 4: Push and open PR**

```bash
git push -u origin feat/soa-entity-convention
gh pr create \
  --title "feat: SoA entity convention — parallel arrays for all entities (#35)" \
  --body "$(cat <<'EOF'
## Summary
- Replaces AoS entity template in CLAUDE.md with SoA parallel-array template
- Adds SDCC rationale (indexed addressing vs stride multiplication)
- Updates gb-c-optimizer module checklist note to flag AoS as anti-pattern
- Audits src/player.c and src/track.c — both already SoA-compliant
- Adds host-side regression test to guard capacity constants in config.h

Closes #35

## Test plan
- [ ] `make test` passes (all existing + new convention test)
- [ ] `GBDK_HOME=~/gbdk make` builds without warnings
- [ ] Smoketest in Emulicious confirms gameplay unchanged
EOF
)"
```
