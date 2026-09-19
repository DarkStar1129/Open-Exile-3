# Exile III town-format notes — Prototype 0.7

Only directly validated or explicitly provisional findings are recorded here.

## Current-town state in the Windows save

The current-town region begins at absolute offset **70,647**. Known fields include:

| Absolute offset | Meaning | Status |
|---:|---|---|
| 70,647 | town number (`uint16`) | confirmed |
| 70,649 | town difficulty (`int16`) | confirmed |
| 75,806 | 60 x 92-byte live creature records | strongly validated |
| 81,331 | party X | confirmed by one-tile save pair |
| 81,332 | party Y | confirmed by one-tile save pair |
| 81,333 | current-town name, 256 bytes | confirmed |
| 81,589 | live terrain buffer with 64-byte x stride | confirmed |

## Terrain storage order and variable active size

The live town terrain buffer uses C-style x-major storage with a fixed 64-byte x stride:

```text
index(x,y) = x*64 + y
```

The **active town size is not always 64x64**. Prototype 0.7 tests 32x32, 48x48 and 64x64 candidates by compacting the active square from the 64-stride live buffer and matching it against `TOWN.DAT`.

Validated samples:

### Fort Emergence

```text
town #21
active size       64x64
TOWN.DAT offset   147,260
match             4,056 / 4,096 bytes (99.02%)
```

The sparse differences are consistent with mutable live terrain state.

### New Cotra

```text
town #42
active size       48x48
TOWN.DAT offset   288,718
match             2,304 / 2,304 bytes (100%)
```

This proves the save retains a 64-stride live buffer while the original map itself can be smaller.

## Party position validation

The supplied Fort Emergence save pair differs by one player movement to the east:

```text
before: (33,28), party direction 6, age 778
after:  (34,28), party direction 2, age 779
```

## Live creature records

The current-town creature array begins at **75,806** and contains 60 records of 92 bytes.

Recovered record fields, relative to each 92-byte record:

| Offset | Type | Meaning |
|---:|---|---|
| 0 | `int16` | active/state |
| 2 | `int16` | attitude |
| 4 | `uint8` | monster ID |
| 5 | `uint8` | X |
| 6 | `uint8` | Y |
| 8 | `uint8` | level |
| 9 | `int16` | current HP |
| 11 | `int16` | max HP |
| 71 | `uint8` | direction |
| 73 | `uint8` | width |
| 74 | `uint8` | height |

The Fort Emergence sample contains 47 populated slots and 44 active creatures. The visible Guard is slot 38, monster ID 12, and moves from `(37,23)` to `(37,24)` during the player's one-tile turn.

## Terrain-only NPC line of sight

Prototype 0.7 applies a first LOS pass using the native E3 terrain collision/sight table. This fixes a concrete New Cotra mismatch: the NPC at `(8,26)` is inside the geometric 9x9 viewport but lies behind sight-blocking wall terrain and is therefore hidden, while the guards at `(4,28)` and `(4,31)` remain visible.

This is not yet a complete port of the original `can_see` function. Lighting, fields, special effects and scripted cases remain future layers.

## Classic trim/frill rendering

The renderer follows classic Windows Exile/Blades behavior for:

- fluid shoreline masks and thin frills from `MIXED.BMP`;
- solid wall corner trim;
- walkway corner substitutions using original pictures 218..225;
- road extension overlays from `FIELDS.BMP` for terrain definitions using pictures 202..204.

No replacement artwork is used.
