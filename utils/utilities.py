from datetime import datetime
import numpy as np
from collections.abc import Iterable

def is_iterable(obj):
    if isinstance(obj, (str, bytes)):  # Strings and bytes are iterable, but we treat them as single items
        return False
    return isinstance(obj, Iterable)

def is_float(x):
    try:
        float(x)
        return True
    except:
        return False

def flatten(input):
    if not is_iterable(input):
        return [input]
    result = []
    if type(input)==dict:
        input=input.items()
    for part in input:
        if is_iterable(part):
            result.extend(flatten(part))
        else:
            result.append(part)
    return result

def combine(args):
    if not args:
        return None
    X = [ [xi] for xi in args[0]]
    return _combine(X, args[1:])

def _combine(X,Y):
    if not Y:
        return X
    return _combine( [ x+[y] for x in X for y in Y[0] ], Y[1:] )

def make_iterable(obj):
    if isinstance(obj, (str, bytes)):  # Strings and bytes are iterable, but we treat them as single items
        return [obj]
    if isinstance(obj, Iterable):
        return obj
    return [obj]

def stamp(name):        
    return f'{name}:{datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}'

def to_dict(element):
    result = {}
    for x in element:
        if not is_iterable(x):
            return element
        name, *other = x
        if name not in result:
            result[name] = []
        if len(other)==1:
            result[name].extend(other)
        else:
            result[name].append(other)
    for name, other in result.items():
        result[name]=to_dict(other)
    return result

    
def format_dict(mydict, indent='', tab=4*' ') -> str:
    if type(mydict) != dict:
        return f'{mydict}'
    if len(mydict) == 0:
        return '{--not found--}'
    response = '{\n'
    keylist = sorted(list(mydict.keys()))
    for i in range(len(keylist)):
        key = keylist[i]
        value = mydict[key]
        response += indent + tab + f"'{key}' : {format_dict(value, indent+tab, tab)}"
        if i == len(keylist)-1:
            response += '\n'+ indent + '}'
        else:
            response += ',\n'
    return response

class RandomName:
    vowels = ["a","e","i","o","u","y","-"]
    consonants = ["b","c","d","f","g","h","j","k","l","m","n","p","q","r","s","t","v","w","x","z"]
    letters = vowels + consonants
    Pvc = 0.85
    Pcv = 0.85
    def generate(self, length=10, basename="", seed=None):
        if length == 0:
            return basename
        if seed is not None:
            np.random.seed(seed)
        if not basename:
            basename = np.random.choice(RandomName.letters)
        while len(basename)<length:
            r = np.random.uniform(0,1)
            v = np.random.choice(RandomName.vowels)
            c = np.random.choice(RandomName.consonants)
            if basename[-1] in RandomName.vowels:
                if r<RandomName.Pvc: basename+=c
                else: basename+=v
            else:
                if r<RandomName.Pcv: basename+=v
                else: basename+=c
        basename=basename.strip()
        return basename
