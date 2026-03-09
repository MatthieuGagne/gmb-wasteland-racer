#include "unity.h"
#include "track.h"

void setUp(void)    {}
void tearDown(void) {}

/* On-track: bottom straight, tile (20,32) = world (160,256) */
void test_track_passable_bottom_straight(void) {
    TEST_ASSERT_EQUAL_UINT8(1, track_passable(160, 256));
}

/* On-track: top straight, tile (20,2) = world (160,16) */
void test_track_passable_top_straight(void) {
    TEST_ASSERT_EQUAL_UINT8(1, track_passable(160, 16));
}

/* On-track: left side, tile (4,15) = world (32,120) */
void test_track_passable_left_side(void) {
    TEST_ASSERT_EQUAL_UINT8(1, track_passable(32, 120));
}

/* On-track: right side, tile (34,15) = world (272,120) */
void test_track_passable_right_side(void) {
    TEST_ASSERT_EQUAL_UINT8(1, track_passable(272, 120));
}

/* Off-track: outer corner, tile (0,0) = world (0,0) */
void test_track_passable_outer_corner(void) {
    TEST_ASSERT_EQUAL_UINT8(0, track_passable(0, 0));
}

/* Off-track: inner void, tile (20,18) = world (160,144) - D-row center */
void test_track_passable_inner_void(void) {
    TEST_ASSERT_EQUAL_UINT8(0, track_passable(160, 144));
}

/* Off-track: beyond map width */
void test_track_passable_out_of_bounds_x(void) {
    TEST_ASSERT_EQUAL_UINT8(0, track_passable(320, 120));
}

/* Off-track: beyond map height */
void test_track_passable_out_of_bounds_y(void) {
    TEST_ASSERT_EQUAL_UINT8(0, track_passable(160, 288));
}

/* Off-track: negative world coords */
void test_track_passable_negative_coords(void) {
    TEST_ASSERT_EQUAL_UINT8(0, track_passable(-1, 120));
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_track_passable_bottom_straight);
    RUN_TEST(test_track_passable_top_straight);
    RUN_TEST(test_track_passable_left_side);
    RUN_TEST(test_track_passable_right_side);
    RUN_TEST(test_track_passable_outer_corner);
    RUN_TEST(test_track_passable_inner_void);
    RUN_TEST(test_track_passable_out_of_bounds_x);
    RUN_TEST(test_track_passable_out_of_bounds_y);
    RUN_TEST(test_track_passable_negative_coords);
    return UNITY_END();
}
