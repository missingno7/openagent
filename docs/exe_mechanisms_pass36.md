# EXE Mechanisms Pass 36 - Sound Records and Playback Hooks

## Summary

Secret Agent uses the same 610-byte PC-speaker sound record layout as Crystal
Caves.  The Secret Agent `.SND` files are encrypted with the same bit-reversal
plus XOR stream used by the other game assets; after decrypting, each record is:

- 300 signed little-endian frequency words;
- `priority`, `unknown0`, `vibrate`, `unknown1`, `unknown2` as five unsigned
  little-endian words.

Each episode has three sound files (`SAM?01E.SND`, `SAM?02E.SND`,
`SAM?03E.SND`), each with twelve records, for 36 sound IDs per episode.

## Crystal Caves Match

OpenCrystalCaves `occ/src/soundmgr.cc` reads the exact same structure and uses a
fixed 320-sample slice at 44.1 kHz for each frequency word.  Playback stops at
the first `-1` frequency.  Non-positive frequencies and non-vibrating slots are
silence; otherwise the value is treated as a square-wave pitch.

That model is now mirrored in `openagent.sound`: decode the encrypted Secret
Agent files, synthesize short unsigned 8-bit mono WAVs, and play them
asynchronously on Windows.

## EXE Playback Routine

The common playback call is:

```asm
mov    $sound_id,%ax
push   %ax
lcall  $0x287e,$0x0
```

Useful SAM1 call sites already tied to runtime hooks:

| Sound ID | Evidence | Current meaning |
|---:|---|---|
| `0x04` | `SAM1:0xD6D8`, `0xC3AC`, `0xC4FF`, etc. after cell removal | high-value pickup / key-door style feedback |
| `0x05` | `SAM1:0xD650`, `0xD72D`, `0xD78D`, `0xD8D0` after collectibles | normal pickup feedback |
| `0x07` | `SAM1:0x5455` after ammo decrement and projectile setup | player/actor fire |
| `0x08` | many actor damage branches, e.g. `SAM1:0x5EC7` | hurt / enemy hit feedback |
| `0x13` | several actor kill/score branches, e.g. `SAM1:0x5C34` | enemy death / score event |
| `0x16` | `SAM1:0x5467`, `SAM1:0xD24F` gated by no-shot/panel state | no-ammo / denied action style feedback |

This table is intentionally narrow: only IDs with nearby control-flow context
are used.  The rest of the 36 sound records should be named by continuing the
same disassembly pass instead of guessing from waveform shape alone.

## Runtime State

`openagent.sound` is data-driven and episode-aware.  Switching episodes reloads
that episode's three SND files, preserving Secret Agent's shared-but-separate
episode asset layout.

Currently hooked events:

- player fire and no-ammo fire attempt;
- guard/enemy projectile fire for the implemented shooting actors;
- score/key/ammo/glasses pickups and unlocked doors;
- player hurt by enemies, beams, spikes or hostile projectiles;
- enemy hit/death and RIP pickup/shot score branches.

## Remaining Questions

1. Prove the exact `0x287e` playback routine internals, especially priority
   handling and whether the five footer words affect preemption beyond
   `vibrate`.
2. Name the remaining sound IDs from EXE call sites across SAM1/SAM2/SAM3.
3. Compare synthesized output against DOSBox capture; OpenCrystalCaves gives
   the timing model, but the original PC speaker mixer details may differ.
