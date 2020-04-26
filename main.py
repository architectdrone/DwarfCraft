from caves import populate
from edges import get_edges, is_ceiling, is_floor, is_wall, get_single_block
from util import place_single_block, line_y, clamp, get_positions_in_sub_box, map, get_block_wrapper
from spawners import *
from amulet.api.world import *
from amulet.api.selection import *
from amulet.api.block import *
from amulet.operations import fill
from amulet import world_interface
from amulet.api.errors import ChunkDoesNotExist
from amulet.api.block_entity import BlockEntity
from noise import pnoise3
from amulet_nbt import *
import math
import random
import time
import argparse

SQUARE_MAX = 64
SEED = random.randint(0, 1000)

FULL_RESET = False

CAVE_DECO = True #Whether or not to decorate caves (lava pools, glowstone clusters, etc.) About 99% of processing time is spent in this step.

GLOWSTONE_CLUSTERS = True #Whether glowstone clusters spawn
GLOWSTONE_CLUSTER_SPAWN_CHANCE = 0.05 #Chance of a glowstone cluster spawning. Approximately the percent of ceilings with glostone clusters on them.
GLOWSTONE_CLUSTER_COMPRESSION = 0.25 #Percent of ceilings in a glowstone cluster that have a stalagtite on them.
GLOWSTONE_CLUSTER_MAX_LENGTH = 5 #Maximum length of a stalagtite.

LAVA_POOLS = True #Whether Lava Pools Spawn
LAVA_POOL_SPAWN_CHANCE = 0.05 #Spawn chance for lava pools in the threshold
LAVA_POOL_PUNISHMENT_FACTOR = 4 #Spawn rates are "punished" at higher altitudes. Increase this to increase the punishment factor. Conversely, you can set it 0 to do away with punishments, but, if you have fill mode on, I wouldn't reccomend that.
LAVA_POOL_FAST = False #Use the "fast" method of generating lava pools. This prevents the dreaded "recursion limit exceeded" error.

MOB_SPAWNERS = True #Whether mob spawners spawn
MOB_SPAWNER_SPAWN_CHANCE = 0.01 #Chance of a floor block having a mob spawner. Be careful: Even 5% was too much.

BUSHES = True #Whether bushes spawn.
BUSH_MELONS = True #Whether melons grow on bushes.
BUSH_MELON_SPAWN_CHANCE = 0.05 #Chance that a particular leaf will be a melon block.
BUSH_SPAWN_CHANCE = 0.5 #Chance that any edge will be in a bush cluster.
BUSH_COMPRESSION = 0.01 #Chance that an edge in a bush cluster will have a bush
BUSH_MIN_SIZE = 5
BUSH_MAX_SIZE = 10

BIOMES = True #Whether biome decoration occurs.
FLOWER_SPAWN_CHANCE = 0.05
GRASS_SPAWN_CHANCE = 0.1

WATER_POOLS = True
WATER_POOL_SAND_BORDER = True
WATER_POOL_SPAWN_CHANCE = 0.25
WATER_POOL_SUGARCANE_SPAWN_CHANCE = 0.25

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
sand = blockstate_to_block("universal_minecraft:sand")
podzol = blockstate_to_block("universal_minecraft:podzol")
cobblestone = blockstate_to_block("universal_minecraft:cobblestone")
gravel = blockstate_to_block("gravel")
grass_block = blockstate_to_block("minecraft:grass_block")
grass = blockstate_to_block("minecraft:grass")
lava = blockstate_to_block("universal_minecraft:lava")
water = blockstate_to_block("universal_minecraft:water")
coal_ore = blockstate_to_block("universal_minecraft:coal_ore")
iron_ore = blockstate_to_block("universal_minecraft:iron_ore")
gold_ore = blockstate_to_block("universal_minecraft:gold_ore")
emerald_ore = blockstate_to_block("universal_minecraft:emerald_ore")
diamond_ore = blockstate_to_block("universal_minecraft:diamond_ore")
silverfish_egg = blockstate_to_block("infested_stone")
diamond_block = blockstate_to_block("diamond_block")
oak_leaves = blockstate_to_block("oak_leaves")
oak_log = blockstate_to_block("oak_log")
melon = blockstate_to_block("melon")
sugarcane = blockstate_to_block("universal_minecraft:sugar_cane")

