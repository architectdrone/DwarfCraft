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
    max_x = edge_origin[0]+edge_size[0]-1
    max_y = edge_origin[1]+edge_size[1]-1
    max_z = edge_origin[2]+edge_size[2]-1


    #print("OX-OY")
    for o_x in range(edge_size[0]-2):
        for o_y in range(edge_size[1]-2):
            x = min_x+o_x+1
            y = min_y+o_y+1
            yield (x, y, min_z)
            yield (x, y, max_z)
    
    #print("OY-OZ")
    for o_y in range(edge_size[1]-2):
        for o_z in range(edge_size[2]-2):
            y = min_y+o_y+1
            z = min_z+o_z+1
            yield (min_x, y, z)
            yield (max_x, y, z)
    
    #print("OX-OZ")
    for o_x in range(edge_size[0]-2):
        for o_z in range(edge_size[2]-2):
            x = min_x+o_x+1
            z = min_z+o_z+1
            yield (x, min_y, z)
            yield (x, max_y, z)

    #print("CORNERS")
    #8 Corners
    yield (min_x, min_y, min_z)
    yield (min_x, min_y, max_z)
    yield (min_x, max_y, min_z)
    yield (min_x, max_y, max_z)
    yield (max_x, min_y, min_z)
    yield (max_x, min_y, max_z)
    yield (max_x, max_y, min_z)
    yield (max_x, max_y, max_z)

    #print("EDGES")
    #Edges
    for o_x in range(edge_size[0]-2):
        x = min_x+o_x+1
        yield (x, min_y, min_z)
        yield (x, min_y, max_z)
        yield (x, max_y, min_z)
        yield (x, max_y, max_z)
    
    for o_y in range(edge_size[1]-2):
        y = min_y+o_y+1
        yield (min_x, y, min_z)
        yield (min_x, y, max_z)
        yield (max_x, y, min_z)
        yield (max_x, y, max_z)
    
    for o_z in range(edge_size[2]-2):
        z = min_z+o_z+1
        yield (min_x, min_y, z)
        yield (min_x, max_y, z)
        yield (max_x, min_y, z)
        yield (max_x, max_y, z)

def get_edges_of_cube_set(cube_set):
    for cube in cube_set:
        for x, y, z in get_edges_of_cube(cube):
            yield x, y, z
        
def get_edges_fast(world, cube_set, min, max, ambient_block = air):
    all_edges = set()

    total_edges = 0
    true_edges = 0

    for x, y, z in get_edges_of_cube_set(cube_set):
        #print(f"\t{x, y, z}")
        all_edges.add((x, y, z))
        total_edges+=1
    true_edges = len(all_edges)

    print(f"Returned edges: {total_edges} True number of edges: {true_edges}")

    outside_count = 0

    for x, y, z in all_edges:
        if x < min[0] or x > max[0] or y < min[1] or y > max[1] or z < min[2] or z > max[2]:
            outside_count+=1
            continue
        try:
            edge = is_edge(world, x, y, z, ambient_block)
        except ChunkDoesNotExist:
            c_x = math.floor(x/16)
            c_z = math.floor(z/16)
            chunk = Chunk(c_x, c_z)
            world.put_chunk(chunk, 0)
            edge = is_edge(world, x, y, z, ambient_block)
        #print(f"({x, y, z}) - {edge}")
        if edge:
            yield (x, y, z)
    
    print(f"Edges outside = {outside_count}")

if __name__ == "__main__":
    cube_set = [((1, 1, 1), (2, 2, 2))]
    sum = 0
    for i in get_edges_of_cube_set(cube_set):
        for x in i:
            print(x)
            sum+=1
    print(sum)
                    
                