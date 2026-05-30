# EXE mechanisms pass 5: corrected runtime-grid axes, D2 one-way cells, and viewport scaling

## 1. Runtime collision buffer is column-major

The previous extractor had the right setter call sites, but the generated
`dx/dy` axes were transposed.  The setter at SAM1 `0x1059e` computes the runtime
cell address by multiplying one coordinate by `0xC8` and the other by `8`.
`0xC8 == 25 * 8`, which matches a padded **Y-cell count**, so this is an
X-column stride, not a screen-row stride.

Correct interpretation:

```text
cell = buffer + ((tile_x + 1) * 0xC8) + ((tile_y + 1) << 3)
```

The old interpretation treated `0xC8` as a row stride.  That made composite
objects look like their one-way cells were on the left column instead of on the
top row.

## 2. 0xD2 now matches the observed 2x2 one-way top

After regenerating `openagent/exe_runtime_collision.py` with the corrected axes,
raw map byte `0xD2` produces:

```text
map byte 0xD2
  dx=-1 dy=-1 body=0 foot=1 c6=0x00BF
  dx=+0 dy=-1 body=0 foot=1 c6=0x00C0
  dx=-1 dy=+0 body=0 foot=0 c6=0x00C3
  dx=+0 dy=+0 body=0 foot=0 c6=0x00C4
```

So the two upper cells of the 2x2 object are one-way/floor-solid, while the two
lower cells are pass-through for the `+0x1CD` floor channel.  This matches the
in-game behavior better than pass 4.

## 3. D3-style platform remains a raw/visual-id distinction

The corrected axis pass does not change the D3 conclusion:

```text
raw 0xD3: body=0 foot=0, visual marker cA=0xFFFF
raw 0xD7: body=0 foot=1, visual id 0x02D3
```

So a visually labelled `D3` platform can still be one-way when the underlying
map byte is `0xD7`.

## 4. Runtime viewport and zoom

`openagent.runtime` now defaults to a logical 320x200 game viewport at 2x zoom.
The window is resizable, and the canvas crop is computed as:

```text
logical_view_width  = canvas_width / zoom
logical_view_height = (canvas_height - HUD) / zoom
```

Controls:

- `+` / `-` changes zoom.
- `Ctrl + mouse wheel` changes zoom.
- Resizing the window changes how much of the level camera sees.

This keeps the pixels nearest-neighbor scaled while making the prototype closer
to the DOS viewport.

## 5. Animation state research status

The current extracted animation model still stands:

- player animation state lives at `DS:3500`;
- jump alternates states `0x0F` and `0x10` during the table-driven jump phase;
- left/right/idle/fire states are written directly by keyboard and collision
  paths rather than by a simple free-running frame counter;
- actor records have a frame/counter at `DS:34D6 + slot*0x20`, sprite id at
  `DS:34E0 + slot*0x20`, and direction at `DS:34E2 + slot*0x20`;
- horizontal walking actors use frame ranges `0x01..0x13` and `0x15..0x27`, and
  side collision negates their direction.

The next missing implementation step is to connect `DS:3500`/actor frame ranges
back to exact sprite-bank/tile choices.  The state-machine addresses are known,
but the renderer lookup from state id to final tile still needs to be traced.
