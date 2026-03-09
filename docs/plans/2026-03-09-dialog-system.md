# Branching Dialog System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a data-driven branching dialog module (`dialog.c`) with per-NPC persistent state, choice traversal, and a flag bitmask API — no rendering coupling.

**Architecture:** ROM-side `DialogNode`/`NpcDialog` arrays hold text and graph edges; WRAM-side `NpcState[MAX_NPCS]` tracks each NPC's resume point and 8-bit flag field. A thin module-level active-conversation cursor (`active_npc_id` + pointer) serves whichever NPC is currently being spoken to.

**Tech Stack:** C99 (SDCC-compatible), GBDK-2020, Unity (host-side tests via `make test`), gcc for test compilation.

---

## GBDK Constraints (verified)
- No compound literals — use named `static const` arrays for all aggregate data.
- No `malloc`/`free` — all state in `static` globals.
- `uint8_t` preferred for counters and indices.
- `const char *` in ROM structs: fine in SDCC (pointers are 2 bytes on GB).
- No `<gb/gb.h>` include in `dialog.h` — this module is rendering-agnostic; only `<stdint.h>` needed.

## Memory Budget (verified vs AC6)
- `NpcState`: 2 bytes × 6 NPCs = **12 bytes WRAM** ✓
- Module cursor (`active_npc_id` + `active_dialog*`): ~3 bytes WRAM
- Sample dialog data (7 nodes × ~12 bytes + strings): ~400 bytes ROM — well under 8 KB ✓

---

## Task 1: Create `src/config.h`

**Files:**
- Create: `src/config.h`

**Step 1: Create the file**

```c
#ifndef CONFIG_H
#define CONFIG_H

#define MAX_NPCS 6

#endif /* CONFIG_H */
```

**Step 2: Verify it compiles in the test build**

```bash
cd /home/mathdaman/code/gmb-wasteland-racer
make test
```

Expected: all existing tests still pass (no regressions).

**Step 3: Commit**

```bash
git add src/config.h
git commit -m "feat: add config.h with MAX_NPCS=6"
```

---

## Task 2: Create `src/dialog.h` and `src/dialog_data.h`

**Files:**
- Create: `src/dialog.h`
- Create: `src/dialog_data.h`

**Step 1: Write `src/dialog.h`**

```c
#ifndef DIALOG_H
#define DIALOG_H

#include <stdint.h>
#include "config.h"

/* Sentinel: used in DialogNode.next[] to mark end of conversation. */
#define DIALOG_END 0xFFu

/* ROM-side node: text, optional choices, and destination indices. */
typedef struct {
    const char *text;           /* displayed line                           */
    uint8_t     num_choices;    /* 0 = narration (auto-advance via next[0]) */
    const char *choices[3];     /* choice labels; NULL for unused slots      */
    uint8_t     next[3];        /* destination node index per choice/advance */
} DialogNode;

/* ROM-side per-NPC dialog: pointer to node array + count. */
typedef struct {
    const DialogNode *nodes;
    uint8_t           num_nodes;
} NpcDialog;

/* --- Public API ---------------------------------------------------------- */

/* Zero all NPC state. Call once at game start. */
void dialog_init(void);

/* Begin a conversation with npc_id, resuming from its stored current_node.
 * npc_id must be < MAX_NPCS. dialog must remain valid for the session. */
void dialog_start(uint8_t npc_id, const NpcDialog *dialog);

/* Return the text of the current node (valid after dialog_start). */
const char *dialog_get_text(void);

/* Return the number of choices on the current node (0 = narration). */
uint8_t dialog_get_num_choices(void);

/* Return the label of choice idx (idx < dialog_get_num_choices()). */
const char *dialog_get_choice(uint8_t idx);

/* Advance the conversation.
 * For narration nodes (num_choices == 0): choice_idx is ignored.
 * For choice nodes: choice_idx selects the branch (0, 1, or 2).
 * Returns 1 if there is more dialog, 0 if the conversation has ended.
 * On end, current_node is reset to 0 for the next dialog_start. */
uint8_t dialog_advance(uint8_t choice_idx);

/* Persistent flag API (within-session only, not saved to SRAM). */
void    dialog_set_flag(uint8_t npc_id, uint8_t flag_bit);
uint8_t dialog_get_flag(uint8_t npc_id, uint8_t flag_bit);

#endif /* DIALOG_H */
```

