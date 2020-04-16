from caves import populate
from edges import get_edges, is_ceiling, is_floor, is_wall, get_single_block
from util import place_single_block, line_y, clamp, get_positions_in_sub_box, map
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

LAVA_POOL_SPAWN_CHANCE = 0.20 #Spawn chance for lava pools in the threshold
LAVA_POOL_FAST = False #Use the fast method of generating lava pools. This does not fill the area.

min = (0, 0, 0)
max = (SQUARE_MAX, SQUARE_MAX, SQUARE_MAX)

#Blocks
air = blockstate_to_block("universal_minecraft:air")
glowstone = blockstate_to_block("universal_minecraft:glowstone")
stone = blockstate_to_block("universal_minecraft:stone")
dirt = blockstate_to_block("universal_minecraft:dirt")
podzol = blockstate_to_block("universal_minecraft:podzol")
cobblestone = blockstate_to_block("universal_minecraft:cobblestone")
lava = blockstate_to_block("universal_minecraft:lava")

#Various Noise Functions
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

#Field Declaration
def hazard_field(x, y, z):
    '''
    Degree of danger, between 0.0 (safe) and 1.0 (dangerous). 0.5 is the average.
    '''
    hazard_seed = SEED+666 #HELL YEAH
    return perlin(x, y, z, base=hazard_seed)

#Cave Decoration
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
    to_return = 0
    if is_ceiling(world, x, y, z, air):
        if perlin_probability(GLOWSTONE_CLUSTER_SPAWN_CHANCE, x, y, z):
            length = random.randint(1, GLOWSTONE_CLUSTER_MAX_LENGTH)
            to_return = 1
            if random.random() < GLOWSTONE_CLUSTER_COMPRESSION:
                grow_stalagtite(world, x, y-1, z, block, length)
    return to_return

def handle_lava_pools(world, x, y, z, fast = False):
    floor = is_floor(world, x, y, z)
    #correct_hazard_level = hazard_field(x, y, z) > LAVA_POOL_HAZARD_THRESHOLD
    scaling_factor = (2/(map(y,0,SQUARE_MAX,0,1)+1))-1 #We want to punish the spawn chance at high altitudes. This equation does exactly that.
    spawn = perlin_probability(scaling_factor*LAVA_POOL_SPAWN_CHANCE, x, y, z, seed = SEED*5)

    if floor and spawn:
        if not fast:
            place_single_block(world, air, x, y, z)
            return slow_pool_fill(world, x, y, z, lava)
        else:
            place_single_block(world, lava, x, y, z)
            return 1
    return 0

def slow_pool_fill(world, x, y, z, block, downwards = False):
    '''
    We use a modified flood fill algorithim. This is likely to be slow.
    Also, there are some silly little bugs, due to preserving stack space.
    '''
    #print(f"Looking at {x, y, z}. ", end = "")
    if (x < 0 or x > SQUARE_MAX) or (y < 0 or y > SQUARE_MAX) or (z < 0 or z > SQUARE_MAX):
        #print("Outta bounds!")
        return 0
    elif world.get_block(x, y, z) == air:
        #print("That's good!")
        if downwards:
            place_single_block(world, block, x, y, z)
            return slow_pool_fill(world, x, y, z, block, downwards = True)+1
        else:
            place_single_block(world, block, x, y, z)
            total = 1
            total+=slow_pool_fill(world, x-1, y  , z  , block)
            total+=slow_pool_fill(world, x+1, y  , z  , block)
            total+=slow_pool_fill(world, x  , y-1, z  , block, downwards = True)
            total+=slow_pool_fill(world, x  , y  , z-1, block)
            total+=slow_pool_fill(world, x  , y  , z+1, block)
            return total
    else:
        #print("Not Air, no can do!")
        return 0

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
    stalagtites = 0
    lava_pools = 0
    floors = 0
    ceilings = 0
    print("DECORATING CAVES...")
    for x, y, z in get_edges(world, subbox):
        stalagtites+=handle_stalagtite_clusters(world, x, y, z, glowstone, GLOWSTONE_CLUSTER_SPAWN_CHANCE, GLOWSTONE_CLUSTER_COMPRESSION, GLOWSTONE_CLUSTER_MAX_LENGTH)
        lava_pools+=handle_lava_pools(world, x, y, z)
        if (is_floor(world, x, y, z)):
            floors+=1
        if is_ceiling(world, x, y, z):
            ceilings+=1
        
            
    print(f"DONE in {time.time()-start}s. Placed lava pools on {(lava_pools/floors)*100:.1f}% of floors, and stalagtites on {(stalagtites/ceilings)*100:.1f}% of floors.")
    print(f"There were {stalagtites} stalagtites on {ceilings} ceilings and {lava_pools} lava pools on {floors} floors.")

    print(f"ALL DONE in {time.time()-program_start}")
    world.save()
    world.close()
