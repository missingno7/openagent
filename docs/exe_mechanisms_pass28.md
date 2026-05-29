# Pass 28 - projectile impact, active viewport and enemy durability

## Projectile helper `CS:5784`

The shared projectile creator at `SAM1 CS:5784` is used by the player, bank-14
shooters and several stationary traps.  When called with `object_id = 0`, it
creates the normal bullet actor:

- `DS:34E0 = 0x0027`
- `DS:34E8 = 0x0007`
- `DS:34D6 = 1`
- `DS:34E6 = caller speed`

Player and bank-14 guard calls pass speed `4`, so runtime bullets are now moved
as actor ticks by exactly `4 px / DOS tick` rather than by a continuous Tk-frame
`dt` approximation.

## Bullet impact / boom animation

The collision/display path around `SAM1 CS:4EDD..4F3A` treats states `0x07`,
`0x0E`, `0x13` and `0x1388` as projectile-like impact-capable actors.  The enemy
hit branch around `SAM1 CS:5C59..5C82` rewrites a shot actor to:

- `DS:34E8 = 0x1388`
- `DS:34E0 = 0x0187`
- `DS:34D6 = 1`
- `DS:34E6 = 0`

Runtime now spawns an `Explosion` entity instead of silently deleting the shot.
`0x0187` is represented by the decoded bank-6 impact family, currently rendered
as bank 6 tiles `44, 47, 45, 46`.

## Fixed active viewport

The original game logic is tied to a 320x200 view.  Scroll variable `DS:6838` is
clamped to `0..0x140`, and actor/projectile code compares player position against
scroll-relative constants such as `+0x96` and `+0xAA`.  This means enlarging the
OpenAgent window must not make off-screen traps start running earlier.

Runtime now has two view concepts:

- render viewport: whatever the resized window shows;
- active gameplay viewport: fixed 320x200 around the player, matching the DOS
  game viewport.

Stationary shooter/trap actors only count their firing timer when inside this
fixed active viewport.

## Enemy durability

Some enemies are not one-shot.  The special actor table has an extra `aux_dc`
field with value `3` for several larger/multi-tile actors, including the bank-0
two-tile dog `0xAE`.  Until the per-state hit routines are fully decoded, runtime
uses this as a hitpoint hint:

- `0xAE` dog: 3 hits
- `0x56`, `0x58`, `0x63`, `0x65`, `0x6E`: 3 hits where the same EXE table hint is present

Bank-14 guards still use their separate degrade chain rather than generic HP.
