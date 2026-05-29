# Pass 35 - foreground is the `+0x1CA` object pass, not the source FG layer

This pass supersedes the simplified pass 34 wording.  `*` rows are one way to
feed the foreground/object redraw path, but they are not the rule that decides
what can appear in front of the player.

## Counterexample: EP1 level 3 raw `0xEB`

Raw code `0xEB` occurs in a normal BG row, but in the original game it can be in
front of the player.  The generated runtime write explains why:

```text
raw 0xEB -> c6=0x0002, c8=0x0000, cA=0x02FC
```

So its draw-relevant object id is in runtime cell word `+0x1CA`, even though the
source row is BG.

## Two redraw routines

The main full-cell redraw routine is the far call `d93:0000`, linear
`0xD930`.  It draws the cell words in this order:

```text
+0x1C6
+0x1C8
+0x1CA
```

The second routine is `d93:2530`, linear `0xFE60`.  It reads only `+0x1CA` and
dispatches the same object-id ranges:

```text
FEAE: read runtime cell +0x1CA
FEB2: skip if zero
FEBA..10598: decode/draw +0x1CA ranges
```

This is the static object/foreground redraw pass.  The setter nonzero-marker
branch also calls this path after writing only `+0x1CA`, which is why `*` rows
were a useful clue but not the whole mechanism.

## Working render rule

For the port, source BG/FG is not the player-occlusion rule:

- normal source rows can still render in front if their EXE-derived write has a
  nonzero `cA`;
- `*` rows render in front because their setter branch writes visual data only
  into `+0x1CA`;
- base static rendering should contain the non-object `c6/c8` portion;
- the player is drawn;
- then the static `+0x1CA` object/overlay pass is composited;
- runtime actor slots are still drawn from the actor loop after that.

Current implementation still uses raw-code draw refs as the visual source, so a
future precision pass should render directly from the generated runtime cell
words instead of classifying whole raw codes.  The important behavioral rule is
now correct: foreground is hardcoded EXE object-layer logic, not the editor
BG/FG split.
