# In-memory movement sandbox — Prototype 0.10

Prototype 0.9 keeps all movement **in memory only**. It never writes party coordinates, exploration state, direction, or any other movement state back to the original Exile III save.

## Recovered direction numbering

The classic Windows `set_direction()` mapping is:

```text
0 north       1 northeast
2 east        3 southeast
4 south       5 southwest
6 west        7 northwest
```

The supplied one-tile-east Fort Emergence save pair independently validates `6 -> 2` while position changes `(33,28) -> (34,28)`.

## Town movement gate

Town moves currently apply:

1. active 32x32 / 48x48 / 64x64 bounds;
2. the native Exile III 256-entry terrain blocking table recovered from `EXILE3.EXE`;
3. occupancy of active live current-town creatures, including recovered width/height footprints.

The New Cotra sample validates creature occupancy: north of the party is passable terrain but occupied by a Guard, so the sandbox rejects the move.

## Outdoor 2x2 working-window shifts

The original engine keeps four 48x48 outdoor sectors in a 96x96 working map. Before an outdoor move, it shifts this window when the attempted destination approaches within six tiles of an edge:

```text
destination.x < 6   -> shift window left when possible
destination.x > 90  -> shift window right when possible
destination.y < 6   -> shift window up when possible
destination.y > 90  -> shift window down when possible
```

A horizontal shift changes the working coordinates by 48 tiles while preserving the same absolute world tile. For example:

```text
corner (3,4), working source (5,40)
attempt west

window shifts left
corner -> (2,4)
source -> (53,40)
destination -> (52,40)
```

Absolute source before and after the shift is identical:

```text
3*48 + 5 == 2*48 + 53
```

Prototype 0.9 implements the same remapping and the classic world-edge checks.

## Outdoor coordinate layers

The sandbox exposes all useful forms at once:

```text
outdoor_corner        top-left 48x48 sector of the 96x96 window
working position      0..95 coordinate inside the current window
quadrant i_w_c        0/1,0/1 selected from working position
local position        0..47 coordinate inside the current sector
sector                 outdoor_corner + quadrant
absolute world tile    outdoor_corner*48 + working position
```

This makes sector shifts visible without losing a stable world coordinate.

## Exploration state

The save supplies the current 96x96 explored/visibility buffer. Prototype 0.9 splits it into per-sector 48x48 maps in memory. When the working window shifts, those sector maps are reassembled into the new 96x96 view.

After each successful outdoor move, the sandbox performs the classic nine-by-nine exploration radius (`party +/- 4 tiles`). The original engine uses its full `can_see()` implementation; OpenExile3 currently uses the recovered terrain sight-blocking layer, so this part is intentionally marked as an approximation until fields, lighting and all special visibility rules are implemented.

## Town entrance detection

`OUTDOOR.DAT` directly stores up to eight `(x,y) -> town number` exits per sector. After a successful outdoor move, the sandbox checks the party's current sector-local coordinate against those records.

The first Valorim surface save validates this cleanly:

```text
start: sector (1,8), local (20,23)
region: Fort Emergence Area

move south -> local (20,24)
move south -> local (20,25)
OUTDOOR.DAT exit -> Town #21 Fort Emergence
```

Prototype 0.9 reports that entrance but deliberately stops before loading the town. The next transition layer needs the destination town's source record and correct entry square.

## Base movement semantics

The native terrain table uses code `2` for **blocked to monsters, but not the party**. The supplied outside-Fort save provides a real validation tile with code 2 that the original party can occupy; OpenExile3 permits it as well.

## Still separate / not executed

- scripted special nodes and forced moves;
- locked/secret door transitions;
- actual town loading after an outdoor entrance is detected;
- town -> outdoor exit execution;
- boats, horses and flying;
- outdoor wandering-party occupancy;
- waterfalls, conveyors, damaging terrain and movement sounds;
- NPC turns / AI;
- clock advancement;
- exact full `can_see()` / lighting behavior;
- save-file writes.

Keeping these layers separate prevents the prototype from silently inventing game behavior that has not yet been recovered or validated.

## Prototype 0.10 town-source confidence guard

The Inn of Blades save demonstrated that the fixed 64x64 live town buffer can retain stale data outside the active town footprint. A weak source-map candidate must therefore not be treated as authoritative movement bounds.

`locate_active_town_map(..., require_confident=True)` now requires a source similarity of at least 75%. `MovementSandbox` uses that strict mode. The current references are:

```text
Fort Emergence  99.02%  accepted
New Cotra       100.00% accepted
New Formello    100.00% accepted
Inn false hit    45.80% rejected
```

The Inn can still be rendered from its live save terrain, but movement is intentionally blocked until the correct source town record/size is proven.
