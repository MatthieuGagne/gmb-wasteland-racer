#include "dialog.h"

void    dialog_init(void)                              { }
void    dialog_start(uint8_t npc_id,
                     const NpcDialog *dialog)          { (void)npc_id; (void)dialog; }
const char *dialog_get_text(void)                      { return ""; }
uint8_t dialog_get_num_choices(void)                   { return 0; }
const char *dialog_get_choice(uint8_t idx)             { (void)idx; return ""; }
uint8_t dialog_advance(uint8_t choice_idx)             { (void)choice_idx; return 0; }
void    dialog_set_flag(uint8_t npc_id,
                        uint8_t flag_bit)              { (void)npc_id; (void)flag_bit; }
uint8_t dialog_get_flag(uint8_t npc_id, uint8_t flag_bit) {
    (void)npc_id; (void)flag_bit; return 0;
}
