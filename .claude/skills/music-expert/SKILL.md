# Music Expert — Junk Runner

Use when working with hUGEDriver music integration, song data, APU registers, or audio for the Junk Runner GBC project.

---

## hUGEDriver v6.1.3 — Key Facts

- **Source:** https://github.com/SuperDisk/hUGEDriver
- **License:** Public domain
- **Release zip:** `https://github.com/SuperDisk/hUGEDriver/releases/download/v6.1.3/hUGEDriver-6.1.3.zip`
- **Vendored in this project:** `lib/hUGEDriver/include/hUGEDriver.h` + `lib/hUGEDriver/gbdk/hUGEDriver.lib`

---

## API

```c
#include "hUGEDriver.h"

// Initialize driver with a song. Call inside __critical.
void hUGE_init(const hUGESong_t *song);

// Advance one tick. Call exactly once per VBlank.
// hUGEDriver.lib is in bank 0 — always accessible.
void hUGE_dosound(void);

// Mute/unmute individual channels
void hUGE_mute_channel(enum hUGE_channel_t ch, enum hUGE_mute_t mute);
// Channels: HT_CH1=0, HT_CH2, HT_CH3, HT_CH4
// Mute:     HT_CH_PLAY=0, HT_CH_MUTE

// Jump to a pattern position
void hUGE_set_position(unsigned char pattern);

// Force wave channel to reload (needed if you externally modified wave RAM)
void hUGE_reset_wave(void);   // sets hUGE_current_wave = 100

extern volatile unsigned char hUGE_current_wave;
extern volatile unsigned char hUGE_mute_mask;
```

---

## APU Enable (required before hUGE_init)

```c
NR52_REG = 0x80;  /* bit7=1: enable sound system */
NR51_REG = 0xFF;  /* route all 4 channels to both left and right */
NR50_REG = 0x77;  /* max master volume: left=7, right=7 */
```

---

## hUGESong_t Struct

```c
typedef struct hUGESong_t {
    unsigned char tempo;
    const unsigned char * order_cnt;      /* pointer to order count byte */
    const unsigned char ** order1;        /* CH1 pattern order table */
    const unsigned char ** order2;        /* CH2 pattern order table */
    const unsigned char ** order3;        /* CH3 pattern order table */
    const unsigned char ** order4;        /* CH4 pattern order table */
    const hUGEDutyInstr_t * duty_instruments;
    const hUGEWaveInstr_t * wave_instruments;
    const hUGENoiseInstr_t * noise_instruments;
    const hUGERoutine_t ** routines;      /* NULL if no custom routines */
    const unsigned char * waves;          /* 256-byte wave table */
} hUGESong_t;
```

Songs are exported from hUGETracker as "GBDK .c" format. The project uses the hUGEDriver sample song as a placeholder (`src/music_data.c`).

---

## CRITICAL: Banking Rule for music.c

**`music.c` must NOT have `#pragma bank 255`.**

`SET_BANK(var)` expands to inline `SWITCH_ROM(BANK(var))`. If `music_tick()` lived in a switched ROM bank (0x4000–0x7FFF), calling `SET_BANK` would remap that window to the data bank — the CPU's next instructions would come from the data bank's bytes → garbage execution.

`music.c` stays in bank 0 (0x0000–0x3FFF, always accessible). Same pattern as `main.c`.

`music_data.c` uses `#pragma bank 255` as normal — it only runs while its bank is switched in.

---

## Version Pinning

hUGETracker and hUGEDriver **must match exactly** (e.g., hUGETracker 1.0b10 requires hUGEDriver 1.0b10). The data format changes between versions — mismatches produce silent corruption or crashes. This project vendors v6.1.3; do not update one without the other.

---

## Sound Effects (SFX)

hUGEDriver has no built-in SFX system. Coordinate SFX via channel muting:

```c
// 1. Release a channel from driver control (0=CH1, 1=CH2, 2=CH3/wave, 3=CH4/noise)
hUGE_mute_channel(HT_CH2, HT_CH_MUTE);

// 2. Play SFX on that channel using your SFX engine

// 3. Restore channel to hUGEDriver
hUGE_mute_channel(HT_CH2, HT_CH_PLAY);
```

