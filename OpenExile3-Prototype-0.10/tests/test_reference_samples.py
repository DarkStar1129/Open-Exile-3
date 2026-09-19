"""Optional integration tests against locally supplied original Exile III files.

No copyrighted game assets or user save files are distributed with OpenExile3.
Environment variables select the local validation corpus.
"""
from __future__ import annotations
import os,unittest,hashlib
from pathlib import Path
from openexile3.collision import load_collision_table
from openexile3.classic_render import ClassicTownRenderer,ClassicOutdoorRenderer,has_line_of_sight
from openexile3.location import parse_location_state,SaveMode
from openexile3.movement import MovementSandbox
from openexile3.ne import decode_win16_dialog_resources,find_win16_dialogs
from openexile3.transitions import build_town_entrance_index,retained_town_entrance
from openexile3.outdoor import load_outdoor,sector_at
from openexile3.save import parse_save,extract_outdoor_info,outdoor_info_at,extract_town_name
from openexile3.town import (
    active_tile,extract_current_town_creatures,extract_current_town_position,
    extract_current_town_terrain,locate_active_town_map,locate_source_map,tile,
    UncertainTownMapError,
)

DATA=Path(os.environ['E3_DATA_DIR']) if os.environ.get('E3_DATA_DIR') else None
SAVE=Path(os.environ['E3_SAVE']) if os.environ.get('E3_SAVE') else None
EAST=Path(os.environ['E3_EAST_SAVE']) if os.environ.get('E3_EAST_SAVE') else None
OUTSIDE=Path(os.environ['E3_OUTSIDE_SAVE']) if os.environ.get('E3_OUTSIDE_SAVE') else None
COTRA=Path(os.environ['E3_COTRA_SAVE']) if os.environ.get('E3_COTRA_SAVE') else None
FORMELLO=Path(os.environ['E3_FORMELLO_SAVE']) if os.environ.get('E3_FORMELLO_SAVE') else None
SURFACE=Path(os.environ['E3_SURFACE_SAVE']) if os.environ.get('E3_SURFACE_SAVE') else None
INN=Path(os.environ['E3_INN_SAVE']) if os.environ.get('E3_INN_SAVE') else None
EDITED=Path(os.environ['E3_EDITED_SAVE']) if os.environ.get('E3_EDITED_SAVE') else None
BASE_COTRA=Path(os.environ['E3_BASE_COTRA_SAVE']) if os.environ.get('E3_BASE_COTRA_SAVE') else None
BASE_READY=bool(DATA and SAVE and EAST and DATA.exists() and SAVE.exists() and EAST.exists())
OUT_READY=bool(DATA and OUTSIDE and DATA.exists() and OUTSIDE.exists())
COTRA_READY=bool(DATA and COTRA and DATA.exists() and COTRA.exists())
FORMELLO_READY=bool(DATA and FORMELLO and DATA.exists() and FORMELLO.exists())
SURFACE_READY=bool(DATA and SURFACE and DATA.exists() and SURFACE.exists())
INN_READY=bool(DATA and INN and DATA.exists() and INN.exists())
EDIT_READY=bool(DATA and EDITED and BASE_COTRA and DATA.exists() and EDITED.exists() and BASE_COTRA.exists())


DATA_READY=bool(DATA and DATA.exists())

@unittest.skipUnless(DATA_READY,'set E3_DATA_DIR')
class ReferenceStaticWorldSamples(unittest.TestCase):
    def test_inn_of_blades_identity_and_outdoor_anchor(self):
        self.assertEqual(extract_town_name(DATA/'EXILE3.EXE',123),'Inn of Blades')
        sec=sector_at(load_outdoor(DATA/'OUTDOOR.DAT'),2,8)
        self.assertEqual((sec.index,sec.region_label),(74,'North of Krizsan'))
        self.assertIn('Near Inn of Blades',sec.labels)
        self.assertIn((25,32,123),[(e.x,e.y,e.town) for e in sec.exits])

    def test_transition_index_joins_town_resources_and_outdoor_exits(self):
        index=build_town_entrance_index(DATA)
        anchors=index[123]
        self.assertTrue(any((a.sector_x,a.sector_y,a.local_x,a.local_y)==(2,8,25,32) for a in anchors))
        inn=next(a for a in anchors if (a.sector_x,a.sector_y,a.local_x,a.local_y)==(2,8,25,32))
        self.assertEqual((inn.town_name,inn.resource_difficulty,inn.region_label),('Inn of Blades',2,'North of Krizsan'))
        self.assertEqual(inn.world_position,(121,416))

    def test_surface_narrative_is_a_decodable_win16_dialog(self):
        dialogs=decode_win16_dialog_resources(DATA/'EXILE3.EXE')
        self.assertIn(5731,dialogs)
        dialog=dialogs[5731]
        self.assertEqual((dialog.x,dialog.y,dialog.width,dialog.height),(10,10,506,354))
        self.assertEqual(len(dialog.controls),9)
        joined='\n'.join(dialog.text_controls).encode('cp1252')
        self.assertEqual(len(joined),1370)
        self.assertEqual(hashlib.sha256(joined).hexdigest(),
                         '169f0717987176b1caf328f216405d24eb66fd0f8a848a6132fbce6176b64296')
        self.assertEqual([d.resource_id for d in find_win16_dialogs(DATA/'EXILE3.EXE','reach the valley')],[5731])