flowers = [
    blockstate_to_block("minecraft:dandelion"),
    blockstate_to_block("minecraft:poppy"),
    blockstate_to_block("minecraft:blue_orchid"),
    blockstate_to_block("minecraft:allium"),
    blockstate_to_block("minecraft:azure_bluet"),
    blockstate_to_block("minecraft:red_tulip"),
    blockstate_to_block("minecraft:orange_tulip")
]
ores = [
    (coal_ore, COAL_DIFF),
    (iron_ore, IRON_DIFF),
    (gold_ore, GOLD_DIFF),
    (emerald_ore, EMERALD_DIFF),
    (diamond_ore, DIAMOND_DIFF),
    (silverfish_egg, SILVERFISH_DIFF)
]

stone_biome_floor_blocks = [stone, cobblestone, gravel]
organic_biome_floor_blocks = [dirt, podzol, grass_block]
biome_floor_blocks = stone_biome_floor_blocks+organic_biome_floor_blocks
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
    if distance < 0.15:
        return 4.95*distance
    else:
        return 1.67*distance + 0.534

def probability_to_distance(probability):
    '''
    Converts a probability to a distance from 0.5 such that the probability that a value will land in the distance is roughly the input probability.
    '''
    if probability < 0.75:
        return 0.177*probability-0.000254
    else:
        return 0.0127*math.exp(3.39*probability)

def perlin_distance(x, y, z, seed = SEED):
    '''
    Returns distance from 0.5 at the specified coordinates.
    '''
    return abs(perlin(x, y, z, octaves=1, base = seed)-0.5)

def perlin_probability(percent_chance, x, y, z, seed = SEED):
    distance = perlin_distance(x, y, z, seed = SEED)
    success_distance = clamp(probability_to_distance(percent_chance), 0, 1)
    return distance < success_distance

def perlin_probability_selection(max, x, y, z, seed = SEED):
    '''
    Returns a number between 0 and max.
    '''

    for i in range(max+1):
        threshold = (i+1)/(max+1)
        if perlin_probability(threshold, x, y, z, seed = seed):
            return i
    return max

def perlin(x, y, z, octaves = 1, base = 1, size=SQUARE_MAX):
    '''
    Returns a normalized (0 - 1) value. The 0.2746 term pushes the average to around 0.5.
    '''
    return clamp(((pnoise3(x/size, y/size, z/size, octaves = octaves, base = base)+1)/2)+0.0535, 0, 0.999)

def perlin_choice(x, y, z, list):
    index = perlin_probability_selection(len(list)-1, x, y, z)
    return list[index]

def choose_random_weighted(weight, spread, list):
    altered_weight = clamp(weight+(random.random()*(spread*2)-spread), 0, 1)
    index = math.floor(altered_weight*(len(list)-1))
    return list[index]

#Cave Decoration
def handle_lava_pools(world, x, y, z):
    floor = is_floor(world, x, y, z)
    scaling_factor = ((2/(map(y,0,SQUARE_MAX,0,1)+1))-1)**LAVA_POOL_PUNISHMENT_FACTOR #We want to punish the spawn chance at high altitudes. This equation does exactly that.
    spawn = perlin_probability(scaling_factor*LAVA_POOL_SPAWN_CHANCE, x, y, z, seed = SEED*5)

    if floor and spawn:
        if not LAVA_POOL_FAST:
            place_single_block(world, air, x, y, z)
            return scanline_pool_fill(world, x, y, z, lava)
        else:
            place_single_block(world, lava, x, y, z)
            return 1
    return 0

def handle_glowstone_clusters(world, x, y, z):
    handle_stalagtite_clusters(world, x, y, z, glowstone, GLOWSTONE_CLUSTER_SPAWN_CHANCE, GLOWSTONE_CLUSTER_COMPRESSION, GLOWSTONE_CLUSTER_MAX_LENGTH)

def handle_mob_spawners(world, x, y, z, spawn_chance):
    if random.random() < spawn_chance and is_floor(world, x, y, z) and y+1 < SQUARE_MAX and get_block_wrapper(world, x, y, z) == stone:
        the_mob = get_mob(y)
        spawner(world, x, y+1, z, the_mob)

