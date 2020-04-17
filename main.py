from caves import populate
from edges import get_edges, is_ceiling, is_floor, is_wall, get_single_block
from util import place_single_block, line_y, clamp, get_positions_in_sub_box, map, get_block_wrapper
from amulet.api.world import *
from amulet.api.selection import *
from amulet.api.block import *
from amulet.operations import fill
from amulet import world_interface
from amulet.api.errors import ChunkDoesNotExist
from noise import pnoise3
import math
import random
import time

SQUARE_MAX = 64
PATH = "C:\\Users\\Owen Mellema\\AppData\\Roaming\\.minecraft\\saves\\EPIC4"
SEED = random.randint(0, 1000)

CAVE_DECO = False #Whether or not to decorate caves (lava pools, glowstone clusters, etc.) About 99% of processing time is spent in this step.

GLOWSTONE_CLUSTERS = True #Whether glowstone clusters spawn
GLOWSTONE_CLUSTER_SPAWN_CHANCE = 0.05 #Chance of a glowstone cluster spawning. Approximately the percent of ceilings with glostone clusters on them.
GLOWSTONE_CLUSTER_COMPRESSION = 0.25 #Percent of ceilings in a glowstone cluster that have a stalagtite on them.
GLOWSTONE_CLUSTER_MAX_LENGTH = 5 #Maximum length of a stalagtite.

LAVA_POOLS = True #Whether Lava Pools Spawn
LAVA_POOL_SPAWN_CHANCE = 0.05 #Spawn chance for lava pools in the threshold
LAVA_POOL_PUNISHMENT_FACTOR = 4 #Spawn rates are "punished" at higher altitudes. Increase this to increase the punishment factor. Conversely, you can set it 0 to do away with punishments, but, if you have fill mode on, I wouldn't reccomend that.
LAVA_POOL_FAST = False #Use the "fast" method of generating lava pools. This prevents the dreaded "recursion limit exceeded" error.

#Ore Spawning Numbers
ORE_POCKETS_PER_CHUNK = 15 #Approximately how many ore pockets should generate in a 16x16x16 area.
ORE_POCKET_SIZE = 5 #Base ore pocket size. This is the size of an ore pocket at the exact diff it is specified at.

#Ore difficulties. Higher numbers mean they tend to spawn in the deeper parts of the map.
COAL_DIFF = 0.1
IRON_DIFF = 0.3
GOLD_DIFF = 0.6
EMERALD_DIFF = 0.7
DIAMOND_DIFF = 0.9
SILVERFISH_DIFF = 0.8

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
coal_ore = blockstate_to_block("universal_minecraft:coal_ore")
iron_ore = blockstate_to_block("universal_minecraft:iron_ore")
gold_ore = blockstate_to_block("universal_minecraft:gold_ore")
emerald_ore = blockstate_to_block("universal_minecraft:emerald_ore")
diamond_ore = blockstate_to_block("universal_minecraft:diamond_ore")
silverfish_egg = blockstate_to_block("infested_stone")
diamond_block = blockstate_to_block("diamond_block")

ores = [
    (coal_ore, COAL_DIFF),
    (iron_ore, IRON_DIFF),
    (gold_ore, GOLD_DIFF),
    (emerald_ore, EMERALD_DIFF),
    (diamond_ore, DIAMOND_DIFF),
    (silverfish_egg, SILVERFISH_DIFF)
]

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
    scaling_factor = ((2/(map(y,0,SQUARE_MAX,0,1)+1))-1)**LAVA_POOL_PUNISHMENT_FACTOR #We want to punish the spawn chance at high altitudes. This equation does exactly that.
    spawn = perlin_probability(scaling_factor*LAVA_POOL_SPAWN_CHANCE, x, y, z, seed = SEED*5)

    if floor and spawn:
        if not fast:
            place_single_block(world, air, x, y, z)
            return scanline_pool_fill(world, x, y, z, lava)
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

