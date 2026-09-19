# OUTDOOR.DAT notes — Prototype 0.9

The Windows Exile III file is exactly 289,800 bytes:

```text
90 records * 3,220 bytes = 289,800 bytes
```

The logical record grid is 9 columns x 10 rows. Terrain is stored x-major.

## Confirmed compact record fields

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 2,304 | `terrain[48][48]`, x-major |
| 2,304 | 36 | 18 `(x,y)` special locations |
| 2,340 | 18 | 18 special IDs |
| 2,358 | 16 | 8 `(x,y)` town-exit locations |
| 2,374 | 8 | 8 destination town IDs |
| 2,382 | 16 | 8 `(x,y)` sign locations |
| 2,398 | 168 | compact encounter/other data — not yet fully decoded |
| 2,566 | 240 | eight fixed 30-byte local labels |
| 2,806 | 30 | region label |
| 2,836 | 384 | remaining compact data — not yet fully decoded |

Unknown areas are intentionally not assigned speculative meanings.

## Four-sector working map

The original engine combines a 2x2 group of 48x48 records into a 96x96 x-major working map. The party record's `outdoor_corner` selects the upper-left record and `i_w_c` selects the current quadrant.

For the outside-Fort reference save:

```text
corner = (7,8)
quadrants:
  (0,0) record 79
  (1,0) record 80
  (0,1) record 88
  (1,1) record 89  <- current
```

## Prototype 0.9 surface-special validation

The first supplied Valorim surface save places the party at sector `(1,8)` / local `(20,23)`. Compact record 73 contains:

```text
special location (20,23) -> special id 2
exit             (20,25) -> town #21 Fort Emergence
region                       Fort Emergence Area
```

A supplied screenshot taken on `(20,23)` shows the original surface-transition message saying that the party has escaped the underworld and can return by stepping there. This provides an independent visual anchor for outdoor special ID 2.

The movement sandbox therefore reports decoded outdoor special IDs when entering their coordinates, while deliberately leaving special-node execution/messages unimplemented until the remaining compact special-node data is decoded.

The same static-world lookup identifies the Inn of Blades without needing a save:

```text
town #123        Inn of Blades
sector            (2,8), record 74
region            North of Krizsan
local label        Near Inn of Blades
exit               (25,32) -> town #123
```
