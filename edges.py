'''
Finds edges.
'''
from amulet import world_interface
from amulet.api.selection import *
from amulet.api.world import *
from amulet.api.block import *
from amulet.operations import fill
import math
import asyncio
import time

def get_single_block(x,y,z):
    lo = (x,y,z)
    hi = (x+1,y+1,z+1)
    return SubSelectionBox(lo, hi)

def get_positions_in_sub_box(sub_box):
    for x_i in range(sub_box.max_x - sub_box.min_x):
        for y_i in range(sub_box.max_y - sub_box.min_y):
            for z_i in range(sub_box.max_z - sub_box.min_z):
                x = sub_box.min_x+x_i
                y = sub_box.min_y+y_i
                z = sub_box.min_z+z_i
                yield x, y, z

def is_block(world, x, y, z, block):
    if y > 255:
        return False
    elif y < 0:
        return False
    else:
        current_block = world.get_block(x, y, z)
        result = current_block == block
        return result

def get_id(world, x, y, z):
    for chunk, slices, _ in world.get_chunk_slices(get_single_block(x, y, z), 0, True):
        return chunk.blocks[slices].max()

# def get_blocks_in_area(world, area):
#     blocks = []
#     for chunk, slices, _ in world.get_chunk_slices(area, 0, True):
#         s_x, s_y, s_z = slices
#         x = 

def is_edge(world, x, y, z, ambient_block):
    if is_block(world, x, y, z, ambient_block):
        return False
    return (is_wall(world, x,y,z, ambient_block) or is_ceiling(world, x,y,z, ambient_block) or is_floor(world, x,y,z, ambient_block))

def is_wall(world, x, y, z, ambient_block):
    if is_block(world, x+1, y  , z  , ambient_block):
        return True
    elif is_block(world, x-1, y  , z  , ambient_block):
        return True
    elif is_block(world, x  , y  , z+1, ambient_block):
        return True
    elif is_block(world, x  , y  , z-1, ambient_block):
        return True
    else:
        return False

def is_ceiling(world, x, y, z, ambient_block):
    if is_block(world, x  , y-1, z  , ambient_block):
        return True
    return False

def is_floor(world, x, y, z, ambient_block):
    if is_block(world, x  , y+1, z  , ambient_block):
        return True
    return False

def get_edges(world, region, ambient_block = None):
    '''
    Returns all edges. An edge is defined as anytime a non-ambient block borders any other block of an ambient type.
    Ambient Blocks are blocks like air or water.
    What is returned is a location tuple          
    '''

    if (not ambient_block):
        ambient_block = blockstate_to_block("universal_minecraft:air")
    
    for x, y, z in get_positions_in_sub_box(region):
        edge = is_edge(world, x, y, z, ambient_block)
        if edge:
            yield (x, y, z)    

if __name__ == "__main__":
    PATH = "C:\\Users\\Owen Mellema\\AppData\\Roaming\\.minecraft\\saves\\FUN"
    new_horizons = world_interface.load_format(PATH)
    print(f"NAME: {new_horizons.world_name}")
    print(f"VERSION: {new_horizons.game_version_string}")
    world = World(PATH, new_horizons)

    region_lo = (0, 0, 0)
    region_hi = (32, 32, 32)
    region = SubSelectionBox(region_lo, region_hi)

    air = blockstate_to_block("universal_minecraft:air")
    dirt = blockstate_to_block("universal_minecraft:dirt")
    glowstone = blockstate_to_block("universal_minecraft:glowstone")
    granite = blockstate_to_block("universal_minecraft:granite")

    ceiling = glowstone
    wall = granite
    floor = dirt
    for i in get_edges(world, region, ambient_block=air):
        x, y, z = i
        if (is_wall(world, x, y, z, air)):
            fill_block = wall
        elif (is_ceiling(world, x, y, z, air)):
            fill_block = ceiling
        else:
            fill_block = floor
        fill.fill(world, 0, get_single_block(x,y,z), {'fill_block':fill_block})
    world.save()
    world.close()