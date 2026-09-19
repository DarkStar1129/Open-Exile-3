#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openexile3.ne import decode_win16_dialog_resources, find_win16_dialogs


def describe(dialog, *, show_text: bool) -> None:
    print(
        f"Dialog #{dialog.resource_id}: pos=({dialog.x},{dialog.y}) "
        f"size={dialog.width}x{dialog.height} controls={len(dialog.controls)} "
        f"style=0x{dialog.style:08X}"
    )
    if dialog.title:
        print(f"  title: {dialog.title}")
    if dialog.font_name:
        print(f"  font: {dialog.font_name} {dialog.point_size or ''}".rstrip())
    for i, control in enumerate(dialog.controls):
        cls = control.class_name
        desc = (
            f"  [{i}] id={control.control_id} class={cls!r} "
            f"rect=({control.x},{control.y},{control.width},{control.height}) "
            f"style=0x{control.style:08X}"
        )
        print(desc)
        if show_text and control.text:
            print(f"      text: {control.text}")


ap = argparse.ArgumentParser(description="Inspect Win16 RT_DIALOG resources in Exile III")
ap.add_argument("exe", type=Path, help="Path to EXILE3.EXE")
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument("--id", type=int, dest="resource_id", help="Dialog resource ID")
g.add_argument("--find", help="Case-insensitive text search across dialog controls")
ap.add_argument("--show-text", action="store_true", help="Print dialog/control text")
args = ap.parse_args()

if args.resource_id is not None:
    dialogs = decode_win16_dialog_resources(args.exe)
    dialog = dialogs.get(args.resource_id)
    if dialog is None:
        raise SystemExit(f"RT_DIALOG #{args.resource_id} was not parsed")
    describe(dialog, show_text=args.show_text)
else:
    found = find_win16_dialogs(args.exe, args.find)
    if not found:
        raise SystemExit(f"No parsed dialog contains {args.find!r}")
    for i, dialog in enumerate(found):
        if i:
            print()
        describe(dialog, show_text=args.show_text)
