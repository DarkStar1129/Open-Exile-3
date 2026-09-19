#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openexile3.assets import iter_bitmap_info, load_terrain_animation_frames, load_terrain_cells
from openexile3.outdoor import load_outdoor
from openexile3.terrain import load_terrain_definitions


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze an Exile III Windows installation")
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    d = args.data_dir.expanduser().resolve()
    picture_offset, string_start, definitions = load_terrain_definitions(d / "EXILE3.EXE")
    sectors = load_outdoor(d / "OUTDOOR.DAT")
    static_cells = load_terrain_cells(d)
    anim_slots = load_terrain_animation_frames(d)

    used_ids = Counter()
    for sector in sectors:
        used_ids.update(sector.terrain)

    report = {
        "installation": str(d),
        "bitmaps": [info.__dict__ for info in iter_bitmap_info(d)],
        "terrain": {
            "count": len(definitions),
            "picture_table_file_offset": picture_offset,
            "terrain_name_string_id_start": string_start,
            "static_picture_count": len(static_cells),
            "animation_slot_count_in_sheet": len(anim_slots),
            "definitions": [
                {
                    "id": t.terrain_id,
                    "name": t.name,
                    "picture": t.picture,
                    "animated": t.is_animated,
                }
                for t in definitions
            ],
        },
        "outdoor": {
            "sector_count": len(sectors),
            "world_dimensions_sectors": [9, 10],
            "sector_dimensions_tiles": [48, 48],
            "used_terrain_ids": sorted(used_ids),
            "used_terrain_id_count": len(used_ids),
            "regions": [s.region_label for s in sectors],
        },
    }

    text = json.dumps(report, indent=2)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {args.json}")
    else:
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
