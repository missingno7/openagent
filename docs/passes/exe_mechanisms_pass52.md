# EXE Mechanisms Pass 52 - Gameplay Sound Hooks

## Goal

This pass follows the common PC-speaker playback call pattern:

```asm
mov    $sound_id,%ax
push   %ax
lcall  $0x287e,$0x0
```

The aim was to stop guessing from waveform shape and instead tie gameplay
sounds to nearby ASM state changes.

## Newly confirmed hooks

### Player jump = sound `0x01`

The ordinary mission jump path around `SAM1:0xBCE4..0xBCF7` checks the tile under
the player, selects a jump/armed animation state, then plays sound `0x01` right
before starting the jump state:

```asm
bce4: mov  $0x1,%ax
bce7: push %ax
bce8: lcall $0x287e,$0x0
bced: movb $0x1,DS:6EC1
bcf7: movb $0x0,DS:34EA
```

Runtime change: `update_player_tick()` now plays `SOUND_JUMP` only at the moment
a grounded jump is accepted.  It does not repeat while space is held.

### Falling money bag arm/drop = sound `0x09`

The raw `0x5B` / state `0x29` money bag branch scans upward to find the ceiling,
then rewrites the actor to falling object `0x026B`.  The arm/drop branch plays
sound `0x09`:

```asm
b173: mov  $0x9,%ax
b176: push %ax
b177: lcall $0x287e,$0x0
b191: movw $0x026B,DS:34E0(actor)
```

Runtime change: `arm_money_bag_drop()` now plays `SOUND_FALLING_BAG_DROP` instead
of the generic pickup sound.

### Teleport = sound `0x17`

This was already implemented in pass 51, but the constant is now named.  The
teleporter dispatcher at `SAM1:0xD4DE..0xD4E2` pushes sound `0x17` before setting
up the teleport state.

## Level-entry / start sound audit

There is a tempting sound near the startup/title loading path:

```asm
1b438: mov  $0x14,%ax
1b43c: call 0x1806B
1b440: mov  $0x15,%ax
1b443: push %ax
1b444: lcall $0x287e,$0x0
```

This is **not yet proven** to be the per-level-entry sound from the overworld.
The surrounding code loads `sam1.crd`/title resources and then waits for a timer
or key, so the safer interpretation is a startup/title/transition chime.  I did
not hook it to `try_enter_world_level()` yet, because that would likely make the
runtime play it too often compared with the original.

The world-map `enter level` path still needs a targeted control-flow pass from
the world tile dispatcher into the level loader to prove whether it calls
`0x287E` directly or only reaches the generic startup/loading branch.

## Sound ID table additions

| ID | ASM evidence | Current runtime name |
|---:|---|---|
| `0x01` | `SAM1:0xBCE4..0xBCF7`, immediately before `DS:6EC1=1` | `SOUND_JUMP` |
| `0x09` | `SAM1:0xB173..0xB191`, raw `0x5B` arms falling object `0x026B` | `SOUND_FALLING_BAG_DROP` |
| `0x15` | `SAM1:0x1B440..0x1B444`, startup/title/loading region | `SOUND_MENU_OR_LEVEL_START`, documented only |
| `0x17` | `SAM1:0xD4DE..0xD4E2`, teleporter dispatcher | `SOUND_TELEPORT` |

