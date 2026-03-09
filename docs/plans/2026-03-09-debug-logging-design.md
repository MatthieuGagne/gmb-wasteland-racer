# Debug Logging System — Design

**Date:** 2026-03-09
**Status:** Approved, ready for implementation

## Goal

Add compile-controlled debug logging to aid debugging of memory management, camera streaming, player movement, and frame timing. Output goes to mGBA's log console via GB serial registers — no screen clutter, zero overhead in release builds.

## Module Structure

- `src/debug.h` — public API macros, guarded by `#ifdef DEBUG`
- `src/debug.c` — serial writer + hand-rolled int formatter; stubs when `DEBUG` not defined

All `src/*.c` files are auto-compiled by the Makefile. `debug.c` is always compiled, but its functions are empty stubs in release. Macros expand to nothing without `DEBUG`, so call sites have zero code overhead.

**Enabling:** pass `DEBUG=1` on the build command line (Makefile adds `-DDEBUG` to `CFLAGS`).

## API

```c
// src/debug.h
#ifdef DEBUG
  void debug_str(const char *s);
  void debug_int(const char *label, int16_t val);
  void debug_frame(uint8_t frame_count);
  #define DBG_STR(s)           debug_str(s)
  #define DBG_INT(label, val)  debug_int(label, (int16_t)(val))
  #define DBG_FRAME(n)         debug_frame(n)
#else
  #define DBG_STR(s)
  #define DBG_INT(label, val)
  #define DBG_FRAME(n)
#endif
```

- `debug_str` — writes a null-terminated string byte-by-byte over serial (SB_REG / SC_REG).
- `debug_int` — writes `"label: -123\n"` using a hand-rolled int formatter (no `stdio` / `printf` dependency).
- `debug_frame` — writes `"--- frame N ---\n"` as a per-frame separator in the log.

## Serial Output Mechanism

Write each byte via GB serial registers:
```c
SB_REG = c;
SC_REG = 0x81;  // start transfer, internal clock
while (SC_REG & 0x80);  // wait for completion
```
mGBA captures serial output and prints it to its log console. Slow per byte, but acceptable for sparse logging (not called in tight inner loops).

## Instrumentation Points

| Location | Macro | Trigger |
|---|---|---|
| `main.c` VBlank phase | `DBG_FRAME(frame_count)` | Every frame |
| `camera_update()` | `DBG_INT("cam_x", ncx)`, `DBG_INT("cam_y", ncy)`, `DBG_INT("stream_buf_len", stream_buf_len)` | After computing new camera position |
| `camera_flush_vram()` | `DBG_INT("flush_len", stream_buf_len)` | Before flushing (catches overflow: max is `STREAM_BUF_SIZE` = 4) |
| `player_update()` | `DBG_INT("px", px)`, `DBG_INT("py", py)` | When a move is blocked by `corners_passable` |
| `player_render()` | `DBG_INT("hw_x", hw_x)`, `DBG_INT("hw_y", hw_y)` | Every frame |

A `static uint8_t frame_count` is added to `main.c`, incremented each VBlank.

## Memory Budget Impact

- ROM: `debug.c` adds ~100–150 bytes in `DEBUG` builds only; zero bytes in release (stubs inline to nothing).
- WRAM: no allocations — `debug_str` and `debug_int` are stack-only with tiny local buffers.
- No impact on OAM or VRAM.

## Files Changed

- `src/debug.h` — new
- `src/debug.c` — new
- `src/main.c` — add `#include "debug.h"`, `frame_count`, `DBG_FRAME`
- `src/camera.c` — add `DBG_INT` calls in `camera_update` and `camera_flush_vram`
- `src/player.c` — add `DBG_INT` calls in `player_update` and `player_render`
- `Makefile` — support `DEBUG=1` → `-DDEBUG` in `CFLAGS`
