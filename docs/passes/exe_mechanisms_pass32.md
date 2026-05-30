# Pass 32 — shark direction and pushable barrel anti-stick behaviour

## Shark / raw 0x5F / bank 4

The previous runtime treated the bank-4 shark as a generic four-frame loop and mirrored it when travelling left.  That is not how the decoded game data is laid out.  The bank itself already contains the facing direction:

- bank 4 tiles `46,47` = shark swimming right
- bank 4 tiles `44,45` = shark swimming left

The runtime now maps raw `0x5F` to those two directional two-frame loops and does not mirror the left-facing shark.

## Pushable barrel / raw 0xA7 / bank 6 tile 24

The barrel is not just a normal solid tile.  In the actor dispatcher the EXE has a dedicated branch involving object id `0x00A7` and the transient states `0x1388/0x1389`:

- `SAM1:0x834f` writes `DS:34E0 = 0x00A7`.
- `SAM1:0x8335` / `0x84b3` write `DS:34E8 = 0x1389`.
- `SAM1:0x83c4..0x848a` compares the player's shrunken X range (`player_x+3 .. player_x+12`) and Y range against the actor instead of treating the cell as a permanently blocking wall.

This explains the in-game behaviour where pushing the barrel into a wall does not trap the player.  The object is allowed to overlap the player briefly, turns/nudges away from the wall, and the overlap resolves instead of becoming a hard collision deadlock.

Runtime changes:

- When a barrel push succeeds, it still moves by the player step.
- When that horizontal move leaves it without floor support, it continues as a
  dynamic actor and falls; it is not pinned to the old map row.
- When a barrel push fails because it is against a wall/solid cell, it is turned away and nudged back if possible.
- The player's collision with that same barrel is temporarily ignored until the overlap clears, instead of being re-enabled after a single pixel.  This fixes the previous “barrel sticks to player” feel.

This is still a Python-level reconstruction, but the important structural point now matches the EXE: raw `0xA7` has special actor overlap handling and should not behave as a simple solid tile.
