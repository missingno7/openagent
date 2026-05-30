# EXE Mechanisms Pass 69 - Raw 0x6E Lightning Flyer Timer Correction

## Scope

This pass revisits raw mission code `0x6E`, object `0x0085`, behaviour state
`0x26`, because the runtime still had a first-pass approximation of its
lightning cadence.

## ASM evidence

The relevant dispatcher branch is `SAM1:0xA70F..0xA894`.

Important fields:

- `DS:34DE` is the hold/pause timer.
  - While it is non-zero, the branch decrements it and then writes the old X
    coordinate back to `DS:34CE`; the actor animates, but does not really move.
- `DS:34DA` is the active lightning timer.
  - When `DS:34DE == 0` and `DS:34DA == 0`, the branch immediately calls
    helper `0x5784` with object `0x0089` at `(actor_x, actor_y + 16)`.
  - Then it increments `DS:34DA`.
  - When `DS:34DA == DS:34D8`, it resets `DS:34DA = 0` and sets
    `DS:34DE = 0x6E`.
- Object `0x0089` is the stationary lightning bolt actor below the flyer.  The
  helper maps it to the short-lived state `0x28` and the visible bank-2
  lightning tiles `36..39`.

## Runtime correction

The previous runtime waited the full random interval after each pause before
spawning the lightning, then immediately entered the next pause.  That inverted
the EXE cadence.

Runtime now mirrors the EXE timer order:

1. long initial/pause `alert_ticks` / `DS:34DE`, no movement;
2. first active tick with timer zero spawns lightning immediately;
3. active timer counts up to the randomized period `DS:34D8`;
4. timer resets to zero and reloads the `0x6E` pause.

This should make the flyer feel closer to the original: the bolt appears right
as the actor wakes up from its hold phase rather than only after another full
charge cycle.
