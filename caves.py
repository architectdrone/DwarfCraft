'''
The populate function populates a region with caves.
'''

from amulet import world_interface
from amulet.api.selection import *
from amulet.api.block import *
from amulet.operations import fill
from amulet.api.world import *
from noise import pnoise3, pnoise1
import random
import math
PATH = "C:\\Users\\Owen Mellema\\AppData\\Roaming\\.minecraft\\saves\\FUN"


def cave_section(center, width):
    #Right now, just a cube
    c_x = center[0]
    c_y = center[1]
    c_z = center[2]
    l_x = c_x-int((width/2))
    l_y = c_y-int((width/2))
    l_z = c_z-int((width/2))
    min = (l_x, l_y, l_z)
    max = (l_x+width, l_y+width, l_z+width)
    return Selection([SubSelectionBox(min, max)])

def strict_sigmoid(input, clamp):
    #returns -1 if input < -clamp
    #returns 1 if input > clamp
    #else, returns 0
    if (input < -1*clamp):
        return -1
    elif (input > clamp):
        return 1
    else:
        return 0

def scale(input, input_lo, input_hi, output_lo, output_hi):
    return (((input - input_lo) * (output_hi - output_lo)) / (input_hi - input_lo)) + output_lo

def shift(input, mod):
    #If input = 1 or -1,
    #   and mod = input, return input
    #   and mod = -1*input, return 0
    #   and mod = 0, return input
    #Else, return mod
    if (abs(input) == 1):
        if input == mod:
            return input
        elif input == -1*mod:
            return 0
        else:
            return input
    else:
        return mod

def shift_vector(input, mod):
    return (shift(input[0], mod[0]), shift(input[1], mod[1]), shift(input[2], mod[2]))

def add_vectors(input1, input2):
    return (input1[0]+input2[0], input1[1]+input2[1], input1[2]+input2[2])

def make_cave(world, region, start, iterations, min_width, max_width, block):
    for i in region.subboxes:
        MIN_X = i.min_x
        MIN_Y = i.min_y
        MIN_Z = i.min_z
        MAX_X = i.max_x
        MAX_Y = i.max_y
        MAX_Z = i.max_z

    position = start
    vector = (1, 0, 0)
    width = int(min_width+((max_width-min_width)/2))
    for i in range(iterations):
        px = random.choice([-1, 0, 1]) #pnoise1(i/1000, octaves = 3)
        py = random.choice([-1, 0, 1]) #pnoise1(px, octaves = 3)
        pz = random.choice([-1, 0, 1]) #pnoise1(py, octaves = 3)
        width+=random.choice([-1, 0, 1])
        if width < min_width:
            width = min_width
        elif width > max_width:
            width = max_width
        
        #mod = (strict_sigmoid(px-0.5, clamp), strict_sigmoid(py-0.5, clamp), strict_sigmoid(pz-0.5, clamp))
        mod = (px, py, pz)
        vector = shift_vector(vector, mod)
        position = add_vectors(position, vector)

        section = cave_section(position, width)
        stop = False
        for i in section.subboxes:
            if i.min_x < MIN_X or i.min_y < 0 or i.min_z < MIN_Z:
                stop = True
            if i.max_x > MAX_X or i.max_y > 255 or i.max_z > MAX_Z:
                stop = True
        if stop:
            #print("OUT OF BOUNDS")
            break

        fill.fill(world, 0, section, {'fill_block': block})
        #print(F"I: {i} POS: {position} VEC: {vector} WIDTH: {width} MOD: {mod} PX: {px} PY: {py} PZ: {pz}")
    #print("END OF ITERATION")

def clamp(number, low, high):
    if number < low:
        return low
    elif number > high:
        return high
    else:
        return number

def populate(world, region, block, fill_cube_size = 32, min_width = 2, max_width = 10, iterations = 1000):
    '''
    Populates a region with caves.
    world - The world to do this replacing in.
    region - A Selection specifying the region to place the caves in. Should be a single sub box!
    block - The block to fill the caves with. Air, usually.
    fill_cube_size - Make sure at least one cave is in each cube with this dimension in the region.
    min_width - Minumum width of a cave.
    max_width - Maximum width of a cave.
    iterations - Essentially, how long a cave can get.
    '''
    for i in region.subboxes:
        MIN_X = i.min_x
        MIN_Y = i.min_y
        MIN_Z = i.min_z
        MAX_X = i.max_x
        MAX_Y = i.max_y
        MAX_Z = i.max_z

    FILL_CUBE_SIZE = fill_cube_size
    for x_i in range(int(math.ceil((MAX_X-MIN_X)/FILL_CUBE_SIZE))):
        x_lo = clamp(MIN_X+x_i*FILL_CUBE_SIZE, MIN_X, MAX_X)
        x_hi = clamp(x_lo+FILL_CUBE_SIZE, MIN_X, MAX_X)
        for y_i in range(int(math.ceil((MAX_Y-MIN_Y)/FILL_CUBE_SIZE))):
            y_lo = clamp(MIN_Y+y_i*FILL_CUBE_SIZE, MIN_Y, MAX_Y)
            y_hi = clamp(y_lo+FILL_CUBE_SIZE, MIN_Y, MAX_Y)
            for z_i in range(int(math.ceil((MAX_Z-MIN_Z)/FILL_CUBE_SIZE))):
                z_lo = clamp(MIN_Z+z_i*FILL_CUBE_SIZE, MIN_Z, MAX_Z)
                z_hi = clamp(z_lo+FILL_CUBE_SIZE, MIN_Z, MAX_Z)

                start = (random.randrange(x_lo, x_hi), random.randrange(y_lo, y_hi), random.randrange(z_lo, z_hi))
                min_width_specific = random.randrange(min_width,max_width)
                max_width_specific = random.randrange(min_width_specific, max_width)
                #print(f"({x_i}, {y_i}, {z_i}) MAKING A CAVE AT {start}. WIDTH: {min_width_specific}-{max_width_specific}. MAX_LENGTH: {iterations}")
                make_cave(world,region,start,iterations, min_width_specific, max_width_specific, block)

if __name__ == "__main__":
    #Create world object
    new_horizons = world_interface.load_format(PATH)
    print(f"NAME: {new_horizons.world_name}")
    print(f"VERSION: {new_horizons.game_version_string}")
    world = World(PATH, new_horizons)

    stone = blockstate_to_block("stone")
    

    #Fill area with stone
    print("STONIFICATION...")
    min_coord = (0, 0, 0)
    max_coord = (32, 32, 32)
    target_area = Selection([SubSelectionBox(min_coord, max_coord)])
    fill.fill(world, 0, target_area, {'fill_block': stone})

    print("CAVIFICATION...")
    air = blockstate_to_block("air")
    populate(world, target_area, air, fill_cube_size = 16)

    world.save()
    world.close()