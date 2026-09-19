from __future__ import annotations

from collections.abc import Callable

from .collision import CollisionTable


def line_cells(x0:int,y0:int,x1:int,y1:int) -> list[tuple[int,int]]:
    """Return integer cells along a line, including both endpoints."""
    dx=x1-x0; dy=y1-y0
    n=max(abs(dx),abs(dy))
    if n == 0:
        return [(x0,y0)]
    out=[]
    for i in range(n+1):
        x=round(x0 + dx*i/n)
        y=round(y0 + dy*i/n)
        if not out or out[-1] != (x,y):
            out.append((x,y))
    return out


def has_line_of_sight(
    tile_at: Callable[[int,int],int],
    collision: CollisionTable,
    start: tuple[int,int],
    target: tuple[int,int],
    map_w:int,
    map_h:int,
) -> bool:
    """Terrain-only LOS used by the prototype.

    This intentionally models the recovered terrain sight-blocking layer only.
    Fields, scripted effects, lighting and other game logic remain separate.
    """
    cells=line_cells(start[0],start[1],target[0],target[1])
    for x,y in cells[1:-1]:
        if not (0<=x<map_w and 0<=y<map_h):
            return False
        if collision.blocks_sight(tile_at(x,y)):
            return False
    return True


def reveal_around(
    info: bytearray,
    tile_at: Callable[[int,int],int],
    collision: CollisionTable,
    center: tuple[int,int],
    map_w:int,
    map_h:int,
    *,
    radius:int=4,
) -> None:
    """Approximate classic update_explored() for an x-major visibility buffer.

    The party cell is marked 2 and newly visible cells are marked 1. Existing
    nonzero values are preserved. This follows the original 9x9 reveal radius,
    while LOS is currently the project's recovered terrain-only approximation.
    """
    if len(info) != map_w * map_h:
        raise ValueError("visibility buffer size does not match map dimensions")
    cx,cy=center
    if not (0<=cx<map_w and 0<=cy<map_h):
        return
    info[cx*map_h+cy]=2
    for x in range(max(0,cx-radius),min(map_w,cx+radius+1)):
        for y in range(max(0,cy-radius),min(map_h,cy+radius+1)):
            idx=x*map_h+y
            if info[idx] == 0 and has_line_of_sight(tile_at,collision,center,(x,y),map_w,map_h):
                info[idx]=1
