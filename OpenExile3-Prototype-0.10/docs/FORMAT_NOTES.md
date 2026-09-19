# Exile III format notes — Prototype 0.7

## Terrain graphics

- terrain cell: **28x36** pixels;
- `TER1.BMP`..`TER4.BMP`: 50 cells each;
- `TER5.BMP`: 40 cells;
- 240 static terrain pictures total;
- `TERANIM.BMP` contains four-frame animation strips;
- animated picture values in `EXILE3.EXE` are 300..313.

The 256-entry terrain ID -> picture table is found automatically from a unique signature in `EXILE3.EXE` (reference executable offset `0xB6A0`). Terrain names are read from Win16 `STRINGTABLE` resources.

## Native collision table

Prototype 0.7 recovers a second 256-entry terrain table directly from `EXILE3.EXE`.

Reference executable offset:

```text
0x5DC7E (384,126)
```

The table uses values 0..5. Working meanings validated against named terrain and the one-tile movement sample are documented in the README and `openexile3/collision.py`.

## OUTDOOR.DAT

- 289,800 bytes;
- 90 records;
- 3,220 bytes per record;
- first 2,304 bytes = 48x48 x-major terrain grid;
- columns 0..6 form the contiguous 7x10 Valorim surface;
- logical storage columns 7..8 contain auxiliary/cave regions.

## TOWN.DAT

`TOWN.DAT` is not a uniform 3,600-byte-record file despite its total size being divisible by 3,600.

For current town #21, Fort Emergence, the original 64x64 terrain stream begins at byte **147,260** and matches the live saved terrain 99.02%.

## Classic rendering resources

The original Windows renderer uses `MIXED.BMP` for thin shoreline and wall-corner trim overlays. Prototype 0.7 reproduces that approach directly from the user's own Exile III bitmap rather than shipping derivative graphics.

Monster sprites are selected from `MONST1.BMP`..`MONST9.BMP`; the supplied Fort Emergence NPC sample contains only 1x1 creatures, allowing full validation of the current renderer path.