def handle_bushes(world, x, y, z):
    is_bush_cluster = perlin_probability(BUSH_SPAWN_CHANCE, x, y, z, seed = SEED*3)
    is_bush_spawn_location = random.random() < BUSH_COMPRESSION

    if is_bush_cluster and is_bush_spawn_location and get_block_wrapper(world, x, y, z) == stone:
        log = oak_log
        leaves = oak_leaves
        length = random.randrange(BUSH_MIN_SIZE, BUSH_MAX_SIZE)
        create_bush(world, x, y, z, log, leaves, 0, length)

def handle_biomes(world, x, y, z):
    if get_block_wrapper(world, x, y, z) == stone:
        if is_floor(world, x, y, z):
            if get_biome(x, y, z) == 0:
                place_single_block(world, perlin_choice(x, y, z, stone_biome_floor_blocks), x, y, z)
            else:
                place_single_block(world, perlin_choice(x, y, z, organic_biome_floor_blocks), x, y, z)
                if random.random() < FLOWER_SPAWN_CHANCE:
                    place_single_block(world, random.choice(flowers), x, y+1, z)
                elif random.random() < GRASS_SPAWN_CHANCE:
                    place_single_block(world, grass, x, y+1, z)
            
        else:
            if get_biome(x, y, z) == 1:
                place_single_block(world, dirt, x, y, z)

def handle_water_pools(world, x, y, z, returnBool = False):
    '''
    If returnBool, does not place a water pool, but rather returns whether it is a valid spot for a water pool.
    '''
    valid_spawn_location = is_floor(world, x, y, z) and not is_wall(world, x, y, z) and not is_ceiling(world, x, y, z)
    valid_spawn_block = get_block_wrapper(world, x, y, z) in biome_floor_blocks+[sand]
    water_area = perlin_probability(WATER_POOL_SPAWN_CHANCE, x, y, z)

    if valid_spawn_location and water_area and valid_spawn_block:
        if returnBool:
            return True
        
        place_single_block(world, water, x, y, z)
        if WATER_POOL_SAND_BORDER:
            handle_water_border(world, x-1, y  , z  )
            handle_water_border(world, x+1, y  , z  )
            handle_water_border(world, x  , y  , z-1)
            handle_water_border(world, x  , y  , z+1)
            handle_water_border(world, x-1, y  , z-1)
            handle_water_border(world, x-1, y  , z+1)
            handle_water_border(world, x+1, y  , z-1)
            handle_water_border(world, x-1, y  , z+1)
            handle_water_border(world, x-1, y-1, z  )
            handle_water_border(world, x+1, y-1, z  )
            handle_water_border(world, x  , y-1, z-1)
            handle_water_border(world, x  , y-1, z+1)
            handle_water_border(world, x-1, y-1, z-1)
            handle_water_border(world, x-1, y-1, z+1)
            handle_water_border(world, x+1, y-1, z-1)
            handle_water_border(world, x-1, y-1, z+1)
    if returnBool:
        return False
        

#Misc World Gen
def handle_water_border(world, x, y, z):
    not_ceiling = not is_ceiling(world, x, y, z)
    not_water = not handle_water_pools(world, x, y, z, returnBool = True) and not get_block_wrapper(world, x, y, z) == water
    if not_ceiling and not_water:
        place_single_block(world, sand, x, y, z)
        valid_sugarcane_location = get_block_wrapper(world, x, y+1, z) == air
        if valid_sugarcane_location and random.random() < WATER_POOL_SUGARCANE_SPAWN_CHANCE:
            height = random.randrange(1, 3)
            for i in range(height):
                place_single_block(world, sugarcane, x, y+i+1, z)
            

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

def get_proper_ore(y):
    '''
    We choose a random ore, and then adjust the size based on it's depth. (level of difficulty)

    For example, if an ore appears at normalized depth of 0.5, and the ores dictionary specifies a depth of 0.4, the ore will be rewarded with a larger size.
    '''
    global ores, SQUARE_MAX
    ore, diff = random.choice(ores)
    ideal_diff = 1-map(y, 0, SQUARE_MAX, 0, 1)
    if ideal_diff > diff:
        size = ORE_POCKET_SIZE*((1+abs(ideal_diff-diff))**2)
    else:
        size = ORE_POCKET_SIZE*(1-abs(ideal_diff-diff))
    return ore, int(size)
    