**Step 2: Write `src/dialog_data.h`**

```c
#ifndef DIALOG_DATA_H
#define DIALOG_DATA_H

#include "dialog.h"

/* Sample NPC dialog tree — 3-level branching conversation.
 * Index into this array with an npc_id to retrieve the NpcDialog. */
extern const NpcDialog npc_dialogs[];

#endif /* DIALOG_DATA_H */
```

**Step 3: Verify headers compile cleanly (no .c yet needed)**

```bash
cd /home/mathdaman/code/gmb-wasteland-racer
echo '#include "dialog.h"' | gcc -Isrc -x c - -fsyntax-only
echo '#include "dialog_data.h"' | gcc -Isrc -x c - -fsyntax-only
```

Expected: no errors.

**Step 4: Commit**

```bash
git add src/dialog.h src/dialog_data.h
git commit -m "feat: add dialog.h and dialog_data.h type/API declarations"
```

---

## Task 3: TDD Red — Write `tests/test_dialog.c` + `src/dialog.c` skeleton

**Files:**
- Create: `tests/test_dialog.c`
- Create: `src/dialog.c` (skeleton — stubs that return 0)

**Step 1: Create `src/dialog.c` skeleton**

This exists so `make test` can link. All functions are stubs.

```c
#include "dialog.h"

void    dialog_init(void)                              { }
void    dialog_start(uint8_t npc_id,
                     const NpcDialog *dialog)          { (void)npc_id; (void)dialog; }
const char *dialog_get_text(void)                      { return ""; }
uint8_t dialog_get_num_choices(void)                   { return 0; }
const char *dialog_get_choice(uint8_t idx)             { (void)idx; return ""; }
uint8_t dialog_advance(uint8_t choice_idx)             { (void)choice_idx; return 0; }
void    dialog_set_flag(uint8_t npc_id,
                        uint8_t flag_bit)              { (void)npc_id; (void)flag_bit; }
uint8_t dialog_get_flag(uint8_t npc_id, uint8_t flag_bit) {
    (void)npc_id; (void)flag_bit; return 0;
}
```

**Step 2: Create `tests/test_dialog.c`**

