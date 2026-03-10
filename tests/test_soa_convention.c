#include "unity.h"
#include "../src/config.h"

void setUp(void) {}
void tearDown(void) {}

void test_max_npcs_sane(void) {
    TEST_ASSERT_GREATER_THAN(0, MAX_NPCS);
}

void test_max_sprites_sane(void) {
    TEST_ASSERT_GREATER_THAN(0, MAX_SPRITES);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_max_npcs_sane);
    RUN_TEST(test_max_sprites_sane);
    return UNITY_END();
}
