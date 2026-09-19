# Town / outdoor transition anchors

Prototype 0.10 formalizes the transition metadata already recovered from saves and `OUTDOOR.DAT`.

## Forward anchor: outdoors -> town

Outdoor sector records contain exit coordinates and destination town numbers. `build_town_entrance_index()` joins those records to the town name/difficulty strings in `EXILE3.EXE`.

For Inn of Blades:

```text
town                123 (Inn of Blades)
sector               (2,8), record 74
region               North of Krizsan
local exit           (25,32)
world tile           (121,416)
resource difficulty  2
```

The existing movement sandbox already reports `town_exit=123` when an outdoor party steps onto such an exit.

## Reverse anchor: town -> retained outdoor entrance

Town-mode saves retain the preceding outdoor 2x2-window coordinates. `retained_town_entrance()` checks those retained coordinates against the current town number and `OUTDOOR.DAT`.

The supplied Inn save retains:

```text
corner       (1,8)
quadrant     (1,0)
working      (73,32)
local        (25,32)
sector       (2,8)
```

That is an exact match for the static `(25,32) -> Town #123` exit. New Cotra and New Formello provide the same kind of independent reverse anchor.

## Why transition execution is not enabled yet

A detected outdoor exit tells the engine **which town** to enter, but executing the transition still requires an authoritative way to locate that town's source record/terrain in `TOWN.DAT` and its entry square.

The Inn save exposed a failure mode in the earlier heuristic: Exile III's live town buffer is always 64x64-stride, and inactive cells can retain data from a previous town. For Inn of Blades those stale cells produce a false Fort Emergence source match of only 1,876/4,096 bytes (45.80%).

Prototype 0.10 therefore distinguishes diagnostic source candidates from simulation-safe matches. `MovementSandbox` requires a >=75% source-map similarity before accepting inferred town bounds. Known references are far above that threshold:

```text
Fort Emergence  4056/4096 = 99.02%
New Cotra       2304/2304 = 100.00%
New Formello    2304/2304 = 100.00%
Inn false hit   1876/4096 = 45.80%  -> rejected
```

This is intentionally conservative. The next reverse-engineering target is the authoritative town-record directory/size metadata in `TOWN.DAT`, not a more permissive heuristic.