@unittest.skipUnless(INN_READY,'set E3_DATA_DIR, E3_INN_SAVE')
class ReferenceInnOfBladesSample(unittest.TestCase):
    def test_inn_save_identity_position_and_reverse_outdoor_anchor(self):
        data=INN.read_bytes();summary=parse_save(INN,exe_path=DATA/'EXILE3.EXE')
        self.assertEqual((summary.current_town,summary.current_town_name,summary.current_town_difficulty),(123,'Inn of Blades',2))
        self.assertEqual((summary.day,summary.gold,summary.direction),(3,488,1))
        self.assertEqual(extract_current_town_position(data),(43,20))
        loc=parse_location_state(data).outdoor
        self.assertEqual((loc.corner_x,loc.corner_y,loc.quadrant_x,loc.quadrant_y),(1,8,1,0))
        self.assertEqual((loc.working_x,loc.working_y,loc.local_x,loc.local_y),(73,32,25,32))
        sec=sector_at(load_outdoor(DATA/'OUTDOOR.DAT'),2,8)
        self.assertIn((25,32,123),[(e.x,e.y,e.town) for e in sec.exits])
        anchor=retained_town_entrance(DATA,data)
        self.assertIsNotNone(anchor)
        self.assertEqual((anchor.town_id,anchor.local_x,anchor.local_y),(123,25,32))
        self.assertEqual(anchor.world_position,(121,416))

    def test_inn_live_creatures_and_renderer_hash(self):
        data=INN.read_bytes();creatures=extract_current_town_creatures(data)
        self.assertEqual(sum(c.populated for c in creatures),18)
        self.assertEqual(sum(c.active != 0 and c.populated for c in creatures),18)
        image=ClassicTownRenderer(DATA,anim_frame=2).render_from_save(data)
        self.assertEqual(image.size,(252,324))
        self.assertEqual(hashlib.sha256(image.convert('RGB').tobytes()).hexdigest(),
                         '75c4e005e8d479714d8d3a38ba9ad05f75881f9167d2ed256648e0e062a1f7e0')

    def test_inn_stale_padding_is_not_accepted_for_movement_bounds(self):
        data=INN.read_bytes();live=extract_current_town_terrain(data)
        match=locate_active_town_map((DATA/'TOWN.DAT').read_bytes(),live)
        self.assertEqual((match.size,match.source_offset),(64,147260))
        self.assertLess(match.similarity,0.50)
        self.assertFalse(match.confident)
        with self.assertRaises(UncertainTownMapError):
            MovementSandbox(DATA,data)

