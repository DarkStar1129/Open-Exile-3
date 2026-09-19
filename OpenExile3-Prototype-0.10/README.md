# OpenExile3 — Prototype 0.10

Experimental native compatibility/reimplementation work for **Exile III: Ruined World**.

This package does **not** redistribute Spiderweb Software's Exile III assets or any user save files. Point it at an existing Windows Exile III installation containing `EXILE3.EXE`, the original BMP files, `TOWN.DAT`, and `OUTDOOR.DAT`.

## 0.10 milestone

Prototype 0.10 uses the new **Inn of Blades save** and **surface-message screenshot** to harden transition work and recover another original Win16 data layer.

New in this milestone:

- validates the Inn of Blades save as **Town #123**, party position `(43,20)`, day 3, 488 gold, and 18 active/populated creatures;
- proves the town save retains the exact outdoor entrance anchor: sector `(2,8)`, local `(25,32)`, `OUTDOOR.DAT` exit -> Town #123;
- adds `openexile3.transitions` to join executable town metadata with outdoor exits and resolve a town save back to its retained entrance;
- adds `tools/inspect_transition_anchor.py` for inspecting that reverse town -> outdoor linkage;
- validates the reconstructed Inn 9x9 viewport against the supplied screenshot: crop `(33,65)`, mean absolute RGB error **1.9445**, maximum channel error **3**;
- discovers that the surface narrative is stored in Win16 **RT_DIALOG resource #5731** rather than the STRINGTABLE layer used for terrain/town names;
- adds a Win16 dialog-template parser and `tools/inspect_dialog.py`; all **624/624 RT_DIALOG resources** in the supplied executable parse successfully;
- decodes resource #5731 as a 506x354 dialog with nine controls and the narrative text controls seen in the supplied screenshot;
- hardens town-size/source inference: weak source matches can no longer silently define movement bounds;
- specifically catches the Inn save's stale 64x64 inactive buffer data, which otherwise falsely points at Fort Emergence with only a 45.80% match;
- preserves live-town rendering even while the static Inn source record remains unresolved;
- expands the complete real-file regression suite to **50/50 passing tests**.

The important consequence is that transition work now has both directions anchored: outdoor exits identify a destination town, while town saves retain the outdoor exit that led into the town. The remaining hard problem is identifying/loading the correct `TOWN.DAT` record and destination entry square without relying on stale live-buffer padding.

## Why the movement result matters

The original Fort Emergence sample starts at:

```text
position   (33,28)
direction  6 (west)
```

The actual original game was then moved exactly one tile east and saved:

```text
position   (34,28)
direction  2 (east)
```

The current sandbox performs the same move from the first save entirely in memory. With NPC rendering disabled so that the original game's NPC turn is removed from the comparison, the simulated output and the real post-move save render are **byte-for-byte identical RGB images**.

That is the first direct validation that OpenExile3 is no longer only displaying save data: its recovered base movement state matches an observed original-engine movement result.

See `docs/MOVEMENT_SANDBOX.md`.

## Confirmed locations / source maps

| Location | Town # | Active size | `TOWN.DAT` terrain offset | Match |
|---|---:|---:|---:|---:|
| Fort Emergence | 21 | 64x64 | 147,260 | 4,056 / 4,096 (99.02%) |
| New Cotra | 42 | 48x48 | 288,718 | 2,304 / 2,304 (100%) |
| New Formello | 43 | 48x48 | 293,308 | 2,304 / 2,304 (100%) |

Fort Emergence's 40 differing terrain bytes are sparse live-state changes. The supplied New Cotra and New Formello maps match their original source terrain exactly.

### New Formello anchor

The new save independently decodes as:

```text
mode                 town
town                 #43 New Formello
party position       (43,24)
outdoor_corner       (7,7)
i_w_c                (0,0)
p_loc                 (10,19)
loc_in_sec            (10,19)
underlying sector     (7,7), record 70
region                Northwest Upper Exile
outdoor exit          (10,19) -> Town #43
```

The current-town creature table contains 22 populated slots, 19 of which are active in the supplied save.

## Existing 0.7 location/renderer foundations

Prototype 0.10 retains:

- town vs outdoor save-mode decoding (`1342` town, `5790` outdoors);
- retained outdoor fields `outdoor_corner`, `i_w_c`, `p_loc`, and `loc_in_sec`;
- proven invariant `p_loc = i_w_c * 48 + loc_in_sec`;
- the original 96x96 four-sector outdoor working-map reconstruction;
- compact `OUTDOOR.DAT` special locations, exits, destination towns, and signs;
- original 96x96 outdoor explored/visibility state;
- confidence-scored 32x32 / 48x48 / 64x64 source-map inference, with weak matches rejected for movement;
- terrain-only NPC line of sight using the native E3 sight-blocking table;
- classic terrain, animated terrain, shoreline frills, wall trims, roads and walkway corners;
- original PC and monster sprites;
- current-town live creature records;
- high-resolution rendering that shows more map rather than stretching 640x480.

