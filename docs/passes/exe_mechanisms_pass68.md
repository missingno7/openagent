# Pass 68: exit-door broken top tile correction

User testing pointed out that both halves of the dynamite exit door keep visible
broken art after the blast.  Re-checking the state-`0x16` branch confirms this.

## ASM evidence

The previous pass only modelled the lower-cell rewrite:

```text
SAM1:0x7490  cmpw $0x27d,0x1ca(%di)
SAM1:0x74B0  movw $0x27e,0x1ca(%di)
SAM1:0x74CB  movb $0x0,0x1cc(%di)
```

Immediately after that, the same branch also updates the cell above the lower
exit tile:

```text
SAM1:0x74D0..0x74E8  address x-1,y cell and clear +0x1CA
SAM1:0x7502          movw $0x027A, +0x1C8
SAM1:0x751E          movb $0, +0x1CC
```

So the post-blast door state is:

- lower cell: foreground/runtime visual `0x027D -> 0x027E`, collision cleared;
- upper cell: foreground/runtime visual `0x0279` is cleared, layer-B visual
  `0x027A` is written, collision cleared.

In the decoded 16x16 art these correspond to bank 5 tile 37 for the lower broken
exit tile, and bank 5 tile 33 for the upper broken exit tile.  The closed upper
red-arrow tile is bank 5 tile 32, so keeping tile 32 after the blast was wrong.

## Runtime change

- Opened exit-door overlay now draws:
  - top: bank 5 tile `33` (`0x027A` broken top);
  - bottom: bank 5 tile `37` (`0x027E` broken/passable lower).
- The upper cell is no longer kept solid after the blast.  This matches the ASM
  clearing `+0x1CC` for both cells.
- The lower broken cell still acts as the level-completion touch point.
