from amulet.api.selection import *
#from amulet.api.world import *
from amulet.api.block import *
from amulet.operations import fill
import math
import time

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