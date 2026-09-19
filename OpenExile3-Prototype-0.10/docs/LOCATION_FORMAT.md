# Exile III save location notes — Prototype 0.7

## Save mode flag

The first little-endian 16-bit value in the Windows save identifies the active world mode in the supplied samples:

- `1342` (`0x053E`) — town
- `5790` (`0x169E`) — outdoors

These values match the legacy Blades save flag constants and are independently confirmed by the supplied Fort Emergence/New Cotra town saves and the outside-Fort save.

## Outdoor position fields

The party record begins at absolute save offset 6 and is XOR'd with `0x5C`.

Within the decoded party record:

| Offset | Size | Meaning |
|---:|---:|---|
| 4,834 | 2 | `outdoor_corner` `(x,y)` sector coordinate of the 2x2 working-map upper-left |
| 4,836 | 2 | `i_w_c` `(x,y)` 0/1 quadrant within that 2x2 working map |
| 4,838 | 2 | `p_loc` `(x,y)` party coordinate in the 96x96 working map |
| 4,840 | 2 | `loc_in_sec` `(x,y)` coordinate inside the current 48x48 sector |

Validated invariant:

```text
p_loc.x = i_w_c.x * 48 + loc_in_sec.x
p_loc.y = i_w_c.y * 48 + loc_in_sec.y
```

Current sector:

```text
sector = outdoor_corner + i_w_c
index  = sector_y * 9 + sector_x
```

## Reference samples

### Outside Fort Emergence

```text
outdoor_corner = (7,8)
i_w_c          = (1,1)
p_loc          = (84,85)
loc_in_sec      = (36,37)
sector          = (8,9), record 89
```

`OUTDOOR.DAT` sector 89 contains exit `(36,36) -> town #21` and sign `(35,39)`.

### New Cotra town save

Even while the active mode is town, the party record retains the outdoor anchor:

```text
outdoor_corner = (7,8)
i_w_c          = (0,0)
p_loc          = (27,25)
loc_in_sec      = (27,25)
sector          = (7,8), record 79
```

Sector 79 contains exit `(27,25) -> town #42`.
