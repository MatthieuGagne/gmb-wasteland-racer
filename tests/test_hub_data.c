#include "unity.h"
#include "hub_data.h"

void setUp(void)    {}
void tearDown(void) {}

void test_rust_town_name(void) {
    TEST_ASSERT_EQUAL_STRING("RUST TOWN", rust_town.name);
}
void test_rust_town_num_npcs(void) {
    TEST_ASSERT_EQUAL_UINT8(3u, rust_town.num_npcs);
}
void test_rust_town_npc_names(void) {
    TEST_ASSERT_EQUAL_STRING("Mechanic", rust_town.npc_names[0]);
    TEST_ASSERT_EQUAL_STRING("Trader",   rust_town.npc_names[1]);
    TEST_ASSERT_EQUAL_STRING("Drifter",  rust_town.npc_names[2]);
}
void test_rust_town_dialog_ids(void) {
    TEST_ASSERT_EQUAL_UINT8(0u, rust_town.npc_dialog_ids[0]);
    TEST_ASSERT_EQUAL_UINT8(1u, rust_town.npc_dialog_ids[1]);
    TEST_ASSERT_EQUAL_UINT8(2u, rust_town.npc_dialog_ids[2]);
}

void test_hub_table_count(void) {
    TEST_ASSERT_EQUAL_UINT8(1u, hub_table_count);
}
void test_hub_table_index_zero_is_rust_town(void) {
    TEST_ASSERT_EQUAL_PTR(&rust_town, hub_table[0]);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_rust_town_name);
    RUN_TEST(test_rust_town_num_npcs);
    RUN_TEST(test_rust_town_npc_names);
    RUN_TEST(test_rust_town_dialog_ids);
    RUN_TEST(test_hub_table_count);
    RUN_TEST(test_hub_table_index_zero_is_rust_town);
    return UNITY_END();
}