def scanline_pool_fill(world, sx, sy, sz, block, left_to_right = None):
    '''
    Assume we start at edge.
    '''
    if left_to_right == None:
        scanline_pool_fill(world, sx, sy, sz, block, left_to_right = True)
        scanline_pool_fill(world, sx, sy, sz, block, left_to_right = False)

    #print(f"RUNNING SCANLINE FILL AT {sx, sy, sz}")

    first = True

    stack = [(sx, sy, sz)]
    up_empty = False
    dn_empty = False

    while stack != []:
        x, y, z = stack[-1]
        stack = stack[:-1]
        up_empty = False
        dn_empty = False
        #print(f"\tPopping {x, y, z} off of the stack.")
        while True:
            try:
                if x > SQUARE_MAX or x < 0 or y > SQUARE_MAX or y < 0 or z > SQUARE_MAX or z < 0 or (get_block_wrapper(world, x, y, z) != air and not first):
                    #print(f"\t\t\t Hit a wall.")
                    break
            except ChunkDoesNotExist:
                print(f"{x, y, z} caused an EPIC FAIL!")
                break
                
            if not up_empty and get_block_wrapper(world, x+1, y, z) == air:
                #print(f"\t\t\t Detected an empty spot at {x+1, y, z} (UP)")
                up_empty = True
                stack.append((x+1, y, z))
            elif not dn_empty and get_block_wrapper(world,x-1, y, z) == air:
                #print(f"\t\t\t Detected an empty spot at {x-1, y, z} (DN)")
                dn_empty = True
                stack.append((x-1, y, z))
            elif up_empty and get_block_wrapper(world,x+1, y, z) != air:
                up_empty = False
            elif dn_empty and get_block_wrapper(world,x-1, y, z) != air:
                dn_empty = False
            
            #print(f"\t\t Filling {x, y, z}.")
            place_single_block(world, block, x, y, z)
            
            alter_y = y-1
            while True:
                if get_block_wrapper(world,x, alter_y, z) != air or alter_y < 0:
                    break
                else:
                    place_single_block(world, block, x, alter_y, z)
                    alter_y-=1 
            #slow_pool_fill(world, x, y-1, z, block, downwards=True)
            
            first = False

            if left_to_right:
                z-=1
            else:
                z+=1
    #print("STACK IS EMPTY.")

#Misc World Gen
def get_proper_ore(y):
    #Placeholder
    global ores, SQUARE_MAX
    ore, diff = random.choice(ores)
    ideal_diff = 1-map(y, 0, SQUARE_MAX, 0, 1)
    if ideal_diff > diff:
        size = ORE_POCKET_SIZE*((1+abs(ideal_diff-diff))**2)
    else:
        size = ORE_POCKET_SIZE*(1-abs(ideal_diff-diff))
    return ore, int(size)
    
def place_ore(world, x, y, z):
    ore, size = get_proper_ore(y)
    #print(f"Placing {ore} vein on size {size} at {x, y, z}. Y={y} has a diff of {1-map(y, 0, SQUARE_MAX, 0, 1)}")
    if size == 0:
        #print("\tNothing else to do.")
        return
    elif size == 1:
        #print("\tWe done here.")
        place_single_block(world, ore, x, y, z)
    else:
        for i in range(size):
            place_x = clamp(x+random.randrange(-1*int((i)/2), 1+int((i)/2)), 0, SQUARE_MAX)
            place_y = clamp(y+random.randrange(-1*int((i)/2), 1+int((i)/2)), 0, SQUARE_MAX)
            place_z = clamp(z+random.randrange(-1*int((i)/2), 1+int((i)/2)), 0, SQUARE_MAX)
            place_single_block(world, ore, place_x, place_y, place_z)
            #print(f"\tPlacing element #{i} at {place_x, place_y, place_z}")
        #print("\tDone.")

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
    print("OREIFICATION...")
    ore_pockets = int(((SQUARE_MAX**3)/(16**3))*ORE_POCKETS_PER_CHUNK)
    for i in range(ore_pockets):
        x = random.randrange(0, SQUARE_MAX)
        y = random.randrange(0, SQUARE_MAX)
        z = random.randrange(0, SQUARE_MAX)
        place_ore(world, x, y, z)
    print(f"DONE in {time.time()-start}s")

    start = time.time()
    print("CAVIFICATION...")
    populate(world, target_area, air, fill_cube_size = 32)
    print(f"DONE in {time.time()-start}s")

    start = time.time()
    print("DECORATING CAVES...")
    if CAVE_DECO:
        for x, y, z in get_edges(world, subbox):
            if GLOWSTONE_CLUSTERS:
                handle_stalagtite_clusters(world, x, y, z, glowstone, GLOWSTONE_CLUSTER_SPAWN_CHANCE, GLOWSTONE_CLUSTER_COMPRESSION, GLOWSTONE_CLUSTER_MAX_LENGTH)
            if LAVA_POOLS:
                handle_lava_pools(world, x, y, z, fast = LAVA_POOL_FAST)
    
    print(f"DONE in {time.time()-start}s.")

    print(f"ALL DONE in {time.time()-program_start}")
    world.save()
    world.close()