```c
#include "unity.h"
#include "dialog.h"

/* --- Inline test dialog data (ROM-side, named static arrays per SDCC rules) --- */

static const char tn0_text[] = "Hello traveler!";
static const char tn1_text[] = "What do you want?";
static const char tn2_text[] = "Good trade!";
static const char tn3_text[] = "Prepare to die!";
static const char tn1_c0[]   = "Trade";
static const char tn1_c1[]   = "Fight";

/*
 * Graph:
 *   node 0 (narration) -> node 1
 *   node 1 (2 choices) -> node 2 (Trade) or node 3 (Fight)
 *   node 2 (narration) -> END
 *   node 3 (narration) -> END
 */
static const DialogNode test_nodes[] = {
    { tn0_text, 0, {NULL,   NULL,   NULL}, {1,           0xFFu, 0xFFu} },
    { tn1_text, 2, {tn1_c0, tn1_c1, NULL}, {2,           3,     0xFFu} },
    { tn2_text, 0, {NULL,   NULL,   NULL}, {DIALOG_END,  0xFFu, 0xFFu} },
    { tn3_text, 0, {NULL,   NULL,   NULL}, {DIALOG_END,  0xFFu, 0xFFu} },
};
static const NpcDialog test_dialog = { test_nodes, 4 };

/* A separate single-node dialog for flag tests */
static const char fn0_text[] = "Flag tester";
static const DialogNode flag_nodes[] = {
    { fn0_text, 0, {NULL, NULL, NULL}, {DIALOG_END, 0xFFu, 0xFFu} },
};
static const NpcDialog flag_dialog = { flag_nodes, 1 };

/* --- setUp / tearDown ---------------------------------------------------- */

void setUp(void)    { dialog_init(); }
void tearDown(void) {}

/* --- Test: linear advance (narration -> narration -> end) ---------------- */

/* After dialog_start on NPC 0, get_text returns the first node's text. */
void test_dialog_get_text_returns_first_node(void) {
    dialog_start(0, &test_dialog);
    TEST_ASSERT_EQUAL_STRING("Hello traveler!", dialog_get_text());
}

/* First node is narration: num_choices == 0. */
void test_dialog_first_node_is_narration(void) {
    dialog_start(0, &test_dialog);
    TEST_ASSERT_EQUAL_UINT8(0, dialog_get_num_choices());
}

/* Advancing past a narration node moves to the next node. */
void test_dialog_advance_narration_moves_to_next(void) {
    dialog_start(0, &test_dialog);
    dialog_advance(0); /* advance past node 0 */
    TEST_ASSERT_EQUAL_STRING("What do you want?", dialog_get_text());
}

/* --- Test: branching choice --------------------------------------------- */

/* After advancing to the choice node, num_choices == 2. */
void test_dialog_choice_node_has_two_choices(void) {
    dialog_start(0, &test_dialog);
    dialog_advance(0); /* skip narration to node 1 */
    TEST_ASSERT_EQUAL_UINT8(2, dialog_get_num_choices());
}

/* get_choice(0) returns the first choice label. */
void test_dialog_get_choice_returns_label(void) {
    dialog_start(0, &test_dialog);
    dialog_advance(0);
    TEST_ASSERT_EQUAL_STRING("Trade", dialog_get_choice(0));
    TEST_ASSERT_EQUAL_STRING("Fight", dialog_get_choice(1));
}

/* Choosing "Trade" (idx 0) leads to node 2 text. */
void test_dialog_branch_choice_0_leads_to_trade_node(void) {
    dialog_start(0, &test_dialog);
    dialog_advance(0); /* narration -> node 1 */
    dialog_advance(0); /* choose Trade -> node 2 */
    TEST_ASSERT_EQUAL_STRING("Good trade!", dialog_get_text());
}

/* Choosing "Fight" (idx 1) leads to node 3 text. */
void test_dialog_branch_choice_1_leads_to_fight_node(void) {
    dialog_start(0, &test_dialog);
    dialog_advance(0); /* narration -> node 1 */
    dialog_advance(1); /* choose Fight -> node 3 */
    TEST_ASSERT_EQUAL_STRING("Prepare to die!", dialog_get_text());
}

/* --- Test: conversation end --------------------------------------------- */

/* dialog_advance on a DIALOG_END node returns 0. */
void test_dialog_advance_returns_0_at_end(void) {
    uint8_t result;
    dialog_start(0, &test_dialog);
    dialog_advance(0); /* -> node 1 */
    dialog_advance(0); /* -> node 2 */
    result = dialog_advance(0); /* node 2's next[0] == DIALOG_END */
    TEST_ASSERT_EQUAL_UINT8(0, result);
}

/* dialog_advance returns 1 while there is more dialog. */
void test_dialog_advance_returns_1_while_ongoing(void) {
    uint8_t result;
    dialog_start(0, &test_dialog);
    result = dialog_advance(0); /* node 0 -> node 1 */
    TEST_ASSERT_EQUAL_UINT8(1, result);
}

/* After conversation ends, starting again resumes from node 0 (reset). */
void test_dialog_end_resets_current_node_to_0(void) {
    dialog_start(0, &test_dialog);
    dialog_advance(0); /* -> node 1 */
    dialog_advance(0); /* -> node 2 */
    dialog_advance(0); /* END: resets current_node to 0 */
    dialog_start(0, &test_dialog);
    TEST_ASSERT_EQUAL_STRING("Hello traveler!", dialog_get_text());
}

/* --- Test: flag round-trip ---------------------------------------------- */

/* A flag starts cleared after dialog_init. */
void test_dialog_flag_starts_clear(void) {
    TEST_ASSERT_EQUAL_UINT8(0, dialog_get_flag(0, 0));
}

/* dialog_set_flag makes dialog_get_flag return 1 for that bit. */
void test_dialog_set_flag_makes_get_flag_true(void) {
    dialog_set_flag(0, 3);
    TEST_ASSERT_EQUAL_UINT8(1, dialog_get_flag(0, 3));
}

/* Setting flag on NPC 0 does not affect NPC 1. */
void test_dialog_flag_is_per_npc(void) {
    dialog_set_flag(0, 2);
    TEST_ASSERT_EQUAL_UINT8(0, dialog_get_flag(1, 2));
}

/* Multiple bits on the same NPC can be set independently. */
void test_dialog_multiple_flags_independent(void) {
    dialog_set_flag(0, 0);
    dialog_set_flag(0, 7);
    TEST_ASSERT_EQUAL_UINT8(1, dialog_get_flag(0, 0));
    TEST_ASSERT_EQUAL_UINT8(0, dialog_get_flag(0, 1));
    TEST_ASSERT_EQUAL_UINT8(1, dialog_get_flag(0, 7));
}

/* --- runner ------------------------------------------------------------- */

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_dialog_get_text_returns_first_node);
    RUN_TEST(test_dialog_first_node_is_narration);
    RUN_TEST(test_dialog_advance_narration_moves_to_next);
    RUN_TEST(test_dialog_choice_node_has_two_choices);
    RUN_TEST(test_dialog_get_choice_returns_label);
    RUN_TEST(test_dialog_branch_choice_0_leads_to_trade_node);
    RUN_TEST(test_dialog_branch_choice_1_leads_to_fight_node);
    RUN_TEST(test_dialog_advance_returns_0_at_end);
    RUN_TEST(test_dialog_advance_returns_1_while_ongoing);
    RUN_TEST(test_dialog_end_resets_current_node_to_0);
    RUN_TEST(test_dialog_flag_starts_clear);
    RUN_TEST(test_dialog_set_flag_makes_get_flag_true);
    RUN_TEST(test_dialog_flag_is_per_npc);
    RUN_TEST(test_dialog_multiple_flags_independent);
    return UNITY_END();
}
```