## Quick start on CachyOS / fish

```fish
cd OpenExile3-Prototype-0.10
python -m venv .venv
source .venv/bin/activate.fish
python -m pip install -r requirements.txt
```

Assuming Exile III is installed at:

```text
/home/james/Games/Exile3-Win31/root/EXILE3
```

### Inspect a save

```fish
python tools/inspect_location.py \
  /home/james/Games/Exile3-Win31/root/EXILE3 \
  /path/to/EXILE3.SAV
```

### Render a classic 9x9 scene

```fish
python tools/render_location.py \
  /home/james/Games/Exile3-Win31/root/EXILE3 \
  /path/to/EXILE3.SAV \
  --output current-location.png
```

### Inspect a retained town/outdoor transition anchor

```fish
python tools/inspect_transition_anchor.py \
  /home/james/Games/Exile3-Win31/root/EXILE3 \
  /path/to/town-save.SAV
```

### Inspect an original Win16 dialog resource

```fish
python tools/inspect_dialog.py \
  /home/james/Games/Exile3-Win31/root/EXILE3/EXILE3.EXE \
  --id 5731
```

Use `--show-text` only when you want to print the control text decoded from your local executable.

### Render a native 2K-scale wide scene

A 45x19 tile scene at exact 2x integer scaling is 2520x1368:

```fish
python tools/render_location.py \
  /home/james/Games/Exile3-Win31/root/EXILE3 \
  /path/to/EXILE3.SAV \
  --width 45 --height 19 --scale 2 \
  --clamp-camera \
  --output current-location-wide.png
```

`--clamp-camera` is useful near town edges: rather than keeping the party rigidly centered and filling half the widescreen viewport with black, it shifts the camera inward when there is valid map terrain available.

## Interactive sandbox movement

Install pygame:

```fish
python -m pip install -r requirements-viewer.txt
```

Launch:

```fish
python tools/native_location_viewer.py \
  /home/james/Games/Exile3-Win31/root/EXILE3 \
  /path/to/EXILE3.SAV \
  --width 1600 --height 1000 --zoom 2
```

Controls:

```text
WASD / arrows       move party N/E/S/W in memory
Q E Z C             diagonal movement
numpad 1/2/3/4/6/7/8/9  movement
Shift + movement    pan camera without moving party
Home                camera follows current sandbox party
R                   reset party to the position/direction in the save
+ / -               integer zoom
V                   toggle saved outdoor visibility mask (outdoor mode)
F11                 fullscreen
Esc                 quit
```

**The viewer does not write coordinates, direction, time, terrain, or any other state back to the save.**

Current sandbox movement now implements:

```text
town:
  bounds -> terrain blocking -> live creature occupancy -> move

outdoors:
  classic 2x2 window shift -> world-edge gate -> terrain blocking
  -> move -> exploration update -> town-entrance detection
```

It deliberately does not fake special-node execution, locked doors, boats, horses, outdoor wandering parties, waterfalls, conveyors, damage tiles, NPC turns, clock advancement, or the actual town-loading step after an entrance is detected.

## Compare original Character Editor modifications

The new semantic diff tool is useful when testing `EXILE3ED.EXE` behavior:

```fish
python tools/inspect_editor_changes.py \
  before.SAV \
  after-editor.SAV \
  --exe /home/james/Games/Exile3-Win31/root/EXILE3/EXILE3.EXE
```

With the supplied New Cotra pair, it correctly reports changes such as:

```text
Jenneke HP     22/22 -> 82/82
Strength       8 -> 20
Dexterity      6 -> 20
Defense        0 -> 20
Luck           0 -> 20
Bronze gear    -> Magic Short Sword / Magic Studded Armor / ...
```

The modified party also provided a useful stress test for PC parsing because all six characters have substantially altered stats and equipment.

## Outdoor transition anchors

### Fort Emergence

```text
sector (8,9), record 89
region "Near Fort Emergence"
exit (36,36) -> Town #21
outside save position local (36,37)
```

### New Cotra

```text
sector (7,8), record 79
region "Western Upper Exile"
exit (27,25) -> Town #42
```

### New Formello

```text
sector (7,7), record 70
region "Northwest Upper Exile"
exit (10,19) -> Town #43
```

These anchors are recovered from the save and `OUTDOOR.DAT` independently.

### Valorim surface / Fort Emergence Area

```text
sector (1,8), record 73
region "Fort Emergence Area"
surface save local position (20,23)
working position (20,23)
special (20,23) -> ID #2
exit (20,25) -> Town #21 Fort Emergence
```

This is the first supplied save on the actual Valorim surface rather than the auxiliary Upper Exile/cave sectors. The native renderer independently reconstructs the supplied 9x9 gameplay viewport from the save and original data files. A later screenshot taken on the same `(20,23)` tile displays the original game's message that the party has escaped the underworld and can return by stepping there; this independently ties compact outdoor special ID 2 to that surface-transition trigger.

