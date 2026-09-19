#!/usr/bin/env python3
from __future__ import annotations
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from openexile3.save import parse_save
from openexile3.town import CURRENT_TOWN_TERRAIN_OFFSET,extract_current_town_terrain,locate_active_town_map

def main()->int:
 ap=argparse.ArgumentParser(description='Inspect live Exile III current-town terrain and infer 32/48/64 map size')
 ap.add_argument('data_dir',type=Path);ap.add_argument('save',type=Path);args=ap.parse_args()
 D=args.data_dir.expanduser().resolve();S=args.save.expanduser().resolve();summary=parse_save(S,exe_path=D/'EXILE3.EXE')
 live=extract_current_town_terrain(S.read_bytes());match=locate_active_town_map((D/'TOWN.DAT').read_bytes(),live)
 print(f'Save: {S}');print(f'Town: #{summary.current_town} {summary.current_town_name or ""}'.rstrip())
 print(f'Live terrain buffer: absolute save offset {CURRENT_TOWN_TERRAIN_OFFSET:,} (64x64 stride)')
 print(f'Best active-map candidate: {match.size}x{match.size}')
 print(f'TOWN.DAT source offset: {match.source_offset:,}')
 print(f'Exact source bytes: {match.exact_bytes:,}/{match.total_bytes:,} ({match.similarity:.2%})')
 print(f'Exact source columns: {match.exact_columns}/{match.size}; column-anchor votes: {match.column_votes}')
 print(f'Simulation-safe confidence: {"yes" if match.confident else "NO - source match is too weak"}')
 return 0
if __name__=='__main__':raise SystemExit(main())
