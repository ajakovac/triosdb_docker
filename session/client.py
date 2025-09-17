import re
import json
from asteval import Interpreter
from session.connector import DatabaseConnector

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.utilities import *
from utils.triplets import *

from configs.logging_config import setup_logger
logger = setup_logger(__file__)

class DataClient:
    def __init__(self):
        self.server = DatabaseConnector()
        self.eval = Interpreter()
        self.eval.symtable['data'] = self.server.get
        def isnumber(x):
            try:
                float(x)
                return True
            except ValueError:
                return  False
        self.eval.symtable['isnumber'] = isnumber

    def __contains__(self, name):
        return self.server.exists(name)

    def new(self, name, module, permitted = ['_all']):
        """
            Creates a new name in the given module.
            - *name*: name of the node to create
            - *module*: module where the name belongs
            - *permitted*: allowed modules, if contains '_all', all modules are allowed
            Returns: number of added nodes
        """
        if ':' in name or ',' in name or ';' in name:
            logger.error(f'DataClient new: invalid name "{name}"')
            return 0
        if '_all' not in permitted and module not in permitted:
            logger.error('DataClient new: not authorized')
            return 0
        if self.server.exists(name):
            return 0
        self.server.start_command('client new')
        # to be sure that 'module' is a module
        self.server.set(module, '_member')
        self.server.set(f'{module}:_member', module)

        # add the name to the module
        self.server.set(f'{module}:_member', name)
        self.server.set(name, '_belongs_to')
        self.server.set(f'{name}:_belongs_to', module)
        return 1

    def is_module(self, name:str):
        if '_member' in self.server.get(name):
            return True
        return False

    def in_module(self, name, module):
        return module in self.server.get(f'{name}:_belongs_to')

    def in_modules(self, name, modules):
        if modules is None:
            return True
        for module in modules:
            if self.in_module(name, module):
                return True
        return False

    def members(self, module:str):
        return self.server.get(f'{module}:_member')
    
    def are_friends(self, target_name, name):
        """
            Checks if any of the modules is a friend of name; 
            if so, names belonging to all of the given modules can appear as a property or value of name2
            Returns: True if they are friends, False otherwise
        """
        if not self.server.exists(name) or not self.server.exists(target_name):
            return False
        modules = self.server.get(f'{name}:_belongs_to')
        target_friends = self.server.get(f'{target_name}:_friend') + self.server.get(f'{target_name}:_belongs_to')
        return len(set(modules) & set(target_friends)) > 0

    ##############################################################x
    # The basic get-set-delete definitions 
    ##############################################################x

    def get(self, triplet, recursion_level=0, permitted = ['_all']) ->TripletSet:
        """
            Basic getter.
            The meaning of arguments:
            - *triplet*: triplet (Triplet-izable entry)->name, property, value
            - *recursion_level*: number of allowed recursions, negative value means infinite allowed recursion
            - *permitted*: allowed modules, if contains '_all', all modules are allowed

            Wildcarding allowed using '*'. Its meaning:
            - in name: all possible names are considered
            - in property: all properties of a name is considered
            - in value: all values in name:property is allowed

            Returns: set of valid triplets
        """
        if is_iterable(triplet):
            name, property, value = Triplet(*triplet)
        else:
            name, property, value = Triplet(triplet)
        name_set      = {n.strip() for n in name.split(',')}
        property_list = dict.fromkeys([p.strip() for p in property.split(',')])
        value_list    = dict.fromkeys([v.strip() for v in value.split(',')])

        if '*' in name_set:
            name_set.update([ key for key in self.server.keys('*') if ':' not in key])
            name_set.discard('*')
        elif '_header' not in property_list:
            name_set_add = self.get(f'{",".join(name_set)}:_header,_alias,_member:*', recursion_level=-1).select_fields(value=True)
            name_set.update(name_set_add)
        else:
            property_list.pop('_header')
            if len(property_list)==0:
                property_list='*'

        if '_all' not in permitted:
            name_set = {n for n in name_set if self.in_modules(n, permitted)}

        result = self.simple_get(name_set, property_list, value_list)
        while recursion_level!=0:
            recursion_level-=1
            new_names = name_set | { n  for n in result.select_fields(name=True, property=True, value=True) if n in self}
            if '_all' not in permitted:
                new_names = {n for n in name_set if self.in_modules(n, permitted)}
            if new_names == name_set:
                break
            name_set = new_names
            result = self.simple_get(new_names, property_list, value_list)
        return result

    def simple_get(self, name_set, property_list, value_list) ->TripletSet:        
        result = TripletSet()
        for n in name_set:
            if '*' in property_list:
                p_list = self.server.get(n)
            else:
                p_list = property_list.copy()
            for p in p_list:
                allowed_values = self.server.get(f'{n}:{p}')
                if '*' in value_list:
                    result.update( [Triplet(n,p,v) for v in allowed_values])
                else:
                    result.update( [Triplet(n,p,v) for v in value_list if v in allowed_values] )
        return result

    def __getitem__(self, triplet)  -> TripletSet:
        return self.get(triplet)


    def set(self, triplet, permitted = ['_all']) -> int:
        """
            Basic setter, it adds to the elements of the triplet, not replaces them.
            - *triplet*: triplet to set: name and property must be given, if value='*' then it means value='_property'
            - *permitted*: allowed modules, if contains '_all', all modules are allowed

            - if friends: property:value->name, value:name->property for all value in values

            Returns: number of added nodes
        """
        if is_iterable(triplet):
            name, property, value = Triplet(*triplet)
        else:
            name, property, value = Triplet(triplet)
        name_set      = dict.fromkeys([n.strip() for n in name.split(',')])
        property_list = dict.fromkeys([p.strip() for p in property.split(',')])
        value_list    = dict.fromkeys([v.strip() for v in value.split(',')])

        if '*' in value_list:
            value_list = ['_property']

        if '_all' not in permitted:
            name_set = {n for n in name_set if self.in_modules(n, permitted)}

        self.server.start_command('client set')
        added_nodes = 0

        for name in name_set:
            if not self.server.exists(name):
                logger.warning(f'DataCommand set: name {name} does not exist')
                continue
            for property in property_list:
                if property == '*':
                    logger.warning(f'DataCommand set: property "*" is not allowed')
                    continue
                added_nodes += self.server.set(name, property)
                for value in value_list:
                    if value in ['_member', '_belongs_to']:
                        continue
                    added_nodes += self.server.set(f'{name}:{property}', value)
                    if self.are_friends(property, name):
                        self.server.set(property, value)
                        added_nodes += self.server.set(f'{property}:{value}', name)                            
                    if self.are_friends(value, name):
                        self.server.set(value, name)
                        added_nodes += self.server.set(f'{value}:{name}',property) 
        return added_nodes

    def delete(self, triplet, permitted = ['_all']) -> int:
        """
            Basic delete.
            - *triplet*: triplet to delete: name must be given, 
                - if property='*', the node is deleted
                - if value='*' then all the property is depeted
            - *permitted*: allowed modules, if contains '_all', all modules are allowed

            - if friends: property:value->name, value:name->property for all value in values

            Returns: number of deleted nodes
        """
        if '_all' not in permitted:
            name_set = {n for n in name_set if self.in_modules(n, permitted)}

        self.server.start_command('client delete')
        deleted_nodes=0

        triplets_to_delete = self.get(triplet=triplet, permitted=permitted)
        for name, property, value in triplets_to_delete._items.copy():
            if self.are_friends(property, name):
                triplets_to_delete.update([Triplet(property, value, name)])
            if self.are_friends(value, name):
                triplets_to_delete.update([Triplet(value, name, property)])
        for name, property, value in triplets_to_delete:
            if property == '_belongs_to':
                deleted_nodes += self.server.delete(f'{value}:_member', name)
            deleted_nodes += self.server.delete(f'{name}:{property}', value)
            if not self.server.exists(f'{name}:{property}'):
                deleted_nodes += self.server.delete(name, property)
        return deleted_nodes

    ###############################################################
    # additional methods for triplet sets
    ###############################################################

    def rebuild(self, triplets, permitted = ['_all']):
        """
            Rebuilds the database from the given triplets, creating friendly connections.
            - *triplets*: list of triplets to set
            Returns: number of added nodes
        """
        added_nodes = 0
        for triplet in triplets:
            added_nodes += self.set(triplet, permitted)
        return added_nodes

    def save(self, triplets, filename, delete=True, permitted = ['_all']):
        """
            Archives the given triplets to a file.
            - *triplets*: list of triplets to save
            - *filename*: name of the file to save the triplets, relative to the database path
              if extension is not given, '.json' is added
            Returns: number of added nodes  
        """
        path = self.server.path()
        if not filename.endswith('.json'):
            filename += '.json'
        tosave = TripletSet()
        for triplet in TripletSet(triplets):
            tosave.update(self.get(triplet, permitted=permitted))
        with open(os.path.join(path, filename), 'w') as f:
            print(str(tosave).replace("'",'"'), file=f)
            logger.info(f"DataClient save: {filename} is saved")
        if delete:
            self.delete(triplet, permitted=permitted)
        return len(tosave)

    def load(self, filename, module, permitted = ['_all']):
        if '_all' not in permitted and not self.in_modules(module, permitted):
            logger.error(f'DataClient load: not authorized to write into {module}')
            return 0
        path = self.server.path()
        if not filename.endswith('.json'):
            filename += '.json'
        with open(os.path.join(path, filename)) as f:
            data = json.load(f)
        return self.load_from_json(data, module, permitted=permitted)
    
    def load_from_json(self, data, module, permitted = ['_all']):
        """
            Loads the given data into the database.
            - *data*: dictionary of triplets to load
            - *module*: name of the module to load the data into
            Returns: number of added nodes
        """
        added_nodes = 0
        for name, element in data.items():
            added_nodes += self.new(name, module)
            for property, values in element.items():
                added_nodes += self.set(f'{name}:{property}:' + ','.join(values), permitted=permitted)
        return added_nodes
    
    def to_execute(self, command):
        def my_execute(x,y,z):
            resp = self.eval(command.replace("name", f"{x}")
                    .replace("property", f"{y}")
                    .replace("value", f"{z}")
                    .replace("triplet", f"{x}:{y}:{z}")
            )
            if not self.eval.error:
                return resp
            else:
                raise ValueError(f"Error in command '{command}': {self.eval.error_msg}")
        return my_execute      

    def transform_by_function(self, triplets, function):
        return TripletSet([y for t in triplets if (y:=function(*t)) is not None])

    def transform(self, triplets, command):
        return self.transform_by_function(triplets, self.to_execute(command))
    
    def filter(self, triplets, command):
        command_function = self.to_execute(command)
        return TripletSet([t for t in triplets if command_function(*t)])