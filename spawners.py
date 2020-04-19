from util import place_single_block

from amulet.api.block import *
from amulet.api.block_entity import BlockEntity
from amulet_nbt import *

from amulet import world_interface
from amulet.api.world import *

PATH = "C:\\Users\\Owen Mellema\\AppData\\Roaming\\.minecraft\\saves\\EPIC5"

def spawner(world, x, y, z, mob):
    '''
    Creates a spawner at (x, y, z), makes it spawn mob.
    '''
    place_single_block(world, blockstate_to_block("universal_minecraft:spawner"), x, y, z)

    cx = int(x/16)
    cz = int(x/16)
    ox = x-(cx*16)
    oy = y
    oz = z-(cz*16)

    spawner_chunk = world.get_chunk(cx, cz)
    spawner_nbt = {
        'utags':{
            'isMovable': True,
            'keepPacked': False,
            'MaxNearbyEntities': Short(6),
            'RequiredPlayerRange': Short(16),
            'SpawnCount': Short(4),
            'MaxSpawnDelay':Short(800),
            'Delay':Short(20),
            'SpawnRange':Short(4),
            'MinSpawnDelay':Short(200),
            'DisplayEntityHeight':1.7999999,
            'DisplayEntityScale':1.0,
            'DisplayEntityWidth':0.8,
            'EntityIdentifier':mob,
            'SpawnData': {'id': mob},
            'SpawnPotentials': [{'Entity': {'id': mob}, 'Weight': 1}]
        }
    }
    spawner = BlockEntity("universal_minecraft","spawner",ox,oy,oz, NBTFile(to_nbt(spawner_nbt)))

    # spawner_nbt = NBTFile()
    # spawner_nbt['utags'] = TAG_Compound()

    # spawner_nbt['utags']['isMovable']           = TAG_Byte(1)
    # spawner_nbt['utags']['keepPacked']          = TAG_Byte(0)
    # spawner_nbt['utags']['MaxNearbyEntities']   = TAG_Short(6)
    # spawner_nbt['utags']['RequiredPlayerRange'] = TAG_Short(16)
    # spawner_nbt['utags']['SpawnCount']          = TAG_Short(4)
    # spawner_nbt['utags']['MaxSpawnDelay']       = TAG_Short(800)
    # spawner_nbt['utags']['Delay']               = TAG_Short(20)
    # spawner_nbt['utags']['SpawnRange']          = TAG_Short(4)
    # spawner_nbt['utags']['MinSpawnDelay']       = TAG_Short(200)
    # spawner_nbt['utags']['DisplayEntityHeight'] = TAG_Float(1.7999999)
    # spawner_nbt['utags']['DisplayEntityScale']  = TAG_Float(1)
    # spawner_nbt['utags']['DisplayEntityWidth']  = TAG_Float(0.8)

    # spawner_nbt['utags']['EntityIdentifier'] = TAG_String(mob)
    # spawner_nbt['utags']['SpawnData'] = TAG_Compound({'id': TAG_String(mob)})
    # spawner_nbt['utags']['SpawnPotentials'] = amulet_nbt.TAG_List(
    #     [
    #         TAG_Compound({
    #             "Entity": TAG_Compound({'id': TAG_String(mob)}),
    #             "Weight": TAG_Int(1)
    #         })
    #     ])
    # spawner = BlockEntity("universal_minecraft","spawner",ox,oy,oz, spawner_nbt)

    spawner_chunk.block_entities.insert(spawner)

def to_nbt(data):
    '''
    Returns the NBT form of the given python object.
    '''
    if type(data) is tuple:
        return data[1](data[0])
    elif type(data) is str:
        return TAG_String(data)
    elif type(data) is int:
        return TAG_Int(data)
    elif type(data) is float:
        return TAG_Float(data)
    elif type(data) is bool:
        if data:
            return TAG_Byte(0)
        else:
            return TAG_Byte(1)
    elif type(data) is list:
        return TAG_List([to_nbt(i) for i in data])
    elif type(data) is dict:
        new_dict = {}
        for key in data.keys():
            new_dict[key] = to_nbt(data[key])
        return TAG_Compound(new_dict)
    elif type(data) is Short:
        return TAG_Short(data.num)
    elif type(data) is Long:
        return TAG_Long(data.num)
    elif type(data) is Double:
        return TAG_Double(data.num)
    elif type(data) is Byte:
        return TAG_Byte(data.num)

#Dummy Classes
#Python has some data types that directly correspond to nbt types, but others that don't. We make these dummy classes so that we can easily declare it, and the to_nbt function will know what to do.
class Short():
    def __init__(self, num):
        self.num = num

class Long():
    def __init__(self, num):
        self.num = num

class Double():
    def __init__(self, num):
        self.num = num

class Byte():
    def __init__(self, num):
        self.num = num

if __name__ == "__main__":
    world = World(PATH, world_interface.load_format(PATH))
    spawner(world, 3, 64, 3,"minecraft:zombie")
    world.save()
    world.close()