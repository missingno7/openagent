# Pass 53 - teleport re-entry gate, one-based sounds, state-0x17 landmine, and D4 frame audit

## Teleport re-entry / ping-pong

Pass 51 implemented the raw `0x77` teleporter dispatcher, but the runtime cleared
its active state and immediately allowed the destination pad to arm again.  In
the EXE the dispatcher branch at `SAM1:0xD4CE..0xD4D5` refuses to arm while
`DS:69E0 != 0`; the main-loop warp path keeps the warp/input state active across
the arrival sequence (`DS:69E0/69E2/69D8`).  Practically, the destination pad is
not re-entered just because the player is still standing on it.

Runtime change: after a warp the destination cell is stored as a release gate.
`check_teleporter_touch()` will not arm another teleport until the player steps
off that destination pad.  This fixes the A<->B teleport loop while preserving
normal paired teleport behaviour.

## Sound ids are one-based

The ASM call sites push sound ids in the range `1..29` before calling the common
PC-speaker routine.  There are no immediate `0` sound ids in the decoded SAM1
call-site scan.  The Python decoder stores SND records in a zero-based list, so
raw sound id `1` must play record index `0`.

Runtime change: `SoundPlayer.play()` now converts `index = sound_id - 1`.  This
fixes shifted sounds such as player jump: the ASM still pushes `0x01` at
`SAM1:0xBCE4..0xBCF7`, but the played SND record is now the first record, not the
second.

## Raw `0xD4` / state `0x2C` frame family

The earlier state-`0x2C` implementation advanced through a 19-tile bank-9 run.
That was too broad: the decoded bank-9 tiles after `8..9` include unrelated
control-room/armory graphics.  For raw `0xD4` / object `0x0135`, the visible
idle decoration is the two-frame bank-9 `8..9` family.

Runtime change: `state2c_tile(0xD4, frame)` now maps to bank 9 tile `8` or `9`
using the EXE-style frame counter cadence instead of cycling through `8..26`.
Raw `0x78` remains a separate bank-15 contact-hazard animation.

## Raw `0x4D` landmine / state `0x17`

Raw `0x4D` writes runtime visual/object `0x0270` in mission maps.  The player
interaction dispatcher branch at `SAM1:0xD0B1..0xD21E` handles `0x0270` as a
landmine:

- it finds a free actor slot (`DS:34EA == 1` scan),
- clears the map cell's `+0x1CA` word,
- creates object `0x0271`,
- sets state `0x17`,
- initializes `DS:34D6 = 1`, `DS:34E2 = 1`, `DS:34D8 = 0x28`, `DS:34DA = 0`.

The state-`0x17` update at `SAM1:0x7782..0x78C1` increments `DS:34D6`; at frame
`0x0B` it calls helper `0x53C4`, the same narrow player-contact hazard helper
used by several other traps.  The non-triggered object-id range renderer draws
`0x0259..0x0270` using `DS:34D6 / 5`, which matches the observed two-frame idle
mine animation.

Runtime change: raw `0x4D` is now a dynamic mission actor in mission levels:

- idle object `0x0270` cycles two frames,
- player overlap arms it into object `0x0271` / state `0x17`,
- the original map cell is removed from the static collision/visual grid,
- frame `0x0B` applies player damage if still overlapping,
- nearby impact sprites approximate the explosion branch.

Note: raw `0x4D` is still kept as an overworld entrance candidate when rendering
or navigating the world map; this pass only changes mission-level simulation.