**Wave channel (CH3) special case:** If you write to wave RAM (FF30–FF3F) while CH3 is released, set:
```c
hUGE_current_wave = HT_NO_WAVE;   // forces driver to reload waveform on restore
```

Effects 5, 8, B, D, F continue to process even on muted channels.

**Compatible SFX engines:** VGM2GBSFX, CBT-FX, Libbet's SFX Engine.

---

## Integration Pattern

### music_data.c (banked)

```c
#pragma bank 255
#include <gb/gb.h>
#include <stddef.h>
#include "banking.h"
#include "hUGEDriver.h"

BANKREF(music_data_song)

/* ... all static pattern/instrument/wave arrays ... */

const hUGESong_t music_data_song = {
    2,                   /* tempo */
    &order_cnt,
    order1, order2, order3, order4,
    duty_instruments,
    wave_instruments,
    noise_instruments,
    NULL,                /* routines */
    waves
};
```

### music_data.h

```c
#ifndef MUSIC_DATA_H
#define MUSIC_DATA_H
#include <gb/gb.h>
#include "banking.h"
#include "hUGEDriver.h"

BANKREF_EXTERN(music_data_song)
extern const hUGESong_t music_data_song;
#endif
```

### music.c (bank 0 — no #pragma)

```c
/* No #pragma bank 255 — see CRITICAL note above */
#include <gb/gb.h>
#include <gb/hardware.h>
#include "banking.h"
#include "hUGEDriver.h"
#include "music_data.h"
#include "music.h"

void music_init(void) {
    NR52_REG = 0x80;
    NR51_REG = 0xFF;
    NR50_REG = 0x77;
    __critical {
        { SET_BANK(music_data_song);
          hUGE_init(&music_data_song);
          RESTORE_BANK(); }
    }
}

void music_tick(void) {
    { SET_BANK(music_data_song);
      hUGE_dosound();
      RESTORE_BANK(); }
}
```

### music.h

```c
#ifndef MUSIC_H
#define MUSIC_H
/* No BANKED — these functions are in bank 0 */
void music_init(void);
void music_tick(void);
#endif
```

### main.c wiring

```c
#include "music.h"

static void vbl_isr(void) {
    frame_ready = 1;
    move_bkg(0, (uint8_t)cam_y);
    /* DO NOT call music_tick() here — see CRITICAL note below */
}

void main(void) {
    DISPLAY_OFF;
    init_palettes();
    player_init();
    music_init();          /* before add_VBL */
    add_VBL(vbl_isr);
    set_interrupts(VBL_IFLAG);
    DISPLAY_ON;

    while (1) {
        while (!frame_ready);
        frame_ready = 0;
        music_tick();      /* once per VBL, safely in main context */
        input_update();
        state_manager_update();
    }
}
```

**CRITICAL — Never call `music_tick()` from a VBL ISR:**

`music_tick()` calls `SET_BANK`/`SWITCH_ROM`, which is a two-step write:
`_current_bank = b; rROMB0 = b`. If the ISR fires between these two writes while a
BANKED function trampoline is in progress in the main loop, the shadow variable and
MBC hardware disagree. `RESTORE_BANK` in the ISR then restores from the stale shadow
value — corrupting bank state for the trampoline's epilogue. After several deep BANKED
call sequences (e.g., repeated state transitions), the mismatched bank causes a crash.

**Rule:** The VBL ISR does display work only (`move_bkg`, sprite updates). All
`SET_BANK` activity — including `music_tick()` — runs in the main loop after
`frame_ready = 0`. This preserves exactly-once-per-VBL timing without ISR bank hazards.

---

## Makefile Changes

```makefile
# Add to CFLAGS:
CFLAGS := ... -Ilib/hUGEDriver/include

# Add lib to the ROM link rule using -Wl-k / -Wl-l (NOT as a positional arg):
$(TARGET): $(OBJS) | build
	$(LCC) $(CFLAGS) $(ROMFLAGS) -o $@ $(OBJS) -Wl-k$(CURDIR)/lib/hUGEDriver/gbdk -Wl-lhUGEDriver.lib
```

### CRITICAL: Do NOT pass hUGEDriver.lib as a positional argument

