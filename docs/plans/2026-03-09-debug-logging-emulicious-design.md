# Debug Logging System — Emulicious Design

**Date:** 2026-03-09
**Status:** Approved, ready for implementation
**Supersedes:** `2026-03-09-debug-logging-design.md` (mGBA serial approach — abandoned due to serial slowdown making game unplayable)

## Goal

Add compile-controlled debug logging to diagnose a freeze that occurs after 2–3 minutes of gameplay. Suspected cause: counter overflow or `stream_buf_len` out-of-bounds write corrupting adjacent memory. Output goes to a WRAM ring buffer — zero serial overhead, zero blocking, inspected post-freeze via Emulicious's memory viewer.

## Approach: WRAM Ring Buffer

Instead of writing bytes to serial registers, each `DLOG()` call writes a 3-byte entry into a fixed-size circular buffer in WRAM. No I/O, no waiting — just array writes. After the freeze, the developer pauses Emulicious and inspects the buffer to read the last 64 entries leading up to the halt.

## Module Structure

- `src/debug.h` — public API macros, tag constants, guarded by `#ifdef DEBUG`
- `src/debug.c` — ring buffer storage and `dlog()` write function; stubs when `DEBUG` not defined

All `src/*.c` files are auto-compiled by the Makefile. `debug.c` is always compiled, but its functions are empty stubs in release. Macros expand to nothing without `DEBUG`, so call sites have zero code overhead.

**Enabling:** `DEBUG=1 GBDK_HOME=/home/mathdaman/gbdk make`
Makefile adds `-DDEBUG` to `CFLAGS` when `DEBUG=1`.

## API

```c
// src/debug.h
#define DLOG_FRAME    0x01u  /* frame_count (uint16_t — survives 3+ minutes) */
#define DLOG_CAM_X    0x02u  /* cam_x after camera_update() */
#define DLOG_CAM_Y    0x03u  /* cam_y after camera_update() */
#define DLOG_STREAM   0x04u  /* stream_buf_len (overflow suspect) */
#define DLOG_PX       0x05u  /* player world x */
#define DLOG_PY       0x06u  /* player world y */

#ifdef DEBUG
  void dlog(uint8_t tag, uint16_t val);
  #define DLOG(tag, val) dlog(tag, (uint16_t)(val))
#else
  #define DLOG(tag, val)
#endif
```

## Ring Buffer

```c
// src/debug.c
#define DLOG_BUF_ENTRIES 64u

typedef struct {
    uint8_t tag;
    uint8_t val_hi;
    uint8_t val_lo;
} DlogEntry;

static DlogEntry dlog_buf[DLOG_BUF_ENTRIES];
static uint8_t   dlog_head = 0u;

void dlog(uint8_t tag, uint16_t val) {
    dlog_buf[dlog_head].tag    = tag;
    dlog_buf[dlog_head].val_hi = (uint8_t)(val >> 8);
    dlog_buf[dlog_head].val_lo = (uint8_t)(val & 0xFFu);
    dlog_head = (dlog_head + 1u) & 63u;
}
```

Each entry is 3 bytes (no alignment padding needed — all `uint8_t`). Struct layout stored 3 bytes per entry avoids SDCC struct alignment surprises.

## Memory Budget

- WRAM: `64 × 3 + 1 = 193 bytes` in DEBUG builds only; zero in release (stubs and macros removed).
- ROM: ~20–30 bytes for `dlog()` in DEBUG builds; zero in release.
- No OAM or VRAM impact.

## Instrumentation Points

| File | Location | Macro | Purpose |
|------|----------|-------|---------|
| `main.c` | After `wait_vbl_done()` | `DLOG(DLOG_FRAME, frame_count)` | Timestamp; `frame_count` is `static uint16_t` added to `main.c` |
| `camera_update()` | After all 4 edge checks | `DLOG(DLOG_CAM_X, ncx)` | Camera position |
| `camera_update()` | After all 4 edge checks | `DLOG(DLOG_CAM_Y, ncy)` | Camera position |
| `camera_update()` | After all 4 edge checks | `DLOG(DLOG_STREAM, stream_buf_len)` | Buffer fill after enqueue |
| `camera_flush_vram()` | Before flush loop | `DLOG(DLOG_STREAM, stream_buf_len)` | Buffer fill before flush (key overflow check) |
| `player_render()` | After computing hw coords | `DLOG(DLOG_PX, (uint16_t)px)` | Player world x |
| `player_render()` | After computing hw coords | `DLOG(DLOG_PY, (uint16_t)py)` | Player world y |

`stream_buf_len` is logged twice per frame (after enqueue in `camera_update`, before flush in `camera_flush_vram`). If it ever reads `> 4` before the flush, that's the overflow.

## Files Changed

- `src/debug.h` — new
- `src/debug.c` — new
- `src/main.c` — add `#include "debug.h"`, `static uint16_t frame_count`, `DLOG(DLOG_FRAME, frame_count)` and `frame_count++` after `wait_vbl_done()`
- `src/camera.c` — add `#include "debug.h"`, `DLOG` calls in `camera_update()` and `camera_flush_vram()`
- `src/player.c` — add `#include "debug.h"`, `DLOG` calls in `player_render()`
- `Makefile` — add `ifeq ($(DEBUG),1) CFLAGS += -DDEBUG endif`

## Emulicious Setup

1. Download `Emulicious.jar` from https://emulicious.net/ — place in project root (add to `.gitignore`)
2. Run: `java -jar Emulicious.jar build/wasteland-racer.gb`
3. Build with debug: `DEBUG=1 GBDK_HOME=/home/mathdaman/gbdk make`

## Reading the Log After a Freeze

1. Reproduce the freeze in Emulicious
2. Pause emulation (Space bar or toolbar)
3. Open **Tools → Memory** in Emulicious
4. Find `dlog_buf` WRAM address: open `build/wasteland-racer.map`, search for `dlog_buf`
5. In the memory viewer, navigate to that address
6. Read `dlog_head` (1 byte before the buffer, or tracked separately) — entries run backward from `dlog_head - 1` wrapping around
7. Each 3-byte entry: `tag | val_hi | val_lo` — decode `val = (val_hi << 8) | val_lo`

**What to look for:**
- `DLOG_STREAM` value `> 4` → `stream_buf_len` overflow → OOB write → memory corruption
- `DLOG_FRAME` stops incrementing → game loop stalled
- `DLOG_CAM_X` / `DLOG_CAM_Y` jumping to unexpected values → cam state corrupted
