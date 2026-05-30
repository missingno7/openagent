# Pass 82 - atomic normal horizontal player probe

## ASM finding

`SAM1:0xBAF5..0xBB97` asks `SAM1:0xB7D9..0xB8A4` whether the requested
horizontal destination is clear before changing player X. The requested
`DS:6820` step is probed as one unit; it is not applied one pixel at a time.

## Runtime change

Normal mission map movement now uses one atomic destination probe per DOS tick.
When that destination is blocked, the whole horizontal step is rejected and the
held-movement ramp counter is reset like `DS:681E`.

Raw `0xA7` pushable barrels remain an explicit exception. They have their own
actor overlap behavior around states `0x1388/0x1389`, so the existing
pixel-granular reconstruction is retained only when the atomic destination
overlaps a barrel.
