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
import numpy as np

air = blockstate_to_block("universal_minecraft:air")

cache = [[[-1 for i in range(64)] for i in range(64)] for i in range(64)]

def is_block(world, x, y, z, block):
    if y > 255:
        return False
    elif y < 0:
        return False
    else:
        try:
            if cache[x][y][z] != -1:
                current_block = cache[x][y][z]
            else:
                current_block = world.get_block(x, y, z)
                cache[x][y][z] = current_block
        except:
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

def get_edges_of_cube(cube):
    '''
    Cube is a 2-tuple. The first element is the origin of the cube. The second is the size of the cube.
    '''
    origin, size = cube
    edge_origin = origin[0]-1, origin[1]-1, origin[2]-1 #origin is inside the cube, we want the outside.
    edge_size = size[0]+2, size[1]+2, size[2]+2 #We want to reach to the outside of the other side of the box.

    min_x = edge_origin[0]
    min_y = edge_origin[1]
    min_z = edge_origin[2]
    max_x = edge_origin[0]+edge_size[0]
    max_y = edge_origin[1]+edge_size[1]
    max_z = edge_origin[2]+edge_size[2]

    for o_x in range(edge_size[0]-1):
        for o_y in range(edge_size[1]-1):
            x = min_x+o_x+1
            y = min_y+o_y+1
            yield (x, y, min_z)
            yield (x, y, max_z)
    
    for o_y in range(edge_size[1]-1):
        for o_z in range(edge_size[2]-1):
            y = min_y+o_y+1
            z = min_z+o_z+1
            yield (min_x, y, z)
            yield (max_x, y, z)
    
    for o_x in range(edge_size[0]-1):
        for o_z in range(edge_size[2]-1):
            x = min_x+o_x+1
            z = min_z+o_z+1
            yield (x, min_y, z)
            yield (x, max_y, z)

    #8 Corners
    yield (min_x, min_y, min_z)
    yield (min_x, min_y, max_z)
    yield (min_x, max_y, min_z)
    yield (min_x, max_y, max_z)
    yield (max_x, min_y, min_z)
    yield (max_x, min_y, max_z)
    yield (max_x, max_y, min_z)
    yield (max_x, max_y, max_z)

    #Edges
    for o_x in range(edge_size[0]-1):
        x = o_x+1
        yield (x, min_y, min_z)
        yield (x, min_y, max_z)
        yield (x, max_y, min_z)
        yield (x, max_y, max_z)
    
    for o_y in range(edge_size[1]-1):
        y = o_y+1
        yield (min_x, y, min_z)
        yield (min_x, y, max_z)
        yield (max_x, y, min_z)
        yield (max_x, y, max_z)
    
    for o_z in range(edge_size[2]-1):
        z = o_z+1
        yield (min_x, min_y, z)
        yield (min_x, max_y, z)
        yield (max_x, min_y, z)
        yield (max_x, max_y, z)

def get_edges_of_cube_set(cube_set):
    for cube in cube_set:
        yield get_edges_of_cube(cube)

def speedy_set(list, new_element):
    for i in list:
        if i == new_element:
            return False
    list.append(new_element)
    return True

def get_edges_fast(world, cube_set, min, max, ambient_block = air):
    all_edges = set()

    for edges in get_edges_of_cube_set(cube_set):
        for x, y, z in edges:
            all_edges.add((x, y, z))
    
    for x, y, z in all_edges:
        try:
            edge = is_edge(world, x, y, z, ambient_block)
        except ChunkDoesNotExist:
            print("AYO")
            c_x = math.floor(x/16)
            c_z = math.floor(z/16)
            chunk = Chunk(c_x, c_z)
            world.put_chunk(chunk, 0)
            edge = is_edge(world, x, y, z, ambient_block)
        if edge:
            yield (x, y, z)

if __name__ == "__main__":
    cube_set = [((1, 1, 1), (0, 0, 0)), ((2, 2, 2), (0, 0, 0))]
    sum = 0
    for i in get_edges_of_cube_set(cube_set):
        for x in i:
            print(x)
            sum+=1
    print(sum)
                    
                