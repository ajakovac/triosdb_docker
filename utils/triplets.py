import re
import sys
import os

from utils.utilities import *
from configs.logging_config import setup_logger
logger = setup_logger(__file__)

class Triplet:
    def __init__(self, *args):
        self.data = ['*' ,'*' ,'*']
        for arg in args[::-1]:
            self.data = [x.strip() for x in str(arg).split(':')] + self.data
        self.data = self.data[:3]

    def __iter__(self):
        return iter(self.data)

    def __eq__(self, other):
        if not isinstance(other, Triplet):
            return NotImplemented
        return self.data == other.data

    def __len__(self):
        return 3

    def __hash__(self):
        return hash(':'.join(self.data))

    def __repr__(self):
        return ':'.join(self.data)

class TripletSet:
    def __init__(self, data=None):
        self._items = {}
        if data is not None:
            self.update(data)

    def update(self, data):
        if not is_iterable(data):
            #it is assumed that data consists ;-separated Triplet-izable entities
            data = data.split(';')
        data = [Triplet(x) for x in data]
        self._items.update( dict.fromkeys(data))
        return self

    def add(self, value):
        self._items[Triplet(value)]=None

    def discard(self, value):
        return self._items.pop(value, None)

    def __contains__(self, value):
        return value in self._items

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def __repr__(self):
        return f"TripletSet({list(self._items.keys())})"

    def __eq__(self, other):
        if not isinstance(other, TripletSet):
            return NotImplemented
        return self._items == other._items

    # --- Set operations ---
    def __or__(self, other):
        return TripletSet(self._items | other._items)

    def __and__(self, other):
        return TripletSet(self._items & other._items)

    def __sub__(self, other):
        return TripletSet(self._items - other._items)
        
    def select_fields(self, name=False, property=False, value=False) -> dict:
        result = []
        for x,y,z in self._items:
            if name: result.append(x)
            if property: result.append(y)
            if value: result.append(z)
        return dict.fromkeys(result)
    
    def format(self, format_string):
        result = []
        for x,y,z in self._items:
            newstring = format_string
            newstring = newstring.replace("name",str(x))
            newstring = newstring.replace("property",str(y))
            newstring = newstring.replace("value",str(z))
            result.append(newstring)
        return result
    
    def show(self, format_string='name:property:value'):
        positions=[]
        positions += [ [m.start(),"name"] for m in re.finditer("name", format_string)]
        positions += [ [m.start(),"property"] for m in re.finditer("property", format_string)]
        positions += [ [m.start(),"value"] for m in re.finditer("value", format_string)]
        format_string = ':'.join([ u[1] for u in sorted(positions, key=lambda x:x[0])])
        result_list = []
        for x,y,z in self._items:
            newstring = format_string
            newstring = newstring.replace("name",str(x))
            newstring = newstring.replace("property",str(y))
            newstring = newstring.replace("value",str(z))
            result_list.append(newstring)
        result = []
        for r in result_list:
            U = r.split(':')
            if len(U)<2:
                result.extend(U)
            else:
                result.append(U)
        return to_dict(result)

    def __str__(self):
        return format_dict(to_dict(self._items))

def tripletset_to_sorted_list(tripletset):
    return [ u.__repr__() for u in sorted(tripletset, key=lambda x: x.__repr__())]