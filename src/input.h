#ifndef INPUT_H
#define INPUT_H

#include <gb/gb.h>
#include <stdint.h>

/* Globals are DEFINED in main.c; all other TUs get extern declarations. */
extern uint8_t input;
extern uint8_t prev_input;

/* Called once per frame in main.c before state_manager_update().
 * static inline: no linker unit; SDCC may not always inline but
 * the function is tiny (2 assignments) so code size impact is negligible. */
static inline void input_update(void) {
    prev_input = input;
    input = joypad();
}

#define KEY_PRESSED(k)   ((input)      & (k))
#define KEY_TICKED(k)    (((input) & (k)) && !((prev_input) & (k)))
#define KEY_RELEASED(k)  (!((input) & (k)) && ((prev_input) & (k)))
#define KEY_DEBOUNCE(k)  (((input) & (k)) && ((prev_input) & (k)))

#endif /* INPUT_H */
