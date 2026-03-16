---
name: rom-banking
description: Use when the ROM shows a blank screen at low FPS (~2 FPS), when questions arise about ROM memory management, bank assignments, or where to place new data assets in Junk Runner.
---

# ROM Banking — Junk Runner

## The Critical Constraint

`state_manager` dispatches states via **plain (non-BANKED) function pointers**. `state_manager_update()` is `BANKED` — it switches to bank 1, then calls `stack[depth-1]->update()` as a plain jump. If the target function landed in bank 2, the wrong bytes execute → blank-screen crash at ~2 FPS.

**All state code (`state_*.c`, `state_manager.c`) must stay in bank 1.**

## SET_BANK Safety Rule

**`SET_BANK` is only safe from HOME bank (bank 0) code.**

Using `SET_BANK` inside a BANKED function that lives in the switchable window (0x4000–0x7FFF) will switch that window away from the function's own bank. The next instruction reads from the newly-mapped bank → wrong bytes → crash.

**Safe:** HOME bank code (no `#pragma bank`, runs at 0x0000–0x3FFF). Examples: `state_overmap.c`, `state_hub.c`, `main.c`.

**Unsafe:** Any `#pragma bank 255` function that calls `SET_BANK` to switch to a *different* bank. Example: `track_init()` (bank 1) calling `SET_BANK(track_tile_data)` while `track_tile_data` is in bank 2 — unmaps bank 1 mid-execution → crash.

**Corollary:** Data assets accessed via `SET_BANK` from a BANKED function must be in the **same bank** as that function, so the switch is a no-op. If they land in a different bank, move them back or refactor the load into HOME bank code.

## Bank Budget

| Bank | Used  | Notes |
|------|-------|-------|
| ROM_0 | ~56% | Fixed/HOME code, always mapped |
| ROM_1 | ~100% | All autobanked modules — 14 bytes free |
| ROM_2 | ~5%  | NPC portraits (pinned to bank 2) |

Current config: MBC5, 16 banks declared (`-Wm-ya16`, `-Wm-yt25`). To add capacity, bump to `-Wm-ya32` — never hardcode bank numbers for game logic or data assets (portraits are the one exception, see below).

## Diagnosing Bank Overflow

**Symptom:** Blank screen, ~2 FPS, game never progresses past boot.

```sh
# Step 1: Check bank percentages
/home/mathdaman/gbdk/bin/romusage build/nuke-raider.gb -a

# Step 2: Find symbols placed in bank 2+ — state_* code here = crash
grep "024[0-9A-Fa-f]\{3\}" build/nuke-raider.map
```

If `_state_ti`, `_state_hu`, `_state_pl`, `_state_ov` appear at `0x024xxx` addresses, bank 1 overflowed and the game will crash at boot.

## Fix: Bank Overflow

All files (except portraits) use `#pragma bank 255` — bankpack fills bank 1, then overflows to banks 2, 3, etc. automatically.

If bank 1 is too full and state code is at risk of overflowing, the fix is to bump `-Wm-ya` to the next power of 2 (e.g., 16→32) in the Makefile. **Never hardcode a bank number for game logic or generated tile/map data.**

`BANKREF` / `BANK()` / `SET_BANK()` resolve correctly at link time regardless of which bank a file lands in — no changes needed in callers, **provided the SET_BANK safety rule above is respected**。

## Asset Banking Rules

| Asset type | Pragma | Reason |
|------------|--------|--------|
| `npc_*_portrait.c` | `#pragma bank 2` (hardcoded via `--bank 2`) | **Must not autobank**: portraits compete with game logic for bank 1; if they win, `track_tile_data`/`player_tile_data` move to bank 2, and `SET_BANK` inside BANKED functions crashes. See Makefile comment. |
| `*_tiles.c` (generated) | `#pragma bank 255` | Autobanked — bankpack places in bank 1 or overflow |
| `*_map.c` (generated) | `#pragma bank 255` | Autobanked |
| State modules (`state_*.c`) | `#pragma bank 255` | Must stay in bank 1 with state_manager |
| `music.c` | no `#pragma bank` (bank 0) | VBL ISR calls music_tick — must be in HOME bank |

## Checklist: After Adding Any Large Asset

1. Build: `GBDK_HOME=/home/mathdaman/gbdk make`
2. Check bank 1: `romusage build/nuke-raider.gb -a` → if bank 1 ≥ 95%, act now
3. Check for state code overflow: `grep "024[0-9A-Fa-f]\{3\}" build/nuke-raider.map`
4. Check that `track_tile_data` and `player_tile_data` are still in bank 1 (verify in `.noi` file)
5. If state code appears in bank 2+: fix is to bump `-Wm-ya32` in the Makefile

## Autobanker Behavior

- `#pragma bank 255` → bankpack assigns automatically, fills bank 1 first, then spills to bank 2, 3, etc.
- Bankpack fills banks sequentially — state code lands in bank 1, overflow data lands in bank 2+
- With 16 banks declared (`-Wm-ya16`), banks 2–15 are available for overflow

## Why BANKED Function Pointers Aren't the Fix

CLAUDE.md documents that `void (*fn)(void) BANKED` in a struct field is **broken on SDCC/SM83**: it generates double-dereference code (reads 2 bytes from the function's address, then jumps there → garbage). The correct fix is to keep all state code in bank 1, not to add `BANKED` to the struct fields.
