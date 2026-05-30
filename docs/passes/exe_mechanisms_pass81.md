# Pass 81 - player fall counter lifetime and BC0E ordering

## Symptom

Changing horizontal direction during or after a jump could make the player fall
unusually slowly. The jump table itself was correct, but the runtime lifetime
of its counter was not.

## ASM findings

- `SAM1:0x28F35` initializes player vertical counter `DS:34EA = 0x12`.
- `SAM1:0xBC11..0xBC20` calls fall routine `B8B3` whenever normal jump flag
  `DS:6EC1` is clear.
- This fall pass runs while standing as well as while airborne.
- `SAM1:0xB8B6..0xB8C1` increments and caps `DS:34EA` at `0x13`.
- Landing branches such as `SAM1:0xB936..0xB948` clear falling flag `DS:6EC0`
  but do not reset `DS:34EA`.
- `SAM1:0xBCED..0xBD7E` starts and advances an accepted jump after that standing
  fall pass, so its first upward displacement happens in the same player tick.

## Runtime changes

- Player spawn now starts the vertical counter at `0x12`.
- Standing/airborne non-jump ticks always run one `B8B3`-shaped fall pass.
- Landing preserves the vertical counter instead of resetting it to zero.
- Downward table displacement is atomic per DOS tick, matching `B8B3`.
- Jump acceptance happens after the standing fall pass and still performs the
  first upward displacement in the same tick.
- Tk keypress handling now mirrors keyboard ISR `SAM1:0x0079..0x0101`: pressing
  left clears right, pressing right clears left, and the vertical pair behaves
  the same way. Direction changes no longer briefly appear as both directions
  held at once.

## Consequence

Walking off an edge starts with the original capped `8 px/tick` displacement.
Horizontal movement and direction changes no longer accidentally restart a slow
fall ramp.
