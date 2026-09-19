# Prototype 0.10 validation

Reference corpus used locally (not distributed):

- original Exile III Windows installation;
- original Fort Emergence save;
- the same save after exactly one tile east;
- save immediately outside Fort Emergence in Upper Exile;
- New Cotra save;
- unmodified and Character-Editor-modified New Cotra saves;
- Character-Editor-modified New Formello save;
- Valorim surface save near the Fort Emergence entrance;
- Character-Editor-modified Inn of Blades save;
- screenshots supplied for Fort Emergence, outside Fort Emergence, New Cotra, New Formello, the Valorim surface, the surface narrative, Inn of Blades, loot UI and combat.

## Regression results

`analysis/test-results-0.10.txt` records a complete **50/50 passing** real-file test run. The source tree also passes `python -m compileall` for the library, tools and tests.

## Movement validation

The original one-step pair remains the strongest controlled movement test:

```text
pre-move   position (33,28), direction 6 (west), age 778
post-move  position (34,28), direction 2 (east), age 779
```

Starting from the pre-move save, `MovementSandbox` performs the east move using the recovered collision table. Rendering that in-memory result with NPCs disabled is byte-for-byte identical in RGB to rendering the actual post-move save with NPCs disabled.

New Cotra supplies a creature-occupancy check: terrain north of the party is passable, but a live Guard occupies `(4,28)`, so sandbox movement north is rejected as creature-occupied.

The outside-Fort Upper Exile sample supplies the complementary collision check: terrain ID 224 north of the party has native collision code `2` (monster-only), and the sandbox correctly allows the party onto it.

## Outdoor-window and surface validation

The sandbox reproduces the classic 96x96 four-sector working-map shifts at the six-tile edge threshold. It keeps per-sector exploration state in memory while the top-left sector corner and working coordinates jump by 48 tiles.

The Valorim surface save decodes as:

```text
mode             outdoors
corner           (1,8)
working/local    (20,23)
sector           (1,8), record 73
region           Fort Emergence Area
absolute tile    (68,407)
```

`OUTDOOR.DAT` independently contains:

```text
special (20,23) -> id #2
exit    (20,25) -> Town #21 Fort Emergence
```

The supplied screenshot taken on `(20,23)` shows the original surface narrative. Prototype 0.10 additionally locates and parses that narrative in Win16 RT_DIALOG resource #5731. This is a strong special/dialog reference pair, though the runtime script instruction connecting special ID 2 to resource #5731 has not yet been decoded and is not hard-coded as engine behavior.

The native 9x9 surface renderer compared against the supplied gameplay viewport at a mean absolute RGB error of **0.380222**, maximum channel error 3.

## Win16 dialog-resource validation

The supplied `EXILE3.EXE` contains **624 RT_DIALOG resources**, and all 624 parse using the new compact Win16 dialog-template decoder.

Resource #5731 parses as:

```text
dialog rect       (10,10) 506x354
controls          9
text hash         169f0717987176b1caf328f216405d24eb66fd0f8a848a6132fbce6176b64296
```

The text hash is over the joined decoded control strings and provides regression coverage without packaging the original narrative text.

## Inn of Blades save validation

The new save decodes as:

```text
mode                 town
town                 #123 Inn of Blades
party position       (43,20)
day / gold            3 / 488
active creatures      18
retained corner       (1,8)
retained quadrant     (1,0)
retained working      (73,32)
retained local        (25,32)
```

Those retained coordinates resolve to sector `(2,8)`, record 74, `North of Krizsan`, where `OUTDOOR.DAT` independently contains `(25,32) -> Town #123`. This is the strongest town -> outdoor reverse-transition anchor in the current corpus.

The native 9x9 Inn renderer is 252x324 pixels. Against the supplied gameplay screenshot, the best exact-size crop is `(33,65,252,324)` with mean absolute RGB error **1.9445097655** and maximum channel error **3**.

### Stale town-buffer finding

The Inn sample exposed a weakness in the previous source-map heuristic. The live save always contains a 64x64-stride terrain buffer. In the Inn save, inactive cells retain enough data from Fort Emergence to produce this false candidate:

```text
candidate size       64x64
TOWN.DAT offset      147260 (Fort Emergence)
exact bytes          1876/4096
similarity           45.80%
exact columns        16/64
```

Fort Emergence, New Cotra and New Formello score 99.02%, 100%, and 100% respectively. Prototype 0.10 therefore treats source-map matches below 75% as unsafe for movement bounds. Rendering can still use the live save terrain directly, but `MovementSandbox` rejects the uncertain Inn map instead of silently simulating against incorrect 64x64 bounds.

## Transition indexing

`openexile3.transitions` now joins town-name/difficulty resources with every decoded `OUTDOOR.DAT` exit and can resolve a town-mode save's retained outdoor state back to the exact entrance used for that town.

Inn of Blades resolves to:

```text
town                 123
sector               (2,8), record 74
local entrance       (25,32)
world tile           (121,416)
region               North of Krizsan
resource difficulty  2
```

This formalizes both halves of the transition problem without pretending that destination town loading is solved.

## Existing source-map anchors

- collision table: `EXILE3.EXE` offset `0x5DC7E`, 256 entries;
- Fort Emergence: town #21, 64x64, `TOWN.DAT` terrain offset 147,260, 4,056/4,096 live bytes matching;
- New Cotra: town #42, 48x48, `TOWN.DAT` terrain offset 288,718, 2,304/2,304 exact;
- New Formello: town #43, 48x48, `TOWN.DAT` terrain offset 293,308, 2,304/2,304 exact;
- outside Fort Emergence: sector `(8,9)`, record 89, exit `(36,36) -> town #21`;
- New Cotra retained outdoor anchor: sector `(7,8)`, record 79, exit `(27,25) -> town #42`;
- New Formello retained outdoor anchor: sector `(7,7)`, record 70, exit `(10,19) -> town #43`;
- Valorim Fort Emergence area: sector `(1,8)`, record 73, special `(20,23) -> #2`, exit `(20,25) -> town #21`;
- Inn of Blades retained anchor: sector `(2,8)`, record 74, exit `(25,32) -> town #123`.

## Character Editor validation

The unmodified/edited New Cotra pair differs by 1,509 raw bytes, but the parser resolves those changes semantically: all six PCs receive the expected HP/SP boosts, many skill values change, and inventory entries are replaced by the editor-selected magic equipment. The first 19 decoded skill slots align with the classic Exile/Blades skill ordering.

## Packaging check

The package contains no original Spiderweb BMPs, `EXILE3.EXE`, `TOWN.DAT`, `OUTDOOR.DAT`, user screenshots, or user `.SAV` files. Those remain external runtime/reference inputs.
