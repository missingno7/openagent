# Pass 87 — make mine/water animation visibly use the ASM render branches

This pass fixes a render integration regression from pass 85.  The tick counters
were advancing, but the animated cels were not actually winning the draw path.

## Raw `0x4D` landmine

ASM evidence remains the same:

- draw branch `SAM1:0x36C2..0x3725` handles object `0x0270` and uses
  `floor(DS:34D6 / 5)`;
- state branch `SAM1:0x7782..0x78C1` increments `DS:34D6` and wraps non-triggered
  mines after `DS:34D6 > 9`;
- triggered object `0x0271` uses the neighbouring draw branch
  `SAM1:0x3728..0x378E` with `floor(DS:34D6 / 3)`.

The bug was in `draw_entities()`: `state17_landmine_tile()` existed, and the
state-0x17 tick code was updating `frame_counter`, but rendering fell through to
`draw_code_sprite(0x4D)`, so the static raw map marker was drawn instead of the
object-id frame.  The renderer now dispatches `enemy.kind == "state17_landmine"`
through `state17_landmine_tile()`.

Idle visible sequence:

```text
object 0x0270: bank 5 tile 23 -> bank 5 tile 41, driven by DS:34D6 / 5
```

## Raw `0x60` water / runtime visual `0x01F3`

The EXE renderer special-cases `0x01F3` in the draw paths already noted in pass
20/pass 23, comparing the runtime visual id and choosing between the two paired
bank-4 bitmaps.  The exact original phase source is still the `DS:6840` draw-page
state, so the runtime keeps the conservative fixed-DOS-tick phase rather than
using Tk redraw FPS.

The bug was that raw `0x60` remained baked into the cached static foreground
image.  `draw_fast_animated_tiles()` was drawing the live phase, but the cached
foreground layer could cover it again.  Raw `0x60` is now skipped from the cached
static layers and is drawn only by the live water overlay.

Visible sequence used by the runtime:

```text
runtime visual 0x01F3: bank 4 tile 48 <-> bank 4 tile 0, fixed DOS tick phase
```

This keeps both animations render-only: collision and gameplay still read the
original fixed tick/game state, not the interpolated/rendered frame.