@unittest.skipUnless(BASE_READY,'set E3_DATA_DIR, E3_SAVE, E3_EAST_SAVE')
class ReferenceBaseSamples(unittest.TestCase):
    def test_one_tile_east_pair(self):
        a=SAVE.read_bytes();b=EAST.read_bytes()
        self.assertEqual(extract_current_town_position(a),(33,28));self.assertEqual(extract_current_town_position(b),(34,28))
        sa=parse_save(SAVE);sb=parse_save(EAST)
        self.assertEqual((sa.age,sb.age),(778,779));self.assertEqual((sa.direction,sb.direction),(6,2))
        terr=extract_current_town_terrain(b);self.assertEqual(tile(terr,34,28),245)

    def test_sandbox_reproduces_known_east_move_and_north_block(self):
        sand=MovementSandbox(DATA,SAVE.read_bytes())
        north=sand.attempt(0,-1)
        self.assertFalse(north.moved);self.assertEqual((north.terrain_id,north.blocking_code),(71,3))
        east=sand.attempt(1,0)
        self.assertTrue(east.moved);self.assertEqual(sand.position,(34,28));self.assertEqual(sand.direction,2)

    def test_sandbox_render_matches_real_one_step_save_without_npc_turns(self):
        before=SAVE.read_bytes();after=EAST.read_bytes();renderer=ClassicTownRenderer(DATA,anim_frame=2)
        sand=MovementSandbox(DATA,before);self.assertTrue(sand.attempt(1,0).moved)
        simulated=renderer.render_from_save(before,draw_npcs=False,party_position=sand.position,party_direction=sand.direction)
        actual=renderer.render_from_save(after,draw_npcs=False)
        self.assertEqual(simulated.convert('RGB').tobytes(),actual.convert('RGB').tobytes())

    def test_native_collision_table(self):
        t=load_collision_table(DATA/'EXILE3.EXE')
        self.assertEqual(t.file_offset,0x5DC7E)
        self.assertEqual(t.blocking_code(71),3);self.assertEqual(t.blocking_code(77),4);self.assertEqual(t.blocking_code(100),5)
        self.assertFalse(t.blocks_party(245));self.assertFalse(t.blocks_party(246))

    def test_fort_emergence_source_and_guard(self):
        b=EAST.read_bytes();terr=extract_current_town_terrain(b)
        m=locate_source_map((DATA/'TOWN.DAT').read_bytes(),terr)
        self.assertEqual(m.source_offset,147260);self.assertEqual(m.exact_bytes,4056)
        vm=locate_active_town_map((DATA/'TOWN.DAT').read_bytes(),terr)
        self.assertEqual((vm.size,vm.source_offset,vm.exact_bytes),(64,147260,4056))
        creatures=extract_current_town_creatures(b);self.assertEqual(sum(c.populated for c in creatures),47)
        guard=creatures[38]
        self.assertEqual((guard.monster_id,guard.x,guard.y,guard.level,guard.health,guard.max_health,guard.direction),(12,37,24,30,140,140,4))

    def test_classic_renderer_reference_hash(self):
        image=ClassicTownRenderer(DATA,anim_frame=2).render_from_save(EAST.read_bytes())
        self.assertEqual(image.size,(252,324))
        digest=hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()
        self.assertEqual(digest,'19ad9667cecedebee274696e64366af8d0797c01148c7f15f5c3bb47beea1b88')

@unittest.skipUnless(OUT_READY,'set E3_DATA_DIR, E3_OUTSIDE_SAVE')
class ReferenceOutdoorSample(unittest.TestCase):
    def test_fort_outdoor_transition_anchor(self):
        data=OUTSIDE.read_bytes();s=parse_location_state(data);self.assertIs(s.mode,SaveMode.OUTDOOR)
        loc=s.outdoor
        self.assertEqual((loc.corner_x,loc.corner_y),(7,8));self.assertEqual((loc.quadrant_x,loc.quadrant_y),(1,1))
        self.assertEqual((loc.working_x,loc.working_y),(84,85));self.assertEqual((loc.local_x,loc.local_y),(36,37))
        self.assertTrue(loc.invariant_ok);self.assertEqual((loc.sector_x,loc.sector_y,loc.sector_index),(8,9,89))
        sec=sector_at(load_outdoor(DATA/'OUTDOOR.DAT'),8,9)
        self.assertEqual(sec.region_label,'Near Fort Emergence')
        self.assertIn((36,36,21),[(e.x,e.y,e.town) for e in sec.exits])
        self.assertIn((35,39),[(s.x,s.y) for s in sec.signs])

    def test_outdoor_visibility_and_renderer_hash(self):
        data=OUTSIDE.read_bytes();info=extract_outdoor_info(data)
        self.assertEqual(outdoor_info_at(info,84,85),2)
        self.assertEqual(outdoor_info_at(info,80,81),0)
        image=ClassicOutdoorRenderer(DATA,anim_frame=2).render_from_save(data)
        self.assertEqual(hashlib.sha256(image.convert('RGB').tobytes()).hexdigest(),
                         'bfa7a63b7ff4ae567dce8de7d1674696d8c19bba408a981e2a94815b90eef143')

    def test_outdoor_blocks_monsters_code_does_not_block_party(self):
        sand=MovementSandbox(DATA,OUTSIDE.read_bytes())
        result=sand.attempt(0,-1)
        self.assertTrue(result.moved)
        self.assertEqual((result.terrain_id,result.blocking_code),(224,2))
        self.assertEqual(sand.position,(84,84))

