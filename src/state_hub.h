#ifndef STATE_HUB_H
#define STATE_HUB_H

#include <gb/gb.h>
#include "state_manager.h"

extern const State state_hub;

/* Set to 1 by state_overmap when hub tile is entered.
 * Reset to 0 by state_hub.enter(). Testability hook. */
extern uint8_t overmap_hub_entered;

uint8_t hub_get_cursor(void);
uint8_t hub_get_sub_state(void);

#endif /* STATE_HUB_H */
