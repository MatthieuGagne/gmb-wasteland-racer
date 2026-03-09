# Player Square — Design Document
**Date:** 2026-03-08

## Overview

Add a moveable player square that appears after the title screen. The player is an 8×8 sprite controlled by the D-pad, clamped to screen bounds.

## Domain Boundaries

The player is its own domain module (`src/player.c` + `src/player.h`). `main.c` owns frame timing and hardware input reads; the player module owns all player state and behavior.

## Files

| File | Role |
|------|------|
| `src/player.h` | Public API + `clamp_u8` inline helper |
| `src/player.c` | Implementation, static state |
| `tests/test_player.c` | Unit tests (gcc + Unity, no GBDK) |

## API

```c
void player_init(void);              // load tile, set start pos, enable sprites
void player_update(uint8_t input);   // update position from joypad bitmask
void player_render(void);            // move_sprite(0, px, py) — call after wait_vbl_done()
```

`clamp_u8(v, lo, hi)` — `static inline` in the header, keeps it inlinable and testable.

## Player State

File-scoped statics in `player.c`:
- `static uint8_t px, py` — current sprite position
- `static const uint8_t player_tile_data[16]` — solid 8×8 tile (GBDK format)

No heap, no large stack allocation.

## Sprite Coordinate System

GB hardware offsets: x=8 is leftmost visible column, y=16 is topmost visible row.

- Initial position: center screen (~`px=80, py=72`)
- Clamp x: `[8, 152]`
- Clamp y: `[16, 136]`

## Movement

- 1 pixel per frame per direction held
- All four cardinal directions supported simultaneously (diagonal movement allowed)
- Input parameter is the raw `joypad()` bitmask; player module checks `J_LEFT`, `J_RIGHT`, `J_UP`, `J_DOWN`

## VBlank Discipline

`player_render()` must be called after `wait_vbl_done()` in `main.c`. The frame loop in `STATE_PLAYING`:

```c
wait_vbl_done();
player_update(joypad());
player_render();
```

## Game Boy Constraints

- `clamp_u8` is `static inline` to avoid Z80 call overhead on a hot path
- Player state is static globals — safe for 8KB WRAM budget
- SDCC compiles each `.c` to a separate `.o`; no ROM penalty for the split

## Testing

`tests/test_player.c` covers:
- `clamp_u8` at min, max, and within bounds
- `player_update` movement in each direction
- `player_update` clamping at all four edges
- `move_sprite` mocked as a no-op in `tests/mocks/`