@unittest.skipUnless(COTRA_READY,'set E3_DATA_DIR, E3_COTRA_SAVE')
class ReferenceNewCotraSample(unittest.TestCase):
    def test_new_cotra_transition_and_variable_town_size(self):
        data=COTRA.read_bytes();s=parse_location_state(data);self.assertIs(s.mode,SaveMode.TOWN)
        loc=s.outdoor
        self.assertEqual((loc.corner_x,loc.corner_y,loc.quadrant_x,loc.quadrant_y),(7,8,0,0))
        self.assertEqual((loc.working_x,loc.working_y,loc.local_x,loc.local_y),(27,25,27,25))
        sec=sector_at(load_outdoor(DATA/'OUTDOOR.DAT'),7,8)
        self.assertEqual(sec.region_label,'Western Upper Exile')
        self.assertIn((27,25,42),[(e.x,e.y,e.town) for e in sec.exits])
        live=extract_current_town_terrain(data);m=locate_active_town_map((DATA/'TOWN.DAT').read_bytes(),live)
        self.assertEqual((m.size,m.source_offset,m.exact_bytes,m.total_bytes),(48,288718,2304,2304))

    def test_new_cotra_los_hides_occluded_npc(self):
        data=COTRA.read_bytes();terr=extract_current_town_terrain(data);tile_at=lambda x,y:active_tile(terr,x,y,48)
        collision=load_collision_table(DATA/'EXILE3.EXE')
        self.assertFalse(has_line_of_sight(tile_at,collision,(4,29),(8,26),48,48))
        self.assertTrue(has_line_of_sight(tile_at,collision,(4,29),(4,28),48,48))
        self.assertTrue(has_line_of_sight(tile_at,collision,(4,29),(4,31),48,48))
        image=ClassicTownRenderer(DATA,anim_frame=2).render_from_save(data)
        self.assertEqual(hashlib.sha256(image.convert('RGB').tobytes()).hexdigest(),
                         'e6b0988900aaf5f4aa438435e14df65a6f8958f41582d7db5e7df9d51dfe6237')

    def test_new_cotra_sandbox_respects_creature_occupancy(self):
        sand=MovementSandbox(DATA,COTRA.read_bytes())
        result=sand.attempt(0,-1)
        self.assertFalse(result.moved)
        self.assertEqual(result.reason,'creature occupied')
        self.assertEqual(result.destination,(4,28))


@unittest.skipUnless(FORMELLO_READY,'set E3_DATA_DIR, E3_FORMELLO_SAVE')
class ReferenceNewFormelloSample(unittest.TestCase):
    def test_new_formello_anchor_and_variable_town_size(self):
        data=FORMELLO.read_bytes();s=parse_location_state(data);self.assertIs(s.mode,SaveMode.TOWN)
        loc=s.outdoor
        self.assertEqual((loc.corner_x,loc.corner_y,loc.quadrant_x,loc.quadrant_y),(7,7,0,0))
        self.assertEqual((loc.working_x,loc.working_y,loc.local_x,loc.local_y),(10,19,10,19))
        sec=sector_at(load_outdoor(DATA/'OUTDOOR.DAT'),7,7)
        self.assertEqual(sec.region_label,'Northwest Upper Exile')
        self.assertIn((10,19,43),[(e.x,e.y,e.town) for e in sec.exits])
        live=extract_current_town_terrain(data);m=locate_active_town_map((DATA/'TOWN.DAT').read_bytes(),live)
        self.assertEqual((m.size,m.source_offset,m.exact_bytes,m.total_bytes),(48,293308,2304,2304))

    def test_new_formello_render_and_creatures(self):
        data=FORMELLO.read_bytes();creatures=extract_current_town_creatures(data)
        self.assertEqual(sum(c.populated for c in creatures),22)
        self.assertEqual(sum(c.active != 0 and c.populated for c in creatures),19)
        image=ClassicTownRenderer(DATA,anim_frame=2).render_from_save(data)
        self.assertEqual(hashlib.sha256(image.convert('RGB').tobytes()).hexdigest(),
                         '9d6b315652d8a81ffcf542b16874ca9e014fdbd952085832ad3e7677ae7d2206')

    def test_new_formello_sandbox_starts_at_saved_position(self):
        sand=MovementSandbox(DATA,FORMELLO.read_bytes())
        self.assertEqual(sand.position,(43,24))
        self.assertEqual(sand.map_size,(48,48))
        result=sand.attempt(-1,0)
        self.assertTrue(result.moved)
        self.assertEqual(sand.position,(42,24))
        self.assertEqual(sand.direction,6)
        sand.reset();self.assertEqual(sand.position,(43,24))

