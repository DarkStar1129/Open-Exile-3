from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct


@dataclass(frozen=True)
class ResourceEntry:
    type_id: int
    resource_id: int
    offset: int
    length: int


@dataclass(frozen=True)
class DialogControl:
    x: int
    y: int
    width: int
    height: int
    control_id: int
    style: int
    class_name: str | int | tuple[str, int] | None
    text: str | tuple[str, int] | None
    extra_data: bytes = b""


@dataclass(frozen=True)
class DialogResource:
    resource_id: int
    style: int
    x: int
    y: int
    width: int
    height: int
    menu: str | tuple[str, int] | None
    class_name: str | tuple[str, int] | None
    title: str | tuple[str, int] | None
    point_size: int | None
    font_name: str | None
    controls: tuple[DialogControl, ...]

    @property
    def text_controls(self) -> tuple[str, ...]:
        return tuple(c.text for c in self.controls if isinstance(c.text, str) and c.text)


def parse_ne_resources(exe_path: Path) -> tuple[bytes, list[ResourceEntry]]:
    data = exe_path.read_bytes()
    if len(data) < 0x40:
        raise ValueError("File is too small to be an NE executable")
    ne_off = struct.unpack_from("<I", data, 0x3C)[0]
    if data[ne_off:ne_off + 2] != b"NE":
        raise ValueError("Not a Windows NE executable")

    resource_rel = struct.unpack_from("<H", data, ne_off + 0x24)[0]
    resource_pos = ne_off + resource_rel
    shift = struct.unpack_from("<H", data, resource_pos)[0]
    pos = resource_pos + 2
    entries: list[ResourceEntry] = []

    while True:
        type_raw, count = struct.unpack_from("<HH", data, pos)
        if type_raw == 0:
            break
        type_id = type_raw & 0x7FFF
        pos += 8  # type id, count, reserved dword
        for _ in range(count):
            off_units, len_units, _flags, rid_raw, _handle, _usage = struct.unpack_from(
                "<HHHHHH", data, pos
            )
            pos += 12
            entries.append(
                ResourceEntry(
                    type_id=type_id,
                    resource_id=rid_raw & 0x7FFF,
                    offset=off_units << shift,
                    length=len_units << shift,
                )
            )
    return data, entries


def decode_win16_string_resources(exe_path: Path) -> dict[int, str]:
    """Decode Win16 STRINGTABLE resources (resource type 6).

    A STRINGTABLE resource contains 16 one-byte-length-prefixed strings. Its
    resource ID identifies a block of 16 string IDs.
    """
    data, entries = parse_ne_resources(exe_path)
    strings: dict[int, str] = {}
    for entry in entries:
        if entry.type_id != 6:
            continue
        blob = data[entry.offset:entry.offset + entry.length]
        pos = 0
        base = (entry.resource_id - 1) * 16
        for index in range(16):
            if pos >= len(blob):
                strings[base + index] = ""
                continue
            length = blob[pos]
            pos += 1
            raw = blob[pos:pos + length]
            pos += length
            strings[base + index] = raw.decode("cp1252", errors="replace")
    return strings


def _read_win16_name(blob: bytes, pos: int, *, control_class: bool = False):
    """Read a variable Win16 dialog name/string field.

    In 16-bit dialog templates, predefined control classes are represented by
    a single byte 0x80..0x85. A 0 byte means no value. The 0xFF + WORD ordinal
    form is also accepted because some resource compilers use it for names or
    integer resource identifiers.
    """
    if pos >= len(blob):
        raise ValueError("Truncated Win16 dialog template")
    first = blob[pos]
    if first == 0:
        return None, pos + 1
    if control_class and 0x80 <= first <= 0x85:
        return first, pos + 1
    if first == 0xFF:
        if pos + 3 > len(blob):
            raise ValueError("Truncated Win16 dialog ordinal")
        return ("ordinal", struct.unpack_from("<H", blob, pos + 1)[0]), pos + 3
    end = blob.find(b"\0", pos)
    if end < 0:
        raise ValueError("Unterminated Win16 dialog string")
    return blob[pos:end].decode("cp1252", errors="replace"), end + 1