```makefile
# WRONG — bankpack will process the .lib, overwrite hUGEDriver.rel with just
# the 68-byte ar symbol index, and _hUGE_init/_hUGE_dosound become undefined:
$(LCC) ... $(OBJS) lib/hUGEDriver/gbdk/hUGEDriver.lib

# CORRECT — route directly to sdldgb as a search-path library (bypasses bankpack):
$(LCC) ... $(OBJS) -Wl-k$(CURDIR)/lib/hUGEDriver/gbdk -Wl-lhUGEDriver.lib
```

`-Wl-k<dir>` adds a library search directory; `-Wl-l<name>` names the lib to link. This is the same pattern GBDK uses internally for `sm83.lib` and `gb.lib`.

---

## Vendoring hUGEDriver (one-time setup)

```bash
wget -q https://github.com/SuperDisk/hUGEDriver/releases/download/v6.1.3/hUGEDriver-6.1.3.zip \
     -O /tmp/hUGEDriver.zip
mkdir -p lib/hUGEDriver/include lib/hUGEDriver/gbdk
unzip -j /tmp/hUGEDriver.zip include/hUGEDriver.h -d lib/hUGEDriver/include/
unzip -j /tmp/hUGEDriver.zip gbdk/hUGEDriver.lib   -d lib/hUGEDriver/gbdk/
```

---

## Adapting a hUGETracker Export

1. Export song from hUGETracker as "GBDK .c" format
2. Add to the top of the exported file:
   ```c
   #pragma bank 255
   #include <gb/gb.h>
   #include "banking.h"
   BANKREF(your_song_name)
   ```
3. Rename the exported `const hUGESong_t ...` variable to match your `BANKREF` name
4. Update `music_data.h` with `BANKREF_EXTERN` and `extern` declaration
5. Update `music.c` to reference the new song name in `SET_BANK` and `hUGE_init`

---

## Placeholder Song Source

The current placeholder uses the hUGEDriver sample song:
```
https://raw.githubusercontent.com/SuperDisk/hUGEDriver/master/gbdk_example/src/sample_song.c
```
68 orders, 40 patterns. Replace with a real composition when ready.

---

## APU Register Map (FF10–FF3F)

```
Name  Addr  Bits        Function
-----------------------------------------------------------------------
NR10  FF10  -PPP NSSS   CH1 sweep: pace, negate, shift
NR11  FF11  DDLL LLLL   CH1 duty + length load (64-L)
NR12  FF12  VVVV APPP   CH1 volume envelope: init vol, add, period
NR13  FF13  FFFF FFFF   CH1 period low (write-only)
NR14  FF14  TL-- -FFF   CH1 trigger, length enable, period high

NR21  FF16  DDLL LLLL   CH2 duty + length load
NR22  FF17  VVVV APPP   CH2 volume envelope
NR23  FF18  FFFF FFFF   CH2 period low (write-only)
NR24  FF19  TL-- -FFF   CH2 trigger, length enable, period high

NR30  FF1A  E--- ----   CH3 DAC enable (bit 7)
NR31  FF1B  LLLL LLLL   CH3 length load (256-L)
NR32  FF1C  -VV- ----   CH3 volume: 00=0%, 01=100%, 10=50%, 11=25%
NR33  FF1D  FFFF FFFF   CH3 period low (write-only)
NR34  FF1E  TL-- -FFF   CH3 trigger, length enable, period high

NR41  FF20  --LL LLLL   CH4 length load
NR42  FF21  VVVV APPP   CH4 volume envelope
NR43  FF22  SSSS WDDD   CH4 clock shift, LFSR width, divisor code
NR44  FF23  TL-- ----   CH4 trigger, length enable

NR50  FF24  ALLL BRRR   Master vol: Vin-L, left vol (7=max), Vin-R, right vol
NR51  FF25  NW21 NW21   Panning: upper nibble=left, lower nibble=right per channel
NR52  FF26  P--- NW21   APU power (bit 7); channel active flags (read-only bits 0-3)

FF30–FF3F               Wave RAM: 16 bytes = 32 four-bit samples (high nibble first)
```

**Read-back mask (ORed with written value):**
CH1: $80/$3F/$00/$FF/$BF — CH2: $FF/$3F/$00/$FF/$BF — CH3: $7F/$FF/$9F/$FF/$BF — CH4: $FF/$FF/$00/$00/$BF

