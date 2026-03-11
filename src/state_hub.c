/* state_hub.c — NO #pragma bank 255: in bank 0, safe to call SET_BANK */
#include <gb/gb.h>
#include "state_hub.h"

uint8_t overmap_hub_entered = 0u;
static uint8_t cursor    = 0u;
static uint8_t sub_state = 0u;

static void enter(void)    { overmap_hub_entered = 0u; }
static void update(void)   {}
static void hub_exit(void) {}

const State state_hub = { enter, update, hub_exit };

uint8_t hub_get_cursor(void)    { return cursor; }
uint8_t hub_get_sub_state(void) { return sub_state; }