def place_ore(world, x, y, z):
    '''
    We place a random ore vein centered at (x, y, z) 
    '''
    ore, size = get_proper_ore(y)
    if size == 0:
        return
    elif size == 1:
        place_single_block(world, ore, x, y, z)
    else:
        for i in range(size):
            place_x = clamp(x+random.randrange(-1*int((i)/2), 1+int((i)/2)), 0, SQUARE_MAX)
            place_y = clamp(y+random.randrange(-1*int((i)/2), 1+int((i)/2)), 0, SQUARE_MAX)
            place_z = clamp(z+random.randrange(-1*int((i)/2), 1+int((i)/2)), 0, SQUARE_MAX)
            place_single_block(world, ore, place_x, place_y, place_z)

def get_mob(y):
    '''
    Get proper mob, depending on height.
    '''

    normalized_y = 1-map(y, 0, SQUARE_MAX, 0, 1)

    #First, we choose the mob.
    normal_hostile_mobs = ['minecraft:witch', 'minecraft:skeleton', 'minecraft:slime', 'minecraft:creeper', 'minecraft:zombie', 'minecraft:enderman', 'minecraft:spider']
    esoteric_hostile_mobs = ['minecraft:blaze', 'minecraft:magma_cube', 'minecraft:evoker', 'minecraft:vindicator', 'minecraft:wither_skeleton']
    if normalized_y < 0.5:
        mobName = random.choice(normal_hostile_mobs)
    else:
        mobName = random.choice(normal_hostile_mobs+esoteric_hostile_mobs)
    mob = Mob(mobName)

    #Next, we choose the armor and weapons
    armor_materials = ['leather', 'chainmail', 'iron', 'golden', 'diamond']
    weapon_materials = ['wooden', 'stone', 'iron', 'golden', 'diamond']
    can_wear_armor = mobName in ['minecraft:zombie', "mincraft:skeleton"]
    if random.random() < normalized_y and can_wear_armor:
        mob.helmet("minecraft:"+choose_random_weighted(normalized_y, 0.2, armor_materials)+"_helmet", drop_chance = 0.5)
    if random.random() < normalized_y and can_wear_armor:
        mob.chestplate("minecraft:"+choose_random_weighted(normalized_y, 0.2, armor_materials)+"_chestplate", drop_chance = 0.5)
    if random.random() < normalized_y and can_wear_armor:
        mob.leggings("minecraft:"+choose_random_weighted(normalized_y, 0.2, armor_materials)+"_leggings", drop_chance = 0.5)
    if random.random() < normalized_y and can_wear_armor:
        mob.boots("minecraft:"+choose_random_weighted(normalized_y, 0.2, armor_materials)+"_boots", drop_chance = 0.5)
    if random.random() < normalized_y and mobName == "minecraft:zombie":
        #We always want skeleton's weapon to be bow
        mob.right_hand("minecraft:"+choose_random_weighted(normalized_y, 0.2, armor_materials)+"_sword", drop_chance = 0.5)
    
    #Next, we choose effect(s)
    if random.random() < normalized_y:
        number_of_effects = math.floor(5*random.random()*normalized_y)
        effects = random.choices(mob_buffs)
        for i in effects:
            _amplifier = math.floor(5*random.random()*normalized_y)
            mob.effect(i, amplifier = _amplifier)
        
    #We are done.
    return mob

def get_biome(x, y, z, seed = SEED*3):
    '''
    Returns:
    0 for stone
    1 for organic
    '''
    return perlin_probability_selection(1, x, y, z, seed = seed)

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

