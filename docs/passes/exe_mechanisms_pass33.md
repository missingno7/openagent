# Pass 33 - draw order around player and runtime cell layers

This pass answers a rendering mismatch: OpenAgent was drawing runtime entities
before the player, which put the player visually above moving platforms,
enemies, projectiles and score popups.  The original EXE does the opposite for
actor slots.

## Main frame order

In `SAM1_unpacked_linear_8086.asm`, the mission frame path first draws or
refreshes the level view, then draws the player:

```text
20CE..21E4: player animation frame selection and draw call
21E4..2254: optional player-related overlay/effect draw
227E:       DS:6826 = 2
2286..:     increment DS:6826 and iterate runtime actor slots
22EF..2F55: actor/object render dispatch
```

So runtime actors are drawn after the player.  This includes moving enemies,
moving platforms when represented as actor objects, projectiles, traps that use
actor slots, impact animations and floating score objects.  Drawing all entities
before the player was a port-side ordering bug.

## Static map cell order

The cell redraw routine around `SAM1:0xD955..0xEAAF` reads the reconstructed
runtime cell words in this order:

```text
+0x1C6
+0x1C8
+0x1CA
```

Each non-zero word is decoded through the same broad object-id ranges and drawn
before the routine returns.  This is layer order inside a static runtime cell,
not a complete front-vs-behind-player flag.  Pass 35 corrects the important
exception: the separate `d93:2530` redraw routine draws `+0x1CA` as the static
object/foreground pass, including normal BG-row codes such as raw `0xEB`.

Current working rule:

- normal/full static `+0x1C6` and `+0x1C8` portions: draw before player;
- static `+0x1CA` object/overlay portions: draw after player as foreground;
- player: draw after static map pass;
- actor slots from index 2 upward: draw after player.

## Runtime change

`openagent/runtime.py` now draws the mission base bitmap, then the player, then
the `*` row foreground overlay, then `draw_entities()`.  This better matches the
EXE actor-slot order and stops the port from treating dynamic entities as
background scenery.

## Still open

The static renderer still uses the editor's `TILE_MAP` draw refs directly.  It
does not yet render from the generated runtime-cell words `c6/c8/cA`.  That is a
separate precision step: build a visual runtime-cell grid from
`openagent/exe_runtime_collision.py` and render the three cell words in EXE
order instead of relying on the current raw-code draw helper.
