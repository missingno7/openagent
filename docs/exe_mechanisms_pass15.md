# Pass 15: bank-14 guard sight and back-shot behaviour

This pass tightens the bank-14 guard logic from EXE control-flow clues instead
of letting shooter guards fire on a blind periodic timer.

## EXE evidence

The SAM1 disassembly has a repeated actor branch that gates projectile creation
by the player position and the actor direction.  One representative block is
around `SAM1:0x63CD..0x6455`:

- it compares the actor Y tile (`DS:34D0 + slot*0x20` shifted by four) with the
  player Y tile;
- if the rows differ, it skips the shot path;
- it compares actor X (`DS:34CE + slot*0x20`) with player X (`DS:34EE`);
- if the player is to the actor's right, `DS:34E2` must be `+1`;
- if the player is to the actor's left, `DS:34E2` must be `-1`;
- only then it clears the actor timer `DS:34DA` and calls helper `0x5784` with
  the actor position and direction.

This matches the in-game observation that the armed bank-14 enemies shoot only
when they are facing the player on the same horizontal line, not constantly.

The same actor family repeatedly rewrites `DS:34E2` and frame state on collision
or interaction.  The visible back-shot behaviour is therefore modelled as: if a
player shot reaches a guard from behind, the shot is consumed and the guard turns
toward the player instead of blindly continuing in the same direction.

## Runtime changes

- Bank-14 shooter variants (`base_tile 24` and `32`) now fire only when they can
  see the player:
  - same tile row;
  - player is in front of the current direction;
  - no body-solid runtime cell between enemy and player.
- Their shot timer no longer counts down while line of sight is blocked.
- A shot from behind flips the guard direction and resets its actor frame
  counter.  This mirrors the observed "turn toward player" response.
- The normal damage/degrade path still applies for frontal hits:
  `32 -> 24 -> 16 -> 8 -> 0 -> RIP(40)`.

Open questions remain around the exact projectile helper `0x5784`: projectile
sprite/timing is still approximated as a simple horizontal bullet, but the spawn
condition is now much closer to the original actor branch.
