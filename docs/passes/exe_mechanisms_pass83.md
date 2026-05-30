# Pass 83 - moving-platform landing crossing

## Symptom

After normal player falling was changed to one atomic table displacement per DOS
tick, the player could pass through moving platform `0x62`. The platform helper
only recognized a player whose final sprite base ended within four pixels below
the platform top. A terminal `8 px/tick` fall can skip that narrow band.

## ASM findings

`SAM1:0xB8B3..0xBA49` confirms that normal falling applies the complete
`byte[DS:34AF + DS:34EA]` displacement before collision probes. It does not
resolve the move pixel by pixel.

The static runtime-grid probes are more detailed than the current port:

- `SAM1:0xB902..0xB934` checks body byte `+0x1CC`.
- Only after `DS:34EA > 0x0A`, `SAM1:0xB957..0xBA30` adds several foot-channel
  `+0x1CD` probes with different vertical offsets.
- Raw moving-platform token `0x62` initializes runtime visual `0x0210` without
  static body or foot solidity, so it must stay a dynamic actor in the port.

The exact original dynamic actor/player overlap branch still needs isolation.

## Runtime change

Dynamic surfaces now use a downward crossing interval for landing:

```text
previous player sprite base <= surface top <= new player sprite base
```

This keeps normal falling atomic while preventing an `8 px/tick` step from
passing through a moving platform. Standing support remains a separate helper
used when the platform carries the player horizontally.

The same crossing shape is applied to pushable-barrel tops so both dynamic
surfaces behave consistently while their actor-specific ASM paths are audited.

## Remaining gap

Static one-way collision is still broader than the EXE: the port checks its
foot channel on every falling tick, while `B8B3` gates the `+0x1CD` path behind
`DS:34EA > 0x0A` and uses offset-specific probes. That needs a dedicated pass.
