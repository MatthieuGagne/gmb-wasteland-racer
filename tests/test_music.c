#include "unity.h"
#include "music.h"

void setUp(void)    { frame_ready = 0; }
void tearDown(void) {}

/* vbl_display_off() should consume the frame_ready flag (set it to 0).
 * We pre-set frame_ready = 1 so the spin loop exits immediately. */
void test_vbl_display_off_consumes_frame_ready(void) {
    frame_ready = 1;
    vbl_display_off();
    TEST_ASSERT_EQUAL_UINT8(0u, frame_ready);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_vbl_display_off_consumes_frame_ready);
    return UNITY_END();
}
