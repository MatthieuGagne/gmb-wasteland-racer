# Scalability Design — Wasteland Racer

**Date:** 2026-03-09
**Status:** Approved
**Scope:** CLAUDE.md + memory conventions (no source changes)

---

## Goal

Ensure every feature added to this game — no matter how small — naturally trends toward an architecture that holds up at 10× the current scope. This is enforced through conventions baked into CLAUDE.md and memory files, not through premature refactoring.

---

## Module Architecture

Each game system lives in `src/<system>.c` + `src/<system>.h`.

`main.c` stays thin:
- Frame timing (`wait_vbl_done()`)
- Input polling (`joypad()`)
- State machine dispatch

No game logic lives inline in `main.c`. If a state handler grows beyond ~10 lines, it moves to a module.

New module checklist:
1. Public API in `.h`; all state `static` in `.c`
2. Matching `tests/test_<system>.c` written first (TDD)
3. `gb-c-optimizer` agent review before merge

---

## Entity Management Pattern

No singletons for things that could multiply. Fixed-size pools with an `active` flag:

```c
#define MAX_ENEMIES 8
typedef struct { uint8_t x, y, active, type; } Enemy;
static Enemy enemies[MAX_ENEMIES];
```

Capacity constants live in `src/config.h` — the single place to tune memory vs. feature tradeoffs.

Applies to: enemies, projectiles, pickups, particles, anything that could have N > 1.

---

## Memory Budgets

Explicit limits tracked as conventions (not enforced by tooling):

| Resource | Total | Player | Budget for rest |
|----------|-------|--------|-----------------|
| OAM sprites | 40 | 1 | 39 (enemies, projectiles, HUD icons) |
| VRAM tiles (DMG bank 0) | 192 | ~1 | ~191 |
| VRAM tiles (CGB bank 1) | 192 | 0 | 192 (color variants) |
| WRAM | 8 KB | ~10 B | ~8 KB |

Rules:
- Large static arrays declared globally or `static`, never on stack (>~64 bytes risks overflow)
- ROM banking (MBC1, up to 1 MB): assets tagged for banking, code stays in bank 0

---

## Refactor Checkpoint

Before closing any task, ask:

> "Does this implementation generalize, or did we hard-code something that will need to change when there are multiple instances of it?"

If the answer is "we hard-coded it," either fix it now or file a follow-up issue immediately.

---

## What This Does NOT Mean

- Don't pre-build systems for features that don't exist yet (YAGNI)
- Don't refactor working code unless a new feature requires it
- Don't add abstraction layers speculatively — the pattern above is the abstraction

---

## Approved Conventions Summary

1. Each system → its own `.c`/`.h` pair
2. `main.c` = timing + input + dispatch only
3. Arrays + `active` flags for any entity type that could have N > 1
4. `src/config.h` for all capacity constants
5. Memory budgets tracked in this doc and `memory/scalability.md`
6. Refactor checkpoint on every task close
