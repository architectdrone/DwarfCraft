'''
Finds edges.
'''
from amulet import world_interface
from amulet.api.selection import *
from amulet.api.world import *
from amulet.api.block import *
from amulet.operations import fill
from amulet.api.chunk import Chunk
from amulet.api.errors import ChunkDoesNotExist
from util import *
import math
import asyncio
import time

air = blockstate_to_block("universal_minecraft:air")

def is_block(world, x, y, z, block):
    if y > 255:
        return False
    elif y < 0:
        return False
    else:
        current_block = world.get_block(x, y, z)
        result = current_block == block
        return result

# def get_blocks_in_area(world, area):
#     blocks = []
#     for chunk, slices, _ in world.get_chunk_slices(area, 0, True):
#         s_x, s_y, s_z = slices
#         x = 

def is_edge(world, x, y, z, ambient_block = air):
    if is_block(world, x, y, z, ambient_block):
        return False
    return (is_wall(world, x,y,z, ambient_block) or is_ceiling(world, x,y,z, ambient_block) or is_floor(world, x,y,z, ambient_block))

def is_wall(world, x, y, z, ambient_block = air):
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

def is_ceiling(world, x, y, z, ambient_block = air):
    if is_block(world, x  , y-1, z  , ambient_block):
        return True
    return False

def is_floor(world, x, y, z, ambient_block = air):
    if is_block(world, x  , y+1, z  , ambient_block):
        return True
    return False

def get_edges(world, region, ambient_block = air):
    '''
    Returns all edges. An edge is defined as anytime a non-ambient block borders any other block of an ambient type.
    Ambient Blocks are blocks like air or water.
    What is returned is a location tuple          
    '''

    for x, y, z in get_positions_in_sub_box(region):
        try:
            edge = is_edge(world, x, y, z, ambient_block)
        except ChunkDoesNotExist:
            c_x = math.floor(x/16)
            c_z = math.floor(z/16)
            chunk = Chunk(c_x, c_z)
            world.put_chunk(chunk, 0)
            edge = is_edge(world, x, y, z, ambient_block)
        if edge:
            yield (x, y, z)    
