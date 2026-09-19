#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from openexile3.location import parse_location_state, SaveMode
from openexile3.outdoor import load_outdoor, sector_at
from openexile3.save import parse_save_bytes
from openexile3.town import extract_current_town_name, extract_current_town_position, extract_current_town_terrain, locate_active_town_map

ap=argparse.ArgumentParser(description='Inspect an Exile III save location in town or outdoors')
ap.add_argument('data_dir',type=Path)
ap.add_argument('save',type=Path)
args=ap.parse_args()
D=args.data_dir.expanduser().resolve(); data=args.save.read_bytes(); state=parse_location_state(data)
print(f'Save: {args.save}')
print(f'Mode: {state.mode.value} (flag {state.raw_mode})')
loc=state.outdoor
print(f'Outdoor corner: ({loc.corner_x},{loc.corner_y})')
print(f'Outdoor quadrant i_w_c: ({loc.quadrant_x},{loc.quadrant_y})')
print(f'Outdoor working-map position: ({loc.working_x},{loc.working_y})')
print(f'Outdoor local sector position: ({loc.local_x},{loc.local_y})')
print(f'Outdoor invariant p_loc=i_w_c*48+loc_in_sec: {loc.invariant_ok}')
print(f'Underlying sector: ({loc.sector_x},{loc.sector_y}) index {loc.sector_index}')
sectors=load_outdoor(D/'OUTDOOR.DAT')
sec=sector_at(sectors,loc.sector_x,loc.sector_y)
if sec:
    print(f'Region: {sec.region_label}')
    labels=[x for x in sec.labels if x]
    if labels: print('Sector labels: ' + ' | '.join(labels))
    here_specials=[sp for sp in sec.specials if (sp.x,sp.y)==(loc.local_x,loc.local_y)]
    if here_specials: print('Special at current local tile: ' + ', '.join(f'id #{sp.special_id} (slot {sp.slot})' for sp in here_specials))
    here_exits=[e for e in sec.exits if (e.x,e.y)==(loc.local_x,loc.local_y)]
    if here_exits: print('Exit at current local tile: ' + ', '.join(f'town #{e.town}' for e in here_exits))
    near_specials=[sp for sp in sec.specials if abs(sp.x-loc.local_x)<=4 and abs(sp.y-loc.local_y)<=4]
    if near_specials:
        print('Nearby specials: ' + ', '.join(f'({sp.x},{sp.y})->id #{sp.special_id}' for sp in near_specials))
    near_exits=[e for e in sec.exits if abs(e.x-loc.local_x)<=1 and abs(e.y-loc.local_y)<=1]
    if near_exits:
        print('Nearby exits: ' + ', '.join(f'({e.x},{e.y})->town #{e.town}' for e in near_exits))
    near_signs=[s for s in sec.signs if abs(s.x-loc.local_x)<=4 and abs(s.y-loc.local_y)<=4]
    if near_signs: print('Nearby signs: ' + ', '.join(f'({s.x},{s.y})' for s in near_signs))
if state.mode is SaveMode.TOWN:
    summary=parse_save_bytes(data,exe_path=D/'EXILE3.EXE')
    pos=extract_current_town_position(data)
    name=extract_current_town_name(data)
    match=locate_active_town_map((D/'TOWN.DAT').read_bytes(),extract_current_town_terrain(data))
    print(f'Town: #{summary.current_town} {name} at {pos}')
    print(f'Town active size: {match.size}x{match.size}')
    print(f'TOWN.DAT terrain offset: {match.source_offset:,}')
    print(f'Source match: {match.exact_bytes:,}/{match.total_bytes:,} ({match.similarity:.2%})')
