'''
Stretches the bottom 128 blocks of a single chunk to 4x it's original size. The result is that each block in the original area is mapped to a "megablock" of 8 blocks.
'''

from amulet import world_interface
from amulet.api.selection import *
from amulet.api.block import *
from amulet.operations import fill
from amulet.api.world import *
PATH = "C:\\Users\\Owen Mellema\\AppData\\Roaming\\.minecraft\\saves\\Newer Horizons"
CX = 16
CY = 1

def fill(world: "World", target_box: Selection, the_id):
    internal_id = the_id

    for chunk, slices, _ in world.get_chunk_slices(target_box, 0, True):
        chunk.blocks[slices] = internal_id
        chunk.changed = True

#Create world object
new_horizons = world_interface.load_format(PATH)
print(f"NAME: {new_horizons.world_name}")
print(f"VERSION: {new_horizons.game_version_string}")
world = World(PATH, new_horizons)

chunk = world.get_chunk(CX, CY, 0)
copy_chunk = chunk.blocks[:, 0:128, :].copy()

stone = blockstate_to_block("stone")
internal_id = world.palette.get_add_block(stone)
print(internal_id)
lo_x = CX*16
lo_y = CY*16
for x in range(16):
    for z in range(128):
        for y in range(16):
            min_point = (lo_x+(2*x), 2*z, lo_y+(2*y))
            max_point = (lo_x+(2*x)+2, (2*z)+2, lo_y+(2*y)+2)
            subselection = SubSelectionBox(max_point, min_point)
            selection = Selection([subselection])
            fill(world, selection, copy_chunk[x,z,y])
            
chunk.changed = True
world.save()
world.close()