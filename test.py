from amulet import world_interface
from amulet.api.selection import *
from amulet.api.block import *
from amulet.operations import fill
from amulet.api.world import *

#Create world object
path = "C:\\Users\\Owen Mellema\\AppData\\Roaming\\.minecraft\\saves\\New Horizons"
new_horizons = world_interface.load_format(path)
print(f"NAME: {new_horizons.world_name}")
print(f"VERSION: {new_horizons.game_version_string}")
print(type(new_horizons))
world = World(path, new_horizons)

#Create selection in that world
min_point = (0, 0, 0)
max_point = (1, 255, 256)
subselection = SubSelectionBox(max_point, min_point)
selection = Selection([subselection])

#Define a block
diamond = blockstate_to_block("diamond_block")

#Okay, let's see if this works.
print(world.changed)
fill.fill(world, 0, selection, {'fill_block':diamond})
print(world.changed)
world.save()
world.close()