**Step 3: Run tests — confirm RED (tests compile but fail)**

```bash
cd /home/mathdaman/code/gmb-wasteland-racer
make test
```

Expected: build succeeds, but test output shows FAIL for most `test_dialog_*` tests (stubs return wrong values). Other test suites (player, track, camera, gamestate) must still pass.

**Step 4: Commit the red state**

```bash
git add src/dialog.c tests/test_dialog.c
git commit -m "test: add dialog tests (red) + skeleton dialog.c"
```

---

## Task 4: TDD Green — Implement `src/dialog.c`

**Files:**
- Modify: `src/dialog.c`

**Step 1: Replace the skeleton with the full implementation**

```c
#include "dialog.h"

/* Per-NPC WRAM state — 2 bytes × MAX_NPCS = 12 bytes total. */
typedef struct {
    uint8_t current_node;
    uint8_t flags;
} NpcState;

static NpcState npc_states[MAX_NPCS];

/* Active conversation cursor. */
static uint8_t           active_npc_id;
static const NpcDialog  *active_dialog;

void dialog_init(void) {
    uint8_t i;
    for (i = 0; i < MAX_NPCS; i++) {
        npc_states[i].current_node = 0;
        npc_states[i].flags        = 0;
    }
    active_npc_id = 0;
    active_dialog = 0;
}

void dialog_start(uint8_t npc_id, const NpcDialog *dialog) {
    active_npc_id = npc_id;
    active_dialog = dialog;
    /* current_node already holds the resume point from last conversation */
}

const char *dialog_get_text(void) {
    uint8_t node_idx = npc_states[active_npc_id].current_node;
    return active_dialog->nodes[node_idx].text;
}

uint8_t dialog_get_num_choices(void) {
    uint8_t node_idx = npc_states[active_npc_id].current_node;
    return active_dialog->nodes[node_idx].num_choices;
}

const char *dialog_get_choice(uint8_t idx) {
    uint8_t node_idx = npc_states[active_npc_id].current_node;
    return active_dialog->nodes[node_idx].choices[idx];
}

uint8_t dialog_advance(uint8_t choice_idx) {
    uint8_t npc       = active_npc_id;
    uint8_t node_idx  = npc_states[npc].current_node;
    const DialogNode *node = &active_dialog->nodes[node_idx];
    uint8_t next_idx;

    if (node->num_choices == 0) {
        next_idx = node->next[0];
    } else {
        next_idx = node->next[choice_idx];
    }

    if (next_idx == DIALOG_END) {
        npc_states[npc].current_node = 0; /* reset for next conversation */
        return 0;
    }

    npc_states[npc].current_node = next_idx;
    return 1;
}

void dialog_set_flag(uint8_t npc_id, uint8_t flag_bit) {
    npc_states[npc_id].flags |= (uint8_t)(1u << flag_bit);
}

uint8_t dialog_get_flag(uint8_t npc_id, uint8_t flag_bit) {
    return (npc_states[npc_id].flags >> flag_bit) & 1u;
}
```

**Step 2: Run tests — confirm GREEN**

```bash
cd /home/mathdaman/code/gmb-wasteland-racer
make test
```

Expected: all 14 `test_dialog_*` tests PASS. All other suites still PASS.