### Inn of Blades anchor

The new Inn save and the static world data now independently line up:

```text
town #123             Inn of Blades
party position         (43,20)
day / gold              3 / 488
active creatures        18
retained outdoor corner (1,8)
retained quadrant       (1,0)
retained working pos    (73,32)
retained local pos      (25,32)
sector                  (2,8), record 74
region                  North of Krizsan
outdoor entrance        (25,32) -> Town #123
world entrance tile     (121,416)
resource difficulty     2
```

The native 9x9 renderer also reproduces the supplied Inn screenshot closely. The current unresolved issue is **static source-map identification**: inactive cells in the save's fixed 64x64 live buffer still contain stale data from another town. The old detector mistook that padding for Fort Emergence; 0.10 now marks the 45.80% match as untrusted and refuses to use it for movement bounds.

## Town lookup helper

Town names are stored in the Win16 string resources while entrances are stored in `OUTDOOR.DAT`. The helper joins those two sources:

```fish
python tools/lookup_town.py \
  /home/james/Games/Exile3-Win31/root/EXILE3 \
  "Inn of Blades"
```

For the current data set it reports Town #123 and the `(2,8)/(25,32)` outdoor entrance.

## Save/resource-format progress

The party and PC records are XOR encoded exactly as in earlier prototypes. Prototype 0.10 retains all 30 PC skill slots and the semantic validation of the first 19 against the classic Exile/Blades skill ordering.

The executable parser now covers two Win16 resource layers used by the original game:

- STRINGTABLE resources for terrain/monster/town metadata;
- RT_DIALOG templates for original dialog geometry and control text.

The surface narrative screenshot provided the first direct gameplay validation of the RT_DIALOG path.

See:

- `docs/SAVE_FORMAT.md`
- `docs/LOCATION_FORMAT.md`
- `docs/OUTDOOR_FORMAT.md`
- `docs/TOWN_FORMAT.md`
- `docs/MOVEMENT_SANDBOX.md`
- `docs/DIALOG_FORMAT.md`
- `docs/TRANSITIONS.md`

## Tests

Synthetic/unit suite:

```fish
python -m unittest discover -s tests -v
```

The optional local reference suite can use all current samples:

```fish
set -lx E3_DATA_DIR /home/james/Games/Exile3-Win31/root/EXILE3
set -lx E3_SAVE /path/to/EXILE3.SAV
set -lx E3_EAST_SAVE /path/to/EXILE3_EAST.SAV
set -lx E3_OUTSIDE_SAVE /path/to/EXILE3_OUTSIDE.SAV
set -lx E3_COTRA_SAVE '/path/to/EXILE32_NEW COTRA.SAV'
set -lx E3_FORMELLO_SAVE /path/to/EXILE32_Edited_New_Formello.SAV
set -lx E3_BASE_COTRA_SAVE /path/to/EXILE32.SAV
set -lx E3_EDITED_SAVE /path/to/EXILE32_Edited.SAV
set -lx E3_SURFACE_SAVE /path/to/EXILE32_Edited_Surface.SAV
set -lx E3_INN_SAVE /path/to/EXILE3_Edited_Inn_of_Blades.SAV
python -m unittest discover -s tests -v
```

The packaged reference run completed **50/50 successfully**.

## Safety / write behavior

All location, renderer, editor-inspection and sandbox-movement paths are read-only.

The only save writer remains the narrow experimental `set_save_gold.py`, which writes a new output file instead of modifying its input and was previously validated byte-for-byte against the original Character Editor's 240 -> 540 gold edit.

## Major remaining layers

OpenExile3 is still a prototype, not a replacement game engine. Important remaining work includes:

- full town/outdoor transition execution after a decoded entrance is reached;
- authoritative `TOWN.DAT` record indexing for towns whose live save buffers contain stale inactive padding;
- outdoor wandering-creature state and rendering;
- exact original exploration/LOS semantics beyond the current terrain-only approximation;
- complete `can_see` behavior;
- town ground items and item interactions;
- fields/effects/special graphics;
- doors and special-node/event execution;
- boats/horses/flying;
- NPC turns and AI;
- clock/time progression;
- special-node -> dialog linkage, shops, quests, spells and combat;
- safe generalized save writing.

The next engine milestone is to recover the authoritative `TOWN.DAT` town-record index/size metadata, using Town #123 as the new difficult reference. Once the correct static Inn record is identified, the engine can execute an outdoor -> town transition by loading that record and the correct entry square. The reverse path is now structurally anchored by `retained_town_entrance()`, so this is the main prerequisite for continuous native world state.

## Licensing

OpenExile3 ports or derives some renderer/movement behavior and classic lookup tables from the GPLv2 Blades of Exile source release. This prototype is distributed under **GPLv2**; see `LICENSE.txt` and `THIRD_PARTY_NOTICES.md`.

Original Exile III assets and user saves are not included.
