# Pass 34 - static foreground tiles over the player

This pass corrected the pass 33 shortcut that treated every static map cell as
being below the player.  Pass 35 further corrects this: `*` rows are not the
whole foreground rule.  The broader rule is the EXE `+0x1CA` object redraw pass,
which can also be fed by normal BG rows such as raw `0xEB`.

## Related Crystal Caves evidence

OpenCrystalCaves exposes the same engine-family idea explicitly:

```text
occ/game/export/tile.h: TILE_RENDER_IN_FRONT = 0x20
occ/occ/src/game_renderer.cc:
  render_background()
  render_tiles(false)
  render_objects(false)
  render_enemies(...)
  render_player()
  render_tiles(true)
  render_objects(true)
```

So this engine style supports tiles that are rendered after the player without
making the whole foreground/background source layer a collision layer.

## Secret Agent setter branch

The main Secret Agent map-token setter starts around `SAM1:0x1059E` and tests
the marker argument:

```text
105A1: cmpb $0x0,0x6(%bp)
```

When the marker is zero, the setter writes the full runtime cell state:

```text
10622: write +0x1C6
10641: write +0x1C8
10660: write +0x1CA
10678: write collision byte +0x1CC
10695: write collision byte +0x1CD
```

When the marker is nonzero, it takes the overlay-only branch:

```text
105C2: write +0x1CA
105CA..105F0: redraw through the overlay path
```

The parsed `SAM?03.GFX` `*` rows are one source-level trigger for this
nonzero-marker branch.  They write visual overlay data only.  They do not write
collision bytes, which matches the earlier collision finding, but they are not
just editor decoration.

## Working render rule

For mission levels:

- normal rows/full cell writes produce runtime words; words in `+0x1CA` belong
  to the object/foreground redraw path even when the source row is BG;
- the player is drawn after that base view;
- `*` rows/nonzero-marker writes are also composited after the player as static
  foreground because they write visual data into `+0x1CA`;
- runtime actor slots still draw from the actor loop after the player.

This means `+0x1CA` by itself is not a player-occlusion flag.  The important
distinction is which setter branch produced the word:

- zero marker: full static cell, under player;
- nonzero marker: overlay-only foreground, over player.

The exact ordering between static foreground overlays and every runtime actor
subtype still needs more EXE/screenshot confirmation.  The current port keeps
actor slots after the foreground overlay because pass 33 confirmed the actor
loop starts after the player, and this avoids moving runtime actors back into
the static background class.
