# Pass 67: exit door open-state correction

User testing showed that the post-dynamite exit door should not vanish.  The
ASM confirms this.

## ASM evidence

The raw `0x71` exit door is initially written as two runtime cells:

- upper visual `0x0279` at `SAM1:0x15C9C` / collision table row for raw `0x71`;
- lower/touch visual `0x027D` at `SAM1:0x15CCE` / collision table row for raw `0x71`.

Touching `0x027D` while `DS:69F4 == 1` consumes the dynamite and creates an actor
slot with:

- object `0x027B`;
- state `0x16`;
- period `DS:34D8 = 0x28`.

The relevant branch is `SAM1:0xCBF0..0xCD71`.

When state `0x16` reaches its period, the actor update branch does **not** clear
the exit door.  It scans the runtime grid for cells whose `+0x1CA` visual is
`0x027D`, then rewrites that visual to `0x027E` and clears `+0x1CC`:

```text
SAM1:0x7490  cmpw $0x27d,0x1ca(%di)
SAM1:0x74B0  movw $0x27e,0x1ca(%di)
SAM1:0x74CB  movb $0x0,0x1cc(%di)
```

So the lower half becomes the broken/passable exit visual.  The upper `0x0279`
part remains visually present.

## Runtime change

The previous pass added the raw source to `opened_doors`, which removed the whole
two-tile door from render and collision.  This pass separates exit doors into
`opened_exit_doors`:

- raw `0x71` is skipped from the normal static renderer only so the closed lower
  half does not remain baked in;
- the renderer overlays the real bank-5 art for the opened state:
  - upper: bank 5 tile `32` (`0x0279` closed/top arrow tile);
  - lower: bank 5 tile `37` (`0x027E` broken/open lower tile);
- the lower tile is passable and triggers level completion;
- the upper tile stays body/floor solid as the original still has the `0x0279`
  cell.

This matches the observed game behaviour: after the blast the door remains on
screen as a broken/passable exit instead of disappearing.
