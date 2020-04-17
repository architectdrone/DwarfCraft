from amulet.api.selection import *
#from amulet.api.world import *
from amulet.api.block import *
from amulet.operations import fill
from amulet.api.chunk import Chunk
from amulet.api.errors import ChunkDoesNotExist
import math
import time

def map(value, leftMin, leftMax, rightMin, rightMax):
    #From stack overflow: https://stackoverflow.com/questions/1969240/mapping-a-range-of-values-to-another
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - leftMin) / float(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return rightMin + (valueScaled * rightSpan)

def clamp(number, lo, hi):
    if (number < lo):
        return lo
    elif (number > hi):
        return hi
    else:
        return number

def get_single_block(x,y,z):
    lo = (x,y,z)
    hi = (x+1,y+1,z+1)
    return SubSelectionBox(lo, hi)

def place_single_block(world, block, x, y, z):
    fill.fill(world, 0, get_single_block(x, y, z), {'fill_block':block})

def get_block_wrapper(world, x, y, z):
    '''
    Wrapper around world.get_block that loads a chunk if the chunk does not exist, eliminating the dreaded "ChunkDoesNotExist" message
    '''
    try:
        return world.get_block(x, y, z)
    except ChunkDoesNotExist:
        c_x = math.floor(x/16)
        c_z = math.floor(z/16)
        chunk = Chunk(c_x, c_z)
        world.put_chunk(chunk, 0)
        return world.get_block(x, y, z)

def line_y(start_x, start_y, start_z, length, up):
    if (up):
        lo = (start_x, start_y, start_z)
        hi = (start_x+1, start_y+length, start_z+1)
        return SubSelectionBox(lo, hi)
    else:
        lo = (start_x+1, start_y-length+1, start_z+1)
        hi = (start_x, start_y+1, start_z)
        return SubSelectionBox(lo, hi)

def get_positions_in_sub_box(sub_box):
    for x_i in range(sub_box.max_x - sub_box.min_x):
        for y_i in range(sub_box.max_y - sub_box.min_y):
            for z_i in range(sub_box.max_z - sub_box.min_z):
                x = sub_box.min_x+x_i
                y = sub_box.min_y+y_i
                z = sub_box.min_z+z_i
                yield x, y, z

if __name__ == "__main__":
    for x, y, z in get_positions_in_sub_box(line_y(1,2,3,4,True)):
        print(x, y, z)