#ifndef CONFIG_H
#define CONFIG_H

/* Entity capacity constants — all entity pools MUST use SoA (parallel arrays),
 * not AoS (struct arrays). See CLAUDE.md "Entity management" for rationale. */

#define MAX_NPCS     6
/* OAM budget: player=2 (top+bottom half), remaining=38 for enemies/projectiles/HUD */
#define MAX_SPRITES  40

/* Player physics — these will become per-gear values when gears are added */
#define PLAYER_ACCEL      1
#define PLAYER_FRICTION   1
#define PLAYER_MAX_SPEED  6

#define MAP_TILES_W  20u
#define MAP_TILES_H  100u

#define HUD_SCANLINE 128  /* LYC fires here: 2-tile HUD = 16px at bottom, scanline 128 is first HUD line */

/* Terrain physics modifiers */
#define TERRAIN_SAND_FRICTION_MUL  2u   /* friction steps applied on sand (double) */
#define TERRAIN_BOOST_DELTA        2u   /* vy kick per frame on boost pad */

#endif /* CONFIG_H */