**Step 3: Commit**

```bash
git add src/dialog.c
git commit -m "feat: implement dialog module (linear advance, branching, flags)"
```

---

## Task 5: Create `src/dialog_data.c` — Sample NPC

**Files:**
- Create: `src/dialog_data.c`

**Step 1: Write the sample NPC data**

This is a 3-level branching conversation for NPC 0 (mechanic). All strings and arrays are `static const` (SDCC places them in ROM).

```c
#include "dialog_data.h"

/* --- NPC 0: Mechanic — 3-level branching conversation ------------------- */
/*
 * Node graph:
 *   0 (narration)  -> 1
 *   1 (2 choices)  -> 2 "The races" | 3 "Supplies"
 *   2 (2 choices)  -> 4 "Thanks"    | 5 "Tell me more"
 *   3 (narration)  -> 6
 *   4 (narration)  -> END
 *   5 (narration)  -> END
 *   6 (narration)  -> END
 */
static const char m0[] = "Greetings, racer. Ready to talk?";
static const char m1[] = "What's on your mind?";
static const char m2[] = "The circuit is brutal. Stay sharp.";
static const char m3[] = "I've got parts if you've got caps.";
static const char m4[] = "Good luck out there.";
static const char m5[] = "Watch the east corner. It bites.";
static const char m6[] = "Come back with caps.";

static const char mc1_0[] = "The races";
static const char mc1_1[] = "Supplies";
static const char mc2_0[] = "Thanks";
static const char mc2_1[] = "Tell me more";

static const DialogNode mechanic_nodes[] = {
    /* 0 */ { m0, 0, {NULL,   NULL,   NULL}, {1,          0xFFu, 0xFFu} },
    /* 1 */ { m1, 2, {mc1_0,  mc1_1,  NULL}, {2,          3,     0xFFu} },
    /* 2 */ { m2, 2, {mc2_0,  mc2_1,  NULL}, {4,          5,     0xFFu} },
    /* 3 */ { m3, 0, {NULL,   NULL,   NULL}, {6,          0xFFu, 0xFFu} },
    /* 4 */ { m4, 0, {NULL,   NULL,   NULL}, {DIALOG_END, 0xFFu, 0xFFu} },
    /* 5 */ { m5, 0, {NULL,   NULL,   NULL}, {DIALOG_END, 0xFFu, 0xFFu} },
    /* 6 */ { m6, 0, {NULL,   NULL,   NULL}, {DIALOG_END, 0xFFu, 0xFFu} },
};

/* --- NPC dialog table (indexed by npc_id) ------------------------------- */
/* Slots 1–5 are placeholders pointing at mechanic until more NPCs are added */
const NpcDialog npc_dialogs[] = {
    { mechanic_nodes, 7 }, /* NPC 0: mechanic */
    { mechanic_nodes, 7 }, /* NPC 1: placeholder */
    { mechanic_nodes, 7 }, /* NPC 2: placeholder */
    { mechanic_nodes, 7 }, /* NPC 3: placeholder */
    { mechanic_nodes, 7 }, /* NPC 4: placeholder */
    { mechanic_nodes, 7 }, /* NPC 5: placeholder */
};
```

**Step 2: Run tests — confirm still GREEN**

```bash
cd /home/mathdaman/code/gmb-wasteland-racer
make test
```

Expected: all tests pass (dialog_data.c is compiled into the test lib but its symbols aren't called by test_dialog.c, so no conflict).

**Step 3: Build the ROM**

```bash
GBDK_HOME=/home/mathdaman/gbdk make
```

Expected: `build/wasteland-racer.gb` produced with no errors. The "EVELYN" warning is harmless.

**Step 4: Commit**

```bash
git add src/dialog_data.c
git commit -m "feat: add sample NPC dialog data (mechanic, 3-level branching)"
```

---

## Checklist (verify before PR)

- [ ] `make test` — all tests pass (including 14 new dialog tests)
- [ ] `GBDK_HOME=/home/mathdaman/gbdk make` — ROM builds without errors
- [ ] AC6 memory budget: WRAM ≤ 12 bytes (6 × 2), ROM ≤ 8 KB for dialog data
- [ ] `git log --oneline` shows 5 clean commits on the feature branch
- [ ] Smoketest confirmed in emulator (`mgba-qt build/wasteland-racer.gb`)
- [ ] PR created with link back to issue #9
