#include <stdint.h>

uint8_t mock_move_sprite_last_nb    = 0;
uint8_t mock_move_sprite_last_x     = 0;
uint8_t mock_move_sprite_last_y     = 0;
int     mock_move_sprite_call_count = 0;

void mock_move_sprite_reset(void) {
    mock_move_sprite_last_nb    = 0;
    mock_move_sprite_last_x     = 0;
    mock_move_sprite_last_y     = 0;
    mock_move_sprite_call_count = 0;
}

void move_sprite(uint8_t nb, uint8_t x, uint8_t y) {
    mock_move_sprite_last_nb = nb;
    mock_move_sprite_last_x  = x;
    mock_move_sprite_last_y  = y;
    mock_move_sprite_call_count++;
}
