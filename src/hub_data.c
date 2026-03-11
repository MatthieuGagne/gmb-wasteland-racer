/* hub_data.c — NO #pragma bank 255: bank 0 data, always accessible */
#include <gb/gb.h>
#include "hub_data.h"

static const char hub_name[]    = "RUST TOWN";
static const char npc_name_0[]  = "Mechanic";
static const char npc_name_1[]  = "Trader";
static const char npc_name_2[]  = "Drifter";

const HubDef rust_town = {
    hub_name,
    3u,
    { npc_name_0, npc_name_1, npc_name_2 },
    { 0u, 1u, 2u }
};