---

## APU Frame Sequencer

Clocked at **512 Hz** off the DIV register (bit 4 falling edge). Drives modulation at lower rates:

```
Step  Length Ctr  Vol Env  Sweep
---------------------------------
0     Clock       -        -
1     -           -        -
2     Clock       -        Clock
3     -           -        -
4     Clock       -        -
5     -           -        -
6     Clock       -        Clock
7     -           Clock    -
---------------------------------
Rate  256 Hz      64 Hz    128 Hz
```

**APU timing is NOT affected by CGB double-speed mode** — same rates regardless of CPU speed.

---

## APU Hardware Notes

- `NR52_REG` (FF26) bit 7 = master on/off; turning off clears all APU registers (FF10–FF51) instantly. Wave RAM is unaffected.
- `NR51_REG` (FF25) = channel panning; `0xFF` = all channels on both speakers.
- `NR50_REG` (FF24) = master volume; `0x77` = max (7 left, 7 right). Bit 7/3 = Vin panning (ignore).
- hUGEDriver uses CH1 (pulse+sweep), CH2 (pulse), CH3 (wave), CH4 (noise).
- **DAC enable — CH1/CH2/CH4:** DAC on when `NRx2 & 0xF8 != 0` (init volume ≠ 0 or envelope direction = add). Channel is silenced when DAC is off regardless of trigger.
- **DAC enable — CH3:** controlled by NR30 bit 7 exclusively.
- Timer periods: CH1/CH2 = `(2048-freq)*4`; CH3 = `(2048-freq)*2`.
- Envelope/sweep period 0 treated as 8.
- CH4 noise LFSR: clock shift ≥ 14 → no clocks (silence). 7-bit mode (NR43 bit 3 = 1) → more tonal noise.

---

## CH3 Wave RAM — Safe Access Rules

**DMG hardware only (not an issue on CGB):** Re-triggering CH3 while it is actively reading Wave RAM corrupts the first 4 bytes of Wave RAM.

Safe procedure for re-triggering CH3:
1. Disable DAC: write 0 to NR30 (`NR30_REG = 0`)
2. Write new Wave RAM data (FF30–FF3F)
3. Re-enable DAC: write `0x80` to NR30
4. Trigger: write trigger bit to NR34

When NOT using hUGEDriver for CH3 (after `hUGE_mute_channel(HT_CH3, HT_CH_MUTE)`), follow this sequence to avoid corruption on real DMG hardware.

Note: Wave RAM reads on DMG only work when the channel is actively reading that byte. CGB allows Wave RAM access any time.

---

## Model Differences (DMG vs CGB)

| Behavior | DMG | CGB |
|----------|-----|-----|
| Wave RAM access while CH3 active | Read only works within a couple clocks of wave read | Any time |
| CH3 retrigger without disabling NR30 | Corrupts first 4 bytes of wave RAM | Works normally |
| Length counters at power-off | Preserved, can be written while off | Zero'd at power-on |
| High-pass filter charge factor | 0.999958 | 0.998943 (MGB same as CGB) |

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| `#pragma bank 255` in `music.c` | Remove it — `music.c` must be in bank 0 |
| `add_VBL(hUGE_dosound)` directly | Use a wrapper that calls `SET_BANK` first |
| Calling `hUGE_init` without `__critical` | Wrap in `__critical { ... }` |
| Forgetting APU enable | Call `NR52_REG = 0x80` before `hUGE_init` |
| `BANKED` on `music_init`/`music_tick` | Not needed — they're in bank 0 |
| Passing `hUGEDriver.lib` as positional arg to lcc | Use `-Wl-k$(CURDIR)/lib/hUGEDriver/gbdk -Wl-lhUGEDriver.lib` — positional arg causes bankpack to corrupt the lib |
| Accessing `hUGE_current_wave` to silence CH3 | Use `hUGE_mute_channel(HT_CH3, HT_CH_MUTE)` |
| Calling `music_tick()` inside `vbl_isr()` | Call it in the main loop after `frame_ready = 0` — `SET_BANK` inside an ISR corrupts MBC shadow state when the ISR fires mid-trampoline, causing crashes after several deep BANKED call sequences |
