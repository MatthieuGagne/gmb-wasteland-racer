#include "unity.h"
#include "player.h"

void setUp(void)    { player_init(); }
void tearDown(void) {}

/* clamp_u8 ---------------------------------------------------------- */

void test_clamp_u8_returns_lo_when_below(void) {
    TEST_ASSERT_EQUAL_UINT8(8, clamp_u8(5, 8, 152));
}

void test_clamp_u8_returns_hi_when_above(void) {
    TEST_ASSERT_EQUAL_UINT8(152, clamp_u8(200, 8, 152));
}

void test_clamp_u8_returns_value_when_within(void) {
    TEST_ASSERT_EQUAL_UINT8(80, clamp_u8(80, 8, 152));
}

/* player_init ------------------------------------------------------- */

void test_player_init_sets_center_position(void) {
    TEST_ASSERT_EQUAL_UINT8(80, player_get_x());
    TEST_ASSERT_EQUAL_UINT8(72, player_get_y());
}

/* player_update movement -------------------------------------------- */

void test_player_update_moves_left(void) {
    player_update(J_LEFT);
    TEST_ASSERT_EQUAL_UINT8(79, player_get_x());
}

void test_player_update_moves_right(void) {
    player_update(J_RIGHT);
    TEST_ASSERT_EQUAL_UINT8(81, player_get_x());
}

void test_player_update_moves_up(void) {
    player_update(J_UP);
    TEST_ASSERT_EQUAL_UINT8(71, player_get_y());
}

void test_player_update_moves_down(void) {
    player_update(J_DOWN);
    TEST_ASSERT_EQUAL_UINT8(73, player_get_y());
}

/* player_update clamping -------------------------------------------- */

void test_player_update_clamps_at_left_boundary(void) {
    player_set_pos(8, 72);
    player_update(J_LEFT);
    TEST_ASSERT_EQUAL_UINT8(8, player_get_x());
}

void test_player_update_clamps_at_right_boundary(void) {
    player_set_pos(167, 72);
    player_update(J_RIGHT);
    TEST_ASSERT_EQUAL_UINT8(167, player_get_x());
}

void test_player_update_clamps_at_top_boundary(void) {
    player_set_pos(80, 16);
    player_update(J_UP);
    TEST_ASSERT_EQUAL_UINT8(16, player_get_y());
}

void test_player_update_clamps_at_bottom_boundary(void) {
    player_set_pos(80, 159);
    player_update(J_DOWN);
    TEST_ASSERT_EQUAL_UINT8(159, player_get_y());
}

/* runner ------------------------------------------------------------ */

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_clamp_u8_returns_lo_when_below);
    RUN_TEST(test_clamp_u8_returns_hi_when_above);
    RUN_TEST(test_clamp_u8_returns_value_when_within);
    RUN_TEST(test_player_init_sets_center_position);
    RUN_TEST(test_player_update_moves_left);
    RUN_TEST(test_player_update_moves_right);
    RUN_TEST(test_player_update_moves_up);
    RUN_TEST(test_player_update_moves_down);
    RUN_TEST(test_player_update_clamps_at_left_boundary);
    RUN_TEST(test_player_update_clamps_at_right_boundary);
    RUN_TEST(test_player_update_clamps_at_top_boundary);
    RUN_TEST(test_player_update_clamps_at_bottom_boundary);
    return UNITY_END();
}
