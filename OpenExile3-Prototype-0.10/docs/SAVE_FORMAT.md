# Exile III Windows save notes — Prototype 0.8

These offsets apply to the supplied Exile III Windows saves used by the project.

## Top-level layout

```text
0           6       header / mode flags
6           34,085  party record, XOR 0x5C
34,091      16,384  setup block
50,475      10,956  six PC records, 1,826 bytes each, XOR 0x6B
61,431       9,216  outdoor 96x96 map/info buffer, x-major
70,647      ...     current-town state
```

## Header mode

First little-endian 16-bit value:

```text
1342  town
5790  outdoors
```

## Confirmed party fields

Decoded XOR-0x5C party offsets:

```text
0       uint32 age/ticks
4       uint16 gold
8       uint16 food
4,834   outdoor_corner x,y
4,836   i_w_c x,y
4,838   p_loc x,y
4,840   loc_in_sec x,y
33,562  int16 party direction
```

Gold is therefore at absolute save offsets 10-11.

## Outdoor map/info buffer

Absolute save offset `61,431`, length 9,216 bytes = 96x96.

Storage is x-major: `index = x*96 + y`.

In the supplied outside-Fort save, `0` cells exactly match the black/unexplored cells in the original game screenshot. Values `1` and `2` are both present; Prototype 0.8 preserves their distinction but treats both as drawable.

## Current town landmarks

```text
70,647   uint16 town number
70,649   int16 difficulty
75,806   60 x 92-byte compact live creature records
81,331   party X
81,332   party Y
81,333   256-byte town-name field
81,589   64x64 live terrain buffer, x-major with 64-byte x stride
```

The live terrain buffer retains the 64-byte stride for 32x32 and 48x48 towns.

## PC record landmarks

Each PC record is XOR'd with `0x6B` and is 1,826 bytes. Confirmed landmarks include:

```text
0       int16 main status
2       20-byte character name
22      30 x int16 skill values
82      int16 max HP
84      int16 current HP
86      int16 max SP
88      int16 current SP
90      int16 experience
92      int16 unspent skill points
94      int16 level
126     24 x 63-byte E3 item records
1786    int16 which_graphic
```

The supplied original-vs-editor New Cotra pair validates this mapping particularly well: the editor raises many named skills, HP/SP, and replaces equipment while the parser independently reports those semantic changes. The first 19 skill slots line up with the published classic Exile/Blades ordering; later slots remain index-only until independently named.
