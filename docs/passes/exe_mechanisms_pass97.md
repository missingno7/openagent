# Pass 97 — object-0x72 laser overlap uses player-origin rectangle

Follow-up to passes 95 and 96.  The previous split between object-`0x72/state 0x25`
and `0x72/state 0x89` was correct, but the Python hit test still reused the
full decoded player sprite rectangle for both narrow laser states.

## ASM evidence

The direct hard-death branch for object-`0x72/state 0x25` is at
`SAM1:0xA456..0xA70C`.

The player-overlap portion at `SAM1:0xA660..0xA6F0` compares the projectile
origin against the player origin fields:

- X uses `DS:34EE` and `DS:34EE + 9`.
- Y uses `DS:34F0` and `DS:34F0 + 15`.
- The projectile side is also treated as a 10x16 rectangle, matching the
  object-`0x72` narrow laser footprint recovered in pass 96.

That means the comparison is not against the full decoded player sprite size.
A beam touching only the player's right/bottom visual edge should not trigger
until it overlaps the player-origin 10x16 gameplay rectangle.

`0x72/state 0x89` still routes through the generic helper `0x53C4`; pass 94
already documented that helper as the same 10x16-vs-10x16 origin-rectangle
family.  So both object-`0x72` laser policies should use the same player-origin
rectangle, while preserving their different damage outcomes:

- state `0x89`: generic hurt / invulnerability path,
- state `0x25`: direct hard-death path.

## Runtime changes

- Added `projectile_hits_player_origin_rect()` in `openagent/combat.py`.
- `hostile_projectile_hits_player()` now uses this origin-rectangle helper for
  `hard_death_on_hit` and `narrow_hurt_on_hit` projectiles.
- Generic projectile/temporary hazard rectangles still use the full sprite-footprint
  helper, so lightning and ordinary bullet behavior is not changed by this pass.
- `narrow_hurt_on_hit` now explicitly respects `hurt_flash` before calling the
  generic hurt helper, matching the surrounding helper-style damage gating used
  elsewhere.

## Known remaining gaps

- Object-`0x72` foreground redraw / solid-impact side effects around
  `SAM1:0xA4CB..0xA604` are still only approximated as an invisible short impact
  slot.
- The complete projectile object/state table is still not finished.
