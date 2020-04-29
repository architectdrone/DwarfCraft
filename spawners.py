from util import place_single_block

from amulet.api.block import *
from amulet.api.block_entity import BlockEntity
from amulet_nbt import *

from amulet import world_interface
from amulet.api.world import *

def spawner(world, x, y, z, mob):
    '''
    Creates a spawner at (x, y, z), makes it spawn mob.
    '''

    if type(mob) is str:
        #Convert to spawndata.
        spawner(world, x, y, z, {'id': mob})
        return
    if type(mob) is Mob:
        mob = mob.mob_dict

    place_single_block(world, blockstate_to_block("universal_minecraft:spawner"), x, y, z)

    cx = int(x/16)
    cz = int(z/16)
    # ox = x-(cx*16)
    # oy = y
    # oz = z-(cz*16)
    ox = x
    oy = y
    oz = z

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
            'EntityIdentifier':mob['id'],
            'SpawnData': mob,
            'SpawnPotentials': [{'Entity': mob, 'Weight': 1}]
        }
    }
    spawner = BlockEntity("universal_minecraft","spawner",ox,oy,oz, NBTFile(to_nbt(spawner_nbt)))
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
    else:
        print(f"Excuse me, but you failed! {type(data)}")

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

#Helpers
class Mob():
    '''
    Represents a single mob
    '''
    def __init__(self, id):
        self.mob_dict = {'id': id}
    
    def _set_hand(self, hand_id, data, tag, drop_chance):
        if type(data) is str:
            item = {'Count':Byte(1), 'id': data}
        else:
            item = data
        
        if tag:
            item['tag'] = tag
        
        if 'HandItems' in self.mob_dict:
            self.mob_dict['HandItems'][hand_id] = item
        else:
            self.mob_dict['HandItems'] = [{},{}]
            self.mob_dict['HandItems'][hand_id] = item
        
        if drop_chance:
            if 'HandDropChances' in self.mob_dict:
                self.mob_dict['HandDropChances'][hand_id] = drop_chance
            else:
                self.mob_dict['HandDropChances'] = [0.0, 0.0]
                self.mob_dict['HandDropChances'][hand_id] = drop_chance

    def _set_armor(self, slot_id, data, tag, drop_chance):
        item = data
        if type(data) is str:
            item = {}
            item['id'] = data
            item['Count'] = Byte(1)
            if tag:
                item['tag'] = tag
        
        if 'ArmorItems' in self.mob_dict:
            self.mob_dict['ArmorItems'][slot_id] = item
        else:
            self.mob_dict['ArmorItems'] = [{}, {}, {}, {}]
            self.mob_dict['ArmorItems'][slot_id] = item
        
        if drop_chance:
            if 'ArmorDropChances' in self.mob_dict:
                self.mob_dict['ArmorDropChances'][slot_id] = drop_chance
            else:
                self.mob_dict['ArmorDropChances'] = [0.0, 0.0, 0.0, 0.0]
                self.mob_dict['ArmorDropChances'][slot_id] = drop_chance
        
    def helmet(self, data, tag = None, drop_chance = None):
        self._set_armor(3, data, tag, drop_chance)

    def chestplate(self, data, tag = None, drop_chance = None):
        self._set_armor(2, data, tag, drop_chance)

    def leggings(self, data, tag = None, drop_chance = None):
        self._set_armor(1, data, tag, drop_chance)
    
    def boots(self, data, tag = None, drop_chance = None):
        self._set_armor(0, data, tag, drop_chance)

    def right_hand(self, data, tag = None, drop_chance = None):
        self._set_hand(0, data, tag, drop_chance)
    
    def left_hand(self, data, tag = None, drop_chance = None):
        self._set_hand(1, data, tag, drop_chance)
    
    def effect(self, data, amplifier = None, duration = None):
        item = data
        if type(data) is int:
            item = {}
            item['Id'] = Byte(data)
            if amplifier:
                item['Amplifier'] = Byte(amplifier)
            else:
                item['Amplifier'] = Byte(0)
            
            if duration:
                item['Duration'] = duration
            else:
                item['Duration'] = 999999
        
        if 'ActiveEffects' in self.mob_dict:
            self.mob_dict['ActiveEffects'].append(item)
        else:
            self.mob_dict['ActiveEffects'] = []
            self.mob_dict['ActiveEffects'].append(item)
          
    def name(self, name):
        self.mob_dict['CustomName'] = name

#Definitions
speed = 1
slowness = 2
haste = 3
mining_fatigue = 4
strength = 5
instant_health = 6
instant_damage = 7
jump_boost = 8
nausea=9
regeneration=10
resistance=11
fire_resistance=12
water_breathing=13
invisibility=14
blindness=15
night_vision=16
hunger=17
weakness=18
poison=19
wither=20
health_boost=21
absorption=22
saturation=23
glowing=24
levitation=25
luck=26
unluck=27
slow_falling=28
conduit_power=29
dolphins_grace=30
bad_omen=31
hero_of_the_village=32

mob_buffs = [speed, strength, regeneration, resistance, invisibility]
