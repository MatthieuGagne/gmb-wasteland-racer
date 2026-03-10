# Autobanking Design — 2026-03-10

## Goal

Switch from manual MBC1 bank management to GBDK's `-autobank` linker flag so the toolchain
automatically assigns ROM banks to assets and `BANKED` functions, eliminating hand-managed bank
numbers as the ROM grows. Closes #36.

## Approach

Single PR, staged commits (Approach C). All changes land atomically so there is no broken
intermediate build, but history is readable by logical area.

## Validated API (GBDK 4.x)

- Makefile flags: `-Wl-j -Wm-ya4 -autobank -Wb-ext=.rel` (verified from installed GBDK example)
- `#pragma bank 255` — sentinel for "let autobank assign this file to a bank"
- `BANKED` / `NONBANKED` — placed after `)` on function signature; defined as `__banked` / `__nonbanked`
- `BANKREF(VARNAME)` — emits a linker symbol encoding the bank number; goes in `.c` after `#pragma bank 255`
- `BANKREF_EXTERN(VARNAME)` — extern declaration for the linker symbol; goes in `.h`
- `CURRENT_BANK` — macro alias for `_current_bank`; tracks the current ROM bank
- `SWITCH_ROM(b)` — switches MBC1 bank and updates `CURRENT_BANK`
- `SET_BANK` / `RESTORE_BANK` — **not in GBDK**; we define them in `src/banking.h`

## Design Sections

### 1. Makefile

Add autobank flags to `CFLAGS` (lcc ignores inapplicable flags per pass):

```makefile
CFLAGS := -Wa-l -Wl-m -Wl-j -Wm-ya4 -autobank -Wb-ext=.rel
```

`-Wm-yt1` stays in `ROMFLAGS`. `-autobank` automatically adds `-Wm-yoA` when no `-yo*` is present.

### 2. `src/banking.h` (new file)

```c
#ifndef BANKING_H
#define BANKING_H
#include <gb/gb.h>

/* Save current bank, switch to the bank holding VAR, restore afterward.
   Usage:
     SET_BANK(my_asset);
     use_data(my_asset);
     RESTORE_BANK();
*/
#define SET_BANK(var)   uint8_t _saved_bank = CURRENT_BANK; SWITCH_ROM(BANK(var))
#define RESTORE_BANK()  SWITCH_ROM(_saved_bank)

#endif
```

### 3. All non-`main.c` source files

Top of every `.c` except `main.c`:
```c
#pragma bank 255
```

Every public function — definition (`.c`) and declaration (`.h`):
```c
void track_init(void) BANKED;       /* .h */
void track_init(void) BANKED { }    /* .c */
```

Static helpers and ISR handlers: leave untagged (or `NONBANKED` if needed). `main.c` is bank 0.
`BANKED` functions have automatic bank switching via SDCC trampoline — no manual `SET_BANK` needed at call sites.

### 4. Asset files — `BANKREF`

In asset `.c` files (`track_tiles.c`, `track_map.c`, `dialog_data.c`, `player_sprite.c`):
```c
#pragma bank 255
BANKREF(track_tile_data)
const uint8_t track_tile_data[] = { ... };
```

In corresponding `.h` files:
```c
BANKREF_EXTERN(track_tile_data)
extern const uint8_t track_tile_data[];
```

### 5. Call sites

Wherever banked const data is passed directly to GBDK (not via a `BANKED` function):
```c
SET_BANK(track_tile_data);
set_bkg_data(0, TRACK_TILE_COUNT, track_tile_data);
RESTORE_BANK();
```

`BANKED` functions do not need `SET_BANK` at their call sites.

### 6. Generator script updates

`tools/png_to_tiles.py` and `tools/tmx_to_c.py` must emit before each exported array:
```c
#pragma bank 255
BANKREF(<varname>)
```
so that regenerating the asset files preserves banking boilerplate.

## Commit Sequence

1. `Makefile + src/banking.h` — linker flags + macro definitions
2. `#pragma bank 255` + `BANKED` on all `.c`/`.h` files
3. `BANKREF` on asset files + `SET_BANK`/`RESTORE_BANK` at call sites
4. Generator script updates

## Acceptance Criteria (from issue #36)

- AC1: `GBDK_HOME=~/gbdk make` builds with `-autobank` flags, no linker errors
- AC2: `romusage` shows assets distributed across banks, not all in bank 0
- AC3: No function or data array > ~16 KB in bank 0
- AC4: `make test` still passes (host-side tests unaffected by banking macros)
- AC5: Smoketest in Emulicious confirms tiles, maps, dialog render correctly
