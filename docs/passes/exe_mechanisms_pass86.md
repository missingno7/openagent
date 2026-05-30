# Pass 86 — player fall/jump/horizontal speed audit

This pass rechecks the user's video observation of diagonal falling against the
normal mission player movement ASM.  The important finding is that there is no
constant `6 px/tick` horizontal fall speed in the EXE.  The apparent value can
show up visually when watching/interpolating video, but the code uses integer
per-tick displacements.

## Horizontal movement — `SAM1:0x532D`

Routine `0x532D` increments `DS:681E` and writes the per-tick horizontal step to
`DS:6820`.  In the normal `DS:69B0 == 0` player branch the ramp is:

- ticks `1..2`: `1 px/tick`
- tick `3`: `2 px/tick`
- ticks `4..6`: `4 px/tick`
- ticks `7..1000`: `DS:69A4 + 4`

The previous OpenAgent interpretation treated `DS:69A4` as if it were normally
`4`, which made the ordinary terminal run speed `8 px/tick`.  The init path at
`SAM1:0x28D0C..0x28D11` actually clears both `DS:69A4` and `DS:69A6`, so normal
terminal speed is `4 px/tick`.

Raw pickup `0x4E` / runtime visual `0x0139` is the speed bonus branch at
`SAM1:0xD659..0xD65F`: it writes `DS:69A4 = 4` and `DS:69A6 = 0x00D8`.  The
timer ISR decrements `DS:69A6` once per `0x14` timer ticks and clears `DS:69A4`
when it reaches zero.  Therefore the boosted terminal speed is `8 px/tick` only
while the speed icon/timer is active.

## Why a diagonal fall may look like about 6 px/tick

The fall table can produce `8 px/tick` vertically once `DS:34EA` reaches its
terminal tail.  If the left/right key was already held before leaving the ledge,
`DS:681E` is already warm, so the horizontal branch immediately uses terminal
speed: normally `4 px/tick`, or `8 px/tick` with the speed bonus.

A fresh six-tick press during a fall moves `1 + 1 + 2 + 4 + 4 + 4 = 16 px`
horizontally.  A warmed normal run moves `6 * 4 = 24 px`.  A warmed speed-bonus
run moves `6 * 8 = 48 px`.  Combined with 16-pixel snapping/collision probes and
video-frame sampling, this can look like a rough `6 px/tick`, but the ASM itself
only writes the integer steps above.

## Vertical fall and jump — `SAM1:0xB8B3`, `SAM1:0xBC0E..0xBD8A`

The vertical side was already close to the ASM-backed behaviour added in passes
80-84:

- falling increments `DS:34EA`, caps it at `0x13`, reads byte table
  `DS:34AF + DS:34EA`, and adds that value to player Y;
- the fall table is `[0, 8, 8, 8, 4, 4, 2, 2, 2, 1, 1, 2, 2, 2, 4, 4, 8, 8, 8, 8]`;
- landing uses bottom probes at `y + 16` and snaps Y to a 16-pixel boundary;
- jump uses the same table, subtracts the value from Y, clears `DS:6EC1` at
  counter `0x0A`, and rewinds `DS:34EA` to `9` for the next fall pass.

No floating-point gravity is involved in the EXE path; all normal mission player
movement here is integer per fixed DOS tick.

## Runtime changes

- Normal horizontal terminal speed is now `4 px/tick`, not permanently `8`.
- Raw `0x4E` now starts the `DS:69A4=4` speed bonus timer and makes ticks `7+`
  use `8 px/tick` while active.
- The status bar now draws the speed icon while the speed bonus is active.
- Horizontal-block acceleration reset now mirrors the `DS:681C > 1` gate instead
  of clearing `DS:681E` for every blocked probe.
