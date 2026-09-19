# Exile III Win16 dialog resources

Prototype 0.10 adds read-only parsing of the Windows 3.x `RT_DIALOG` resources embedded in `EXILE3.EXE`.

## Why this matters

Earlier prototypes decoded Win16 `STRINGTABLE` resources for town names, terrain names and other compact metadata. The supplied Valorim surface-message screenshot exposed a different content path: its long narrative is stored directly in a dialog template, not in the string table.

In the supplied executable:

- NE resource type `5` is the Win16 dialog resource set;
- 624 dialog resources are present;
- all 624 parse with the current standard Win16 template decoder;
- the supplied surface narrative corresponds to dialog resource **5731**;
- resource 5731 is 506x354 dialog units and contains nine controls.

The project does not redistribute the original dialog text. It reads the user's own `EXILE3.EXE` at runtime.

## Implemented template layout

The parser handles the compact 16-bit layout used by Exile III:

```text
DWORD style
BYTE  control_count
SHORT x, y, width, height
menu name / ordinal
class name / ordinal
title string / ordinal
[optional WORD point size + font name when DS_SETFONT is set]

repeated control_count times:
    SHORT x, y, width, height
    WORD  control_id
    DWORD style
    control class (predefined byte 0x80..0x85 or string/ordinal)
    control text / ordinal
    BYTE  extra_data_length
    BYTE  extra_data[extra_data_length]
```

Unlike the later Win32 extended dialog format, these Exile III control records are packed consecutively; inserting Win32-style DWORD alignment breaks resource 5731 immediately.

## API

```python
from pathlib import Path
from openexile3.ne import decode_win16_dialog_resources, find_win16_dialogs

exe = Path('/path/to/EXILE3.EXE')
dialogs = decode_win16_dialog_resources(exe)
surface = dialogs[5731]
print(surface.width, surface.height, len(surface.controls))

matches = find_win16_dialogs(exe, 'search phrase')
```

Command-line inspection:

```fish
python tools/inspect_dialog.py \
  /home/james/Games/Exile3-Win31/root/EXILE3/EXILE3.EXE \
  --id 5731
```

Add `--show-text` only when you explicitly want the tool to print text from your local executable.

## Current limitation

This identifies and decodes dialog resources, but it does **not** yet decode the game-script/special-node instruction that maps outdoor special ID 2 to dialog resource 5731 at runtime. The screenshot, saved outdoor position and resource contents make this a strong reference pair for that next layer, but the runtime linkage should be proven before it is encoded as engine behavior.