@unittest.skipUnless(EDIT_READY,'set E3_DATA_DIR, E3_BASE_COTRA_SAVE, E3_EDITED_SAVE')
class ReferenceEditorSample(unittest.TestCase):
    def test_editor_modified_party_is_semantically_decodable(self):
        base=parse_save(BASE_COTRA);edited=parse_save(EDITED)
        self.assertEqual((base.gold,edited.gold),(240,240))
        self.assertEqual((base.characters[0].max_health,edited.characters[0].max_health),(22,82))
        self.assertEqual((base.characters[3].max_sp,edited.characters[3].max_sp),(29,82))
        self.assertIn('Magic Short Sword',edited.characters[0].inventory_names)
        self.assertEqual(edited.characters[0].skills[0:3],(20,20,20))


@unittest.skipUnless(SURFACE_READY,'set E3_DATA_DIR, E3_SURFACE_SAVE')
class ReferenceSurfaceSample(unittest.TestCase):
    def test_surface_anchor_and_fort_entrance(self):
        data=SURFACE.read_bytes();s=parse_location_state(data);self.assertIs(s.mode,SaveMode.OUTDOOR)
        loc=s.outdoor
        self.assertEqual((loc.corner_x,loc.corner_y,loc.quadrant_x,loc.quadrant_y),(1,8,0,0))
        self.assertEqual((loc.working_x,loc.working_y,loc.local_x,loc.local_y),(20,23,20,23))
        self.assertEqual((loc.sector_x,loc.sector_y,loc.sector_index),(1,8,73))
        sec=sector_at(load_outdoor(DATA/'OUTDOOR.DAT'),1,8)
        self.assertEqual(sec.region_label,'Fort Emergence Area')
        self.assertIn((20,25,21),[(e.x,e.y,e.town) for e in sec.exits])
        # The supplied surface-message screenshot is taken on this exact tile.
        # It shows the original game's "escaped the underworld" message,
        # independently identifying compact outdoor special id 2 as the trigger.
        special=sec.special_at(20,23)
        self.assertIsNotNone(special);self.assertEqual(special.special_id,2)

    def test_surface_sandbox_detects_town_entrance(self):
        sand=MovementSandbox(DATA,SURFACE.read_bytes())
        self.assertEqual(sand.outdoor_world_position,(68,407))
        self.assertEqual(sand.outdoor_special_at_position(),2)
        a=sand.attempt(0,1);self.assertTrue(a.moved);self.assertIsNone(a.town_exit)
        b=sand.attempt(0,1);self.assertTrue(b.moved);self.assertEqual(b.town_exit,21)
        self.assertEqual(sand.outdoor_sector,(1,8));self.assertEqual(sand.outdoor_local_position,(20,25))
        self.assertEqual(sand.outdoor_world_position,(68,409))

    def test_surface_special_trigger_detection(self):
        sand=MovementSandbox(DATA,SURFACE.read_bytes())
        self.assertEqual(sand.outdoor_special_at_position(),2)
        north=sand.attempt(0,-1);self.assertTrue(north.moved);self.assertIsNone(north.special_id)
        back=sand.attempt(0,1);self.assertTrue(back.moved);self.assertEqual(back.special_id,2)

    def test_surface_renderer_reference_hash(self):
        data=SURFACE.read_bytes();image=ClassicOutdoorRenderer(DATA,anim_frame=2).render_from_save(data)
        self.assertEqual(image.size,(252,324))
        # Locks the decoded surface terrain/exploration/player composition.
        self.assertEqual(hashlib.sha256(image.convert('RGB').tobytes()).hexdigest(),
                         '74849ef6a2419221195b809e02154b9aa8528d90c490ef5515b82d71a0512a74')

if __name__=='__main__':unittest.main()
