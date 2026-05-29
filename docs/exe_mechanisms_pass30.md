# Pass 30 — bank12 ceiling laser actor and pushable barrel notes

## Bank 12 tiles 36..43 / raw `0x63`

The special actor table entry for raw `0x63` initializes an actor slot with:

- `DS:34E0 = 0x0345`
- `DS:34E8 = 0x21`
- `DS:34E6 = 2`
- `DS:34D8 = random(20) + 30`
- `DS:34DA = 0`
- `DS:34DC = 3`

This matches the ceiling-mounted bank-12 enemy. The visible atlas family is bank 12 tiles `36..43`: two 4-frame directional loops. The runtime now treats raw `0x63` as a ceiling crawler/laser shooter instead of a generic ground walker:

- moves horizontally at 2 px per DOS actor tick,
- checks support above/ahead rather than floor below,
- fires a downward projectile when the player is in the same tile column below it and its timer expires,
- uses the existing multi-hit shootable object id `0x0345` / hp hint `3`.

The exact projectile object-id to decoded tile lookup for the downward laser is still a target for a later fully automated object-id renderer. The current implementation uses the bank-12 laser family and vertical projectile movement; the actor/timer/movement behaviour is wired from the EXE fields above.

## Pushable barrel / raw `0xA7`

Existing mapping/research identifies raw `0xA7` as bank 6 tile 24. It is now extracted as a dynamic `PushableBarrel` instead of a static map tile.

Implemented runtime behaviour:

- player can stand on it as a floor support,
- player can push it horizontally one DOS pixel at a time,
- when the barrel reaches a wall/end and cannot be pushed further, it turns around and does not trap the player in a solid collision,
- it is drawn dynamically at its current position.

The remaining reverse-engineering task is to isolate the exact EXE branch for `0xA7` to confirm whether it uses a dedicated actor state or runtime-cell mutation path. This pass implements the user-observed behaviour while keeping the raw code dynamic so it can later be replaced by the exact actor-state code.

## Related cleanup

- `0x63` is no longer treated as a two-wide bank12 actor; its bank12 `36..43` tile family is used through normal walker-frame selection.
- Projectiles now support vertical movement (`dx_px`, `dy_px`), needed by downward laser enemies.