def parse_win16_dialog_resource(blob: bytes, *, resource_id: int = 0) -> DialogResource:
    """Parse a standard Windows 3.x (16-bit) RT_DIALOG resource.

    This handles the compact Win16 DLGTEMPLATE used by Exile III. Unlike the
    later Win32 format, controls are packed directly after one another; no
    DWORD alignment is inserted between DLGITEMTEMPLATE records.
    """
    if len(blob) < 13:
        raise ValueError("Dialog resource is too small")
    style = struct.unpack_from("<I", blob, 0)[0]
    control_count = blob[4]
    x, y, width, height = struct.unpack_from("<hhhh", blob, 5)
    pos = 13
    menu, pos = _read_win16_name(blob, pos)
    class_name, pos = _read_win16_name(blob, pos)
    title, pos = _read_win16_name(blob, pos)

    # DS_SETFONT is 0x40 in the low style word. Win16 stores a WORD point size
    # followed by the NUL-terminated font face when that bit is present.
    point_size: int | None = None
    font_name: str | None = None
    if style & 0x40:
        if pos + 2 > len(blob):
            raise ValueError("Truncated Win16 dialog font information")
        point_size = struct.unpack_from("<H", blob, pos)[0]
        pos += 2
        font, pos = _read_win16_name(blob, pos)
        if isinstance(font, str):
            font_name = font

    controls: list[DialogControl] = []
    for _ in range(control_count):
        if pos + 14 > len(blob):
            raise ValueError("Truncated Win16 dialog control")
        cx, cy, cw, ch, control_id = struct.unpack_from("<hhhhH", blob, pos)
        pos += 10
        control_style = struct.unpack_from("<I", blob, pos)[0]
        pos += 4
        control_class_name, pos = _read_win16_name(blob, pos, control_class=True)
        text, pos = _read_win16_name(blob, pos)
        if pos >= len(blob):
            raise ValueError("Truncated Win16 dialog control extra-data length")
        extra_count = blob[pos]
        pos += 1
        if pos + extra_count > len(blob):
            raise ValueError("Truncated Win16 dialog control extra data")
        extra_data = blob[pos:pos + extra_count]
        pos += extra_count
        controls.append(
            DialogControl(
                x=cx,
                y=cy,
                width=cw,
                height=ch,
                control_id=control_id,
                style=control_style,
                class_name=control_class_name,
                text=text,
                extra_data=extra_data,
            )
        )

    return DialogResource(
        resource_id=resource_id,
        style=style,
        x=x,
        y=y,
        width=width,
        height=height,
        menu=menu,
        class_name=class_name,
        title=title,
        point_size=point_size,
        font_name=font_name,
        controls=tuple(controls),
    )


def decode_win16_dialog_resources(exe_path: Path) -> dict[int, DialogResource]:
    """Decode parseable Win16 RT_DIALOG resources (resource type 5)."""
    data, entries = parse_ne_resources(exe_path)
    dialogs: dict[int, DialogResource] = {}
    for entry in entries:
        if entry.type_id != 5:
            continue
        blob = data[entry.offset:entry.offset + entry.length]
        try:
            dialogs[entry.resource_id] = parse_win16_dialog_resource(
                blob, resource_id=entry.resource_id
            )
        except ValueError:
            # A malformed/extended resource should not make the usable dialog
            # catalog unavailable. Callers can inspect raw ResourceEntry data
            # separately if a future executable variant needs another parser.
            continue
    return dialogs


def find_win16_dialogs(exe_path: Path, needle: str) -> tuple[DialogResource, ...]:
    """Return decoded dialogs whose title/control text contains *needle*."""
    target = needle.casefold()
    out: list[DialogResource] = []
    for dialog in decode_win16_dialog_resources(exe_path).values():
        fields: list[str] = []
        if isinstance(dialog.title, str):
            fields.append(dialog.title)
        fields.extend(dialog.text_controls)
        if any(target in value.casefold() for value in fields):
            out.append(dialog)
    return tuple(out)
