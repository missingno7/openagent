# Pass 66: Dynamite and exit-door interaction

This pass focuses on the mission-end door path around the runtime interaction dispatcher.

## Dynamite pickup

Raw map code `0x74` writes runtime visual/object `0x027B`.

The dispatcher branch at `SAM1:0xCB72..0xCBE5` does the following when the player touches it:

- sets `DS:69F4 = 1` — the player is carrying dynamite;
- clears the runtime cell `+0x1CA`;
- plays sound `0x05`;
- calls the score popup helper with argument `0x13`, i.e. the 500-point popup;
- adds `0x01F4` points to the score.

Runtime now models this with `has_dynamite`, clears the source cell, awards 500 points, and draws the 500 popup.

## Exit door

Raw map code `0x71` writes a two-cell exit door footprint:

- upper cell visual `0x0279`, solid;
- lower/touch cell visual `0x027D`, solid.

The interaction branch at `SAM1:0xCBF0..0xCD71` checks `DS:69F4`:

- if dynamite is present, it clears `DS:69F4`, plays sound `0x0B`, and allocates object `0x027B` with state `0x16`;
- that spawned actor has `DS:34D8 = 0x28`, so the door should remain blocked during the blast sequence;
- after the blast, the door can enter the opened/exit path, represented by the later `0x027E` compare at `SAM1:0xCDF4`.

Runtime now keeps a `0x28`-tick blast timer per raw `0x71` source cell. The door stays solid during the timer, then the raw source is added to `opened_doors`, which removes both its render and collision footprint. Touching the opened exit returns to the overworld until the full original end-of-mission bonus/menu flow is reconstructed.

## Remaining uncertainty

The large transition path after `0x027E` includes more global flags (`DS:69CE`, `DS:6D66`, `DS:6A3E`, etc.) and text/menu drawing. The current implementation only models the core playable sequence: pick up dynamite, place it on the exit door, wait for the blast, then leave the level.