def scanline_pool_fill(world, sx, sy, sz, block, left_to_right = None):
    '''
    Assume we start at edge.
    '''
    if left_to_right == None:
        scanline_pool_fill(world, sx, sy, sz, block, left_to_right = True)
        scanline_pool_fill(world, sx, sy, sz, block, left_to_right = False)

    first = True

    stack = [(sx, sy, sz)]
    up_empty = False
    dn_empty = False

    while stack != []:
        x, y, z = stack[-1]
        stack = stack[:-1]
        up_empty = False
        dn_empty = False
        while True:
            try:
                if x > SQUARE_MAX or x < 0 or y > SQUARE_MAX or y < 0 or z > SQUARE_MAX or z < 0 or (get_block_wrapper(world, x, y, z) != air and not first):
                    break
            except ChunkDoesNotExist:
                print(f"{x, y, z} caused an EPIC FAIL!")
                break
                
            if not up_empty and get_block_wrapper(world, x+1, y, z) == air:
                up_empty = True
                stack.append((x+1, y, z))
            elif not dn_empty and get_block_wrapper(world,x-1, y, z) == air:
                dn_empty = True
                stack.append((x-1, y, z))
            elif up_empty and get_block_wrapper(world,x+1, y, z) != air:
                up_empty = False
            elif dn_empty and get_block_wrapper(world,x-1, y, z) != air:
                dn_empty = False
            
            place_single_block(world, block, x, y, z)
            
            alter_y = y-1
            while True:
                if get_block_wrapper(world,x, alter_y, z) != air or alter_y < 0:
                    break
                else:
                    place_single_block(world, block, x, alter_y, z)
                    alter_y-=1 
            
            first = False

            if left_to_right:
                z-=1
            else:
                z+=1

def create_bush(world, x, y, z, log, leaf, current_distance, maximum_distance):
    if (get_block_wrapper(world, x, y, z) != air and current_distance != 0) or current_distance >= maximum_distance:
        return
    if (x<0) or (x>SQUARE_MAX) or (y<0) or (y>SQUARE_MAX) or (z<0) or (z>SQUARE_MAX):
        return

    normalized_distance = map(current_distance, 0, maximum_distance, 0, 1)

    if random.random() < normalized_distance: #Early breakoffs
        return

    if random.random() < normalized_distance:
        if BUSH_MELONS and random.random() < BUSH_MELON_SPAWN_CHANCE:
            block = melon
        else:
            block = leaf
    else:
        block = log
    
    place_single_block(world, block, x, y, z)
    create_bush(world, x-1, y, z, log, leaf, current_distance+1, maximum_distance)
    create_bush(world, x+1, y, z, log, leaf, current_distance+1, maximum_distance)
    create_bush(world, x, y-1, z, log, leaf, current_distance+1, maximum_distance)
    create_bush(world, x, y+1, z, log, leaf, current_distance+1, maximum_distance)
    create_bush(world, x, y, z-1, log, leaf, current_distance+1, maximum_distance)
    create_bush(world, x, y, z+1, log, leaf, current_distance+1, maximum_distance)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the DwarfCraft world generator")
    parser.add_argument("world_path", help="Path of the world.")
    parser.add_argument("--size", default = SQUARE_MAX, type=int, help="Size of generated area")
    args = parser.parse_args()
    PATH = args.world_path
    SQUARE_MAX = args.size
    print(SQUARE_MAX)
    program_start = time.time()

    subbox = SubSelectionBox(min, max)
    target_area = Selection([subbox])

    start = time.time()
    print("LOADING WORLD...")
    world = World(PATH, world_interface.load_format(PATH))
    print(f"DONE in {time.time()-start}s")

    if FULL_RESET:
        big_max = (SQUARE_MAX, 255, SQUARE_MAX)
        big_target_area = Selection([SubSelectionBox(min, big_max)])
        fill.fill(world, 0, big_target_area, {'fill_block': air})

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
                handle_glowstone_clusters(world, x, y, z)
            if LAVA_POOLS:
                handle_lava_pools(world, x, y, z)
            if MOB_SPAWNERS:
                handle_mob_spawners(world, x, y, z, MOB_SPAWNER_SPAWN_CHANCE)
            if BUSHES:
                handle_bushes(world, x, y, z)
            if BIOMES:
                handle_biomes(world, x, y, z)
            if WATER_POOLS:
                handle_water_pools(world, x, y, z)

    print(f"DONE in {time.time()-start}s.")
    
    print(f"ALL DONE in {time.time()-program_start}")

    world.save()
    world.close()
