# Reverse Engineering Notes

This file keeps the original project orientation notes.  For current gameplay
and EXE-derived hard assumptions, start with:

- `docs/reverse_engineering_status.md`
- `docs/exe_mechanisms_summary.md`
- `docs/gameplay_research.md`

## Starting Inputs

- `OpenCrystalCaves` provides a C++20/SDL source port for a closely related
  Apogee engine.
- `dissassembly` contains LZEXE-unpacked Secret Agent executables and linear
  8086 disassemblies.
- `game_data` contains all three Secret Agent episodes and their data files.

## Confirmed Early Facts

- All three `SAM*.EXE` files are LZEXE 0.91 packed. The useful executable input
  is the unpacked `SAM*_unlz.exe` from `dissassembly`.
- Static screens (`.APO`, `.TTL`, `.CRD`, `.END`) are PCX-family images. They
  start with a normal PCX manufacturer byte (`0x0A`) and use 320x200 geometry.
- `openagent.game_assets` confirms the main map/graphics pipeline:
  - `SAM?01.GFX` is `tls-sagent-8k`: 16 banks, 50 masked 16x16 EGA tiles per
    bank, decrypted with the Secret Agent XOR/bit-reversal filter and an
    8064-byte reset.
  - `SAM?02.GFX` is the 8x8 sprite/tile bank, using the same transform with a
    2048-byte reset. `openagent.game_assets.graphics` now decodes this as three banks of 50
    8x8 masked EGA sprites.
  - `SAM?03.GFX` is the encrypted level archive, decrypted with a 42-byte reset.
    Each block is 2016 bytes. Block 0 is the world map; blocks 1-16 are normal
    levels.
- Block 0 is not a platform level. It is the top-down island map where the
  player walks to level entrances. See `docs/gameplay_research.md`.
- Each Secret Agent `.SND` file is exactly 7320 bytes. That equals 12 records of
  610 bytes, matching the Crystal Caves sound record size used by
  OpenCrystalCaves.
- The Secret Agent sound bytes are not directly plausible Crystal Caves speaker
  frequency records. Their first signed words are large negative or otherwise
  implausible values, so the data is likely transformed or uses a nearby but
  different layout.
- The raw Secret Agent `.GFX` files do not parse as OpenCrystalCaves ProGraphx
  chunks starting at byte zero because they are encrypted first.

## Useful OpenCrystalCaves References

- `OpenCrystalCaves/occ/occ/src/spritemgr.cc`: ProGraphx planar graphics loader
  and EGA palette mapping.
- `OpenCrystalCaves/occ/occ/src/imagemgr.cc`: PCX screen loading and episode
  image naming.
- `OpenCrystalCaves/occ/occ/src/soundmgr.cc`: 610-byte PC speaker sound records.
- `OpenCrystalCaves/occ/game/src/level_loader.cc`: EXE-embedded level layout for
  Crystal Caves and tile decoding style.
- `OpenCrystalCaves/occ/utils/src/exe_data.cc`: LZEXE decompression integration.

## Secret Agent Filename Map

Observed from data files and EXE strings:

- Episode 1: `SAM1.EXE`, `SAM1.APO`, `SAM1.TTL`, `SAM1.CRD`, `SAM1.END`,
  `SAM101.GFX`, `SAM102.GFX`, `SAM103.GFX`, `SAM101E.SND`,
  `SAM102E.SND`, `SAM103E.SND`.
- Episode 2: same pattern with `SAM2` plus one `SAM2.END`.
- Episode 3: same pattern with `SAM3` plus `SAM3A.END` and `SAM3B.END`.

Crystal Caves naming differs:

- screens: `CC1.APG`, `CC1.TTL`, `CC1.CDT`, `CC1.END`;
- graphics: `CC1.GFX`;
- sounds: `CC1-1.SND`, `CC1-2.SND`, `CC1-3.SND`.

## Immediate Work Queue

1. Finish original world-map behavior:
   - recover world-map collision from the EXE;
   - recover entrance-to-level mapping instead of relying only on row-major
     entrance order.
2. Finish mission interaction dispatch:
   - follow runtime cell `+0x1CA` branches for keys, doors, exits, teleporters,
     toggles and non-score pickups;
   - keep raw-code semantics as evidence-backed tables, not visual guesses.
3. Continue actor branch recovery:
   - replace remaining state/speed/timer fallbacks with exact actor dispatcher
     branches;
   - keep dynamic actor markers out of the static background render.
4. Continue the sound pass:
   - the `.SND` transform is now proven as normal Secret Agent bit-reverse/XOR;
   - keep naming sound IDs from `lcall $0x287e,$0x0` call sites;
   - compare synthesized WAVs against DOSBox capture and recover priority
     handling from the playback routine.
5. Decide final engine substrate:
   - keep the Python prototype as a fast RE harness;
   - port proven behavior into a C++/SDL OpenCrystalCaves-style runtime once the
     data model and gameplay rules are stable enough.

## Tooling

`tools/inspect_secret_agent_assets.py` is the first reproducible probe. It emits
`docs/asset_inventory.md` and can extract PCX previews to binary PPM files.
