---
name: rom-banking
description: Use when the ROM shows a blank screen at low FPS (~2 FPS), when questions arise about ROM memory management, bank assignments, or where to place new data assets in Nuke Raider.
---

# ROM Banking — Nuke Raider

## The Critical Constraint

`state_manager` dispatches states via **plain (non-BANKED) function pointers**. `state_manager_update()` is `BANKED` — it switches to bank 1, then calls `stack[depth-1]->update()` as a plain jump. If the target function landed in bank 2, the wrong bytes execute → blank-screen crash at ~2 FPS.

**All state code (`state_*.c`, `state_manager.c`) must stay in bank 1.**

## Bank Budget

| Bank | Used  | Notes |
|------|-------|-------|
| ROM_0 | ~46% | Fixed/HOME code, always mapped |
| ROM_1 | ~100% | All autobanked modules — overflows naturally into bank 2+ |
| ROM_2 | ~5%  | Autobank overflow (portraits, tiles, maps all `#pragma bank 255`) |

Total autobanked data: ~16,370 + 788 bytes across banks 1–2 (MBC5, 16 banks declared).

## Diagnosing Bank Overflow

**Symptom:** Blank screen, ~2 FPS, game never progresses past boot.

```sh
# Step 1: Check bank percentages
/home/mathdaman/gbdk/bin/romusage build/nuke-raider.gb -a

# Step 2: Find symbols placed in bank 2+ — state_* code here = crash
grep "024[0-9A-Fa-f]\{3\}" build/nuke-raider.map
```

If `_state_ti`, `_state_hu`, `_state_pl`, `_state_ov` appear at `0x024xxx` addresses, bank 1 overflowed and the game will crash at boot.

## Fix: Bank Overflow with MBC5 + 16 Banks

All files use `#pragma bank 255` — bankpack fills bank 1, then overflows to banks 2, 3, etc. automatically. No manual bank assignments needed for data assets.

The only fix needed if state code overflows bank 1 is to ensure there is room — with 16 banks declared, bankpack has space to place data in higher banks, keeping bank 1 for state code.

`BANKREF` / `BANK()` / `SET_BANK()` resolve correctly at link time regardless of which bank a file lands in — no changes needed in callers.

## Asset Banking Rules

| Asset type | Pragma | Reason |
|------------|--------|--------|
| `npc_*_portrait.c` | `#pragma bank 255` | Autobanked — bankpack places in bank 2+ naturally |
| `*_tiles.c` (generated) | `#pragma bank 255` | Autobanked — bankpack places in bank 2+ naturally |
| `*_map.c` (generated) | `#pragma bank 255` | Autobanked — bankpack places in bank 2+ naturally |
| State modules (`state_*.c`) | `#pragma bank 255` | Must stay in bank 1 with state_manager |
| Music data | check — may be large | If bank 1 is tight, move to explicit bank |

## Checklist: After Adding Any Large Asset

1. Build: `GBDK_HOME=/home/mathdaman/gbdk make`
2. Check bank 1: `romusage build/nuke-raider.gb -a` → if bank 1 ≥ 95%, act now
3. Check for state code overflow: `grep "024[0-9A-Fa-f]\{3\}" build/nuke-raider.map`
4. If state code appears in bank 2+: this should not happen with 16 banks — investigate why bankpack is not overflowing data correctly

## Autobanker Behavior

- `#pragma bank 255` → bankpack assigns automatically, fills bank 1 first, then spills to bank 2, 3, etc.
- All files (state code, data assets, portraits, tiles, maps) use `#pragma bank 255`
- Bankpack fills banks sequentially — state code lands in bank 1, overflow data lands in bank 2+
- With 16 banks declared (`-Wm-ya16`), there is ample room for growth without manual bank management

## Why BANKED Function Pointers Aren't the Fix

CLAUDE.md documents that `void (*fn)(void) BANKED` in a struct field is **broken on SDCC/SM83**: it generates double-dereference code (reads 2 bytes from the function's address, then jumps there → garbage). The correct fix is to keep all state code in bank 1, not to add `BANKED` to the struct fields.
