---
name: bank-pre-write
description: Hard gate — invoke before writing any src/*.c or src/*.h file. Validates bank manifest, pragma, and SET_BANK safety.
---

# Bank Pre-Write Gate

**STOP.** Before writing or editing any `src/*.c` or `src/*.h` file, run the checks below. For `.c` files: all 5 checks apply. For `.h` files: Checks 3, 4, and 5 apply (headers carry no `#pragma bank`; the manifest covers `.c` files only).

## Check 1 — Manifest entry exists

Read `bank-manifest.json` at the repo root.

- If the file you are about to write is a `.c` file and is NOT in the manifest → **BLOCK**:
  > "Add an entry to `bank-manifest.json` for `src/<file>.c` before writing it. Specify bank number (255 for autobank, 1 for state code, 2 for portraits, 0 for HOME bank code) and reason."

- If creating a new `state_*.c` file → manifest bank **must** be 1 (or 0 if it calls SET_BANK).
- If creating a new `npc_*_portrait.c` file → manifest bank **must** be 2.

## Check 2 — Pragma matches manifest

Look up the file's expected bank in `bank-manifest.json`.

| Manifest bank | Required in first 5 lines of `.c` file |
|---------------|----------------------------------------|
| 0             | No `#pragma bank` line at all |
| 1             | `#pragma bank 1` |
| 2             | `#pragma bank 2` |
| 255           | `#pragma bank 255` |

If the pragma you are about to write doesn't match → **BLOCK and correct it before writing.**

## Check 3 — No `SET_BANK` inside banked code

If the file's manifest bank is **not 0** (i.e., it lives in the switchable window 0x4000–0x7FFF):

- **BLOCK** any `SET_BANK(...)` call inside that file.
  > Reason: calling SET_BANK from banked code switches the window away from the running function → crash.
  > Fix: move the SET_BANK call into a bank-0 caller, or move the calling function to a bank-0 file.

Bank-0 files (`main.c`, `music.c`, `hub_data.c`, `state_hub.c`, `state_overmap.c`) may freely call `SET_BANK`.

## Check 4 — No `BANKED` on static functions or bank-0 functions

- `static` functions must NOT be `BANKED` — they cannot be called cross-bank anyway.
- Bank-0 functions must NOT be `BANKED` — they're always mapped; the keyword generates useless trampoline overhead.
- Function pointer fields in structs must NOT be `BANKED` — SDCC generates broken double-dereference code. Use plain `void (*fn)(void)`.

## Check 5 — Makefile `--bank` flags consistent

NPC portrait files are pinned via `--bank 2` in the Makefile `png_to_tiles.py` invocation.

If adding a new generated file that must be pinned, ensure the Makefile passes `--bank N` to `png_to_tiles.py` and the manifest entry matches.

## If all checks pass

Proceed with writing the file. Announce: "bank-pre-write: all checks passed for `src/<file>.c` (bank N)."
