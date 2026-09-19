#!/usr/bin/env python3
"""Unified scalable Exile III viewer with read-only sandbox movement."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openexile3.assets import TERRAIN_CELL_H, TERRAIN_CELL_W
from openexile3.classic_render import ClassicOutdoorRenderer, ClassicTownRenderer
from openexile3.location import SaveMode, parse_location_state
from openexile3.movement import DIRECTION_NAMES, MovementSandbox
from openexile3.outdoor import load_outdoor, sector_at
from openexile3.town import extract_current_town_name


def main() -> int:
    try:
        import pygame
    except ImportError:
        print("pygame is required. In a venv: python -m pip install pygame")
        return 2

    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("save", type=Path)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=1000)
    ap.add_argument("--zoom", type=int, default=2)
    args = ap.parse_args()

    D = args.data_dir
    data = args.save.read_bytes()
    state = parse_location_state(data)
    sandbox = MovementSandbox(D, data)

    if state.mode is SaveMode.TOWN:
        name = extract_current_town_name(data) or "Town"
        renderer = ClassicTownRenderer(D)
        active_size = renderer.detect_active_size(data)
    elif state.mode is SaveMode.OUTDOOR:
        sec = sector_at(load_outdoor(D / "OUTDOOR.DAT"), state.outdoor.sector_x, state.outdoor.sector_y)
        name = ((sec.region_label if sec else "") or "Outdoors").strip()
        renderer = ClassicOutdoorRenderer(D)
        active_size = None
    else:
        print(f"Unknown save mode flag {state.raw_mode}")
        return 2

    pygame.init()
    screen = pygame.display.set_mode((args.width, args.height), pygame.RESIZABLE)
    pygame.display.set_caption(f"OpenExile3 0.10 - {name} - sandbox movement")
    font = pygame.font.Font(None, 24)
    small = pygame.font.Font(None, 20)
    clock = pygame.time.Clock()

    zoom = max(1, args.zoom)
    cam = list(sandbox.position)
    follow_party = True
    saved_visibility = True
    running = True
    cache = None
    cache_key = None
    last_message = "Read-only sandbox: movement is in memory; the save is never changed."

    # Original set_direction() numbering:
    # 0 N, 1 NE, 2 E, 3 SE, 4 S, 5 SW, 6 W, 7 NW.
    move_keys = {
        pygame.K_UP: (0, -1), pygame.K_w: (0, -1), pygame.K_KP8: (0, -1),
        pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0), pygame.K_KP6: (1, 0),
        pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1), pygame.K_KP2: (0, 1),
        pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0), pygame.K_KP4: (-1, 0),
        pygame.K_q: (-1, -1), pygame.K_KP7: (-1, -1),
        pygame.K_e: (1, -1), pygame.K_KP9: (1, -1),
        pygame.K_z: (-1, 1), pygame.K_KP1: (-1, 1),
        pygame.K_c: (1, 1), pygame.K_KP3: (1, 1),
    }

    def pil_surface(im):
        rgb = im.convert("RGB")
        return pygame.image.fromstring(rgb.tobytes(), rgb.size, "RGB")

    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE,):
                    running = False
                elif e.key in move_keys:
                    dx, dy = move_keys[e.key]
                    if e.mod & pygame.KMOD_SHIFT:
                        # Shift+movement keys retain the old viewer's camera-pan ability.
                        mw, mh = sandbox.map_size
                        cam[0] = min(mw - 1, max(0, cam[0] + dx))
                        cam[1] = min(mh - 1, max(0, cam[1] + dy))
                        follow_party = False
                        last_message = f"Camera panned to {tuple(cam)}"
                    else:
                        result = sandbox.attempt(dx, dy)
                        dname = DIRECTION_NAMES[result.direction]
                        if result.moved:
                            shift = f" shift={'+'.join(result.shifted)}" if result.shifted else ""
                            entrance = f" | entrance -> town #{result.town_exit}" if result.town_exit is not None else ""
                            special = f" | outdoor special #{result.special_id}" if result.special_id is not None else ""
                            last_message = (
                                f"Moved {dname}: {result.source} -> {result.destination}; "
                                f"terrain={result.terrain_id} block={result.blocking_code}{shift}{entrance}{special}"
                            )
                            if follow_party:
                                cam[:] = sandbox.position
                        else:
                            extra = ""
                            if result.terrain_id is not None:
                                extra = f" terrain={result.terrain_id} block={result.blocking_code}"
                            last_message = f"Blocked {dname}: {result.reason}.{extra}"
                    cache_key = None
                elif e.key == pygame.K_HOME:
                    cam[:] = sandbox.position
                    follow_party = True
                    last_message = "Camera follow enabled."
                    cache_key = None
                elif e.key == pygame.K_r:
                    sandbox.reset()
                    cam[:] = sandbox.position
                    follow_party = True
                    last_message = "Sandbox position reset to the save."
                    cache_key = None
                elif e.key == pygame.K_v and state.mode is SaveMode.OUTDOOR:
                    saved_visibility = not saved_visibility
                    last_message = f"Saved outdoor visibility {'enabled' if saved_visibility else 'disabled'}."
                    cache_key = None
                elif e.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    zoom = min(6, zoom + 1)
                    cache_key = None
                elif e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    zoom = max(1, zoom - 1)
                    cache_key = None
                elif e.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                    cache_key = None

        if follow_party:
            cam[:] = sandbox.position

        w, h = screen.get_size()
        tw, th = TERRAIN_CELL_W * zoom, TERRAIN_CELL_H * zoom
        cols = max(3, (w // tw) | 1)
        rows = max(3, (h // th) | 1)
        frame = (pygame.time.get_ticks() // 180) % 4
        visibility = sandbox.visibility_buffer if state.mode is SaveMode.OUTDOOR else None
        key = (
            tuple(cam), sandbox.position, sandbox.direction, sandbox.outdoor_corner, zoom, cols, rows,
            frame, w, h, state.mode, saved_visibility, visibility,
        )
        if key != cache_key:
            renderer.terrain.anim_frame = frame
            kwargs = dict(
                view_width=cols,
                view_height=rows,
                scale=zoom,
                camera_center=tuple(cam),
                party_position=sandbox.position,
                party_direction=sandbox.direction,
                clamp_camera=True,
            )
            if state.mode is SaveMode.TOWN:
                kwargs["active_size"] = active_size
            else:
                kwargs["apply_saved_visibility"] = saved_visibility
                kwargs["outdoor_corner"] = sandbox.outdoor_corner
                kwargs["visibility_info"] = visibility
            im = renderer.render_from_save(data, **kwargs)
            cache = pil_surface(im)
            cache_key = key

        screen.fill((0, 0, 0))
        screen.blit(cache, ((w - cache.get_width()) // 2, (h - cache.get_height()) // 2))

        dir_name = DIRECTION_NAMES[sandbox.direction] if 0 <= sandbox.direction < 8 else str(sandbox.direction)
        display_name = sandbox.region_label or name if state.mode is SaveMode.OUTDOOR else name
        if state.mode is SaveMode.OUTDOOR:
            sec=sandbox.outdoor_sector; local=sandbox.outdoor_local_position; world=sandbox.outdoor_world_position
            special=sandbox.outdoor_special_at_position()
            special_text=f" special=#{special}" if special is not None else ""
            loc_text=f" sector={sec} local={local} world={world} corner={sandbox.outdoor_corner}{special_text}"
        else:
            loc_text=""
        hud = (
            f"{state.mode.value}: {display_name}  sandbox={sandbox.position} facing={dir_name}{loc_text}  "
            f"camera={tuple(cam)}  {cols}x{rows} tiles  zoom={zoom}x"
        )
        controls = (
            "Move: WASD/arrows + Q/E/Z/C diagonals | Shift+keys pan | Home follow | "
            "R reset | +/- zoom | F11 fullscreen | Esc quit"
        )
        if state.mode is SaveMode.OUTDOOR:
            controls += f" | V saved visibility={'on' if saved_visibility else 'off'}"

        lines = [hud, controls, last_message]
        rendered = [font.render(lines[0], True, (255, 255, 255))]
        rendered.extend(small.render(line, True, (255, 255, 255)) for line in lines[1:])
        bw = max(t.get_width() for t in rendered) + 16
        bh = sum(t.get_height() for t in rendered) + 12
        bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 190))
        screen.blit(bg, (6, 6))
        yy = 10
        for t in rendered:
            screen.blit(t, (12, yy))
            yy += t.get_height()

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
