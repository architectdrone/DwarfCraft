from caves import populate
from edges import get_edges, is_ceiling, is_floor, is_wall, get_single_block
from util import place_single_block, line_y, clamp
from amulet.api.world import *
from amulet.api.selection import *
from amulet.api.block import *
from amulet.operations import fill
from amulet import world_interface
from noise import pnoise3
import math
import random
import time

SQUARE_MAX = 64
PATH = "C:\\Users\\Owen Mellema\\AppData\\Roaming\\.minecraft\\saves\\EPIC"
SEED = random.randint(0, 1000)

GLOWSTONE_CLUSTER_SPAWN_CHANCE = 0.05 #Chance of a glowstone cluster spawning. Approximately the percent of ceilings with glostone clusters on them.
GLOWSTONE_CLUSTER_COMPRESSION = 0.25 #Percent of ceilings in a glowstone cluster that have a stalagtite on them.
GLOWSTONE_CLUSTER_MAX_LENGTH = 5 #Maximum length of a stalagtite.

min = (0, 0, 0)
max = (SQUARE_MAX, SQUARE_MAX, SQUARE_MAX)

#Blocks
air = blockstate_to_block("universal_minecraft:air")
glowstone = blockstate_to_block("universal_minecraft:glowstone")
stone = blockstate_to_block("universal_minecraft:stone")
dirt = blockstate_to_block("universal_minecraft:dirt")
podzol = blockstate_to_block("universal_minecraft:podzol")
cobblestone = blockstate_to_block("universal_minecraft:cobblestone")

def deterministic_random(x, y, z):
    seed_value = (SEED**2)*x + (SEED)*y + z
    random.seed(seed_value)
    return random.random()

def distance_to_probability(distance):
    '''
    Converts a distance, from 0.5, to the probability that a value would land in the area between 0.5-distance and 0.5+distance in 3D Perlin Noise.
    Based on a linear interpolation of data collected from running 100 tests with different seeds. Valid only if octaves = 1.
    (Deprecated)
    '''
    print("(DISTANCE TO PROBABILITY)THIS IS DEPRECATED. IF YOU NEED TO USE IT, PLEASE REDO CALCULATIONS.")
    if distance < 0.12:
        return 5.82*distance+0.0148
    else:
        return 0.27*math.log(distance)+1.26

def probability_to_distance(probability):
    '''
    Converts a probability to a distance from 0.5 such that the probability that a value will land in the distance is roughly the input probability.
    '''
    if probability < 0.75:
        return 0.177*probability-0.000254
    else:
        return 0.0127*math.exp(3.39*probability)

def perlin_probability(percent_chance, x, y, z, seed = SEED):
    distance = abs(perlin(x, y, z, octaves=1, base = seed)-0.5)
    success_distance = clamp(probability_to_distance(percent_chance), 0, 1)
    return distance < success_distance

def perlin(x, y, z, octaves = 1, base = 1, size=SQUARE_MAX):
    '''
    Returns a normalized (0 - 1) value. The 0.2746 term pushes the average to around 0.5.
    '''
    return clamp(((pnoise3(x/size, y/size, z/size, octaves = octaves, base = base)+1)/2)+0.0535, 0, 0.999)

def perlin_choice(x, y, z, list):
    perlin_result = perlin(x, y, z)
    index = math.floor(perlin_result*(len(list)))
    return list[index]

def grow_stalagtite(world, x, y, z, block, height):
    '''
    Places a stalagtite. Note that this implementation is fast, but not perfect. 
    A negative consequence is that stalagtites may cut through the floor of a cave into an adjacent cave.
    The previous (perfect) implementation took about 5x longer.
    '''
    global air
    if (height < 0):
        return
    if ((y-height)<0) or world.get_block(x, y-height, z) != air:
        grow_stalagtite(world, x, y, z, block, int(math.floor(height/2))) #Try again with a shorter height.
    else:
        fill.fill(world, 0, line_y(x, y, z, height, False), {'fill_block':block})

def handle_stalagtite_clusters(world, x, y, z, block, spawn_chance, compression, max_length):
    '''
    Takes care of placing stalagtite clusters. Assumes that (x, y, z) is an edge (but not neccesarilya ceiling)
    '''
    global air
    if is_ceiling(world, x, y, z, air):
        if perlin_probability(GLOWSTONE_CLUSTER_SPAWN_CHANCE, x, y, z):
            length = random.randint(1, GLOWSTONE_CLUSTER_MAX_LENGTH)
            if random.random() < GLOWSTONE_CLUSTER_COMPRESSION:
                grow_stalagtite(world, x, y-1, z, block, length)

if __name__ == "__main__":

    program_start = time.time()
    
    subbox = SubSelectionBox(min, max)
    target_area = Selection([subbox])

    start = time.time()
    print("LOADING WORLD...")
    world = World(PATH, world_interface.load_format(PATH))
    print(f"DONE in {time.time()-start}s")

    start = time.time()
    print("STONIFICATION...")
    fill.fill(world, 0, target_area, {'fill_block': stone})
    print(f"DONE in {time.time()-start}s")

    start = time.time()
    print("CAVIFICATION...")
    populate(world, target_area, air, fill_cube_size = 32)
    print(f"DONE in {time.time()-start}s")

    start = time.time()
    print("DECORATING CAVES...")
    for x, y, z in get_edges(world, subbox):
        handle_stalagtite_clusters(world, x, y, z, glowstone, GLOWSTONE_CLUSTER_SPAWN_CHANCE, GLOWSTONE_CLUSTER_COMPRESSION, GLOWSTONE_CLUSTER_MAX_LENGTH)
        if is_floor(world, x, y, z):
            block = perlin_choice(x, y, z, [podzol, dirt, stone, cobblestone])
            place_single_block(world, block, x, y, z)
        
            
    print(f"DONE in {time.time()-start}s.")

    print(f"ALL DONE in {time.time()-program_start}")
    world.save()
    world.close()
