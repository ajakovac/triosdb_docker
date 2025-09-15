
import re
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from session.manager import SessionManager
from src.session.response_model import CommandResponse

from utils.utilities import *
from database.triplets import *
from database.client import DataClient

from configs.logging_config import setup_logger
logger = setup_logger(__file__)

@SessionManager.register("new")
def new_function(**kwargs):
    argument = kwargs["argument"]
    user = kwargs["user"]
    data_client:DataClient = kwargs["data_client"]
    token = kwargs["token"]
    session:SessionManager = kwargs["session"]

    response = CommandResponse(command = "new " + argument)

    permitted = data_client.simple_get([user],['write'],['*']).format('value')
    argument = session.nested_replace(argument, token)
    argument_list=[x.strip() for x in argument.split(';')]
    module = argument_list.pop(0).strip()
    added_nodes = 0
    for name in argument_list:
        added_nodes = data_client.new(name, module, permitted)
    response.message = f'added {added_nodes} new nodes'
    response.success=True
    return response

@SessionManager.register("get")
def get_function(**kwargs):
    argument = kwargs["argument"]
    user = kwargs["user"]
    data_client:DataClient = kwargs["data_client"]
    token = kwargs["token"]
    session:SessionManager = kwargs["session"]

    response = CommandResponse(command = "get " + argument)
    
    permitted = data_client.simple_get([user],['read'],['*']).format('value')
    argument = session.nested_replace(argument, token, item_separator=',', entry_separator=',')
    argument_list=[x.strip() for x in argument.split(';')]
    check_recursive = argument_list[0].split(':')
    recursion_level=0
    if check_recursive.pop(0).strip() == "recursive":
        argument_list.pop(0)
        if len(check_recursive) == 0:
            recursion_level=-1
            logger.info(f'DataCommand get: recursion level is infinity')
            response.message = "recursion level is infinity; "
        else:
            try:
                assert(check_recursive[0].strip()=='level')
                recursion_level = int(check_recursive[1])
                logger.info(f'DataCommand get: recursion level is {recursion_level}')
                response.message = f"recursion level is {recursion_level}; "
            except:
                logger.info(f'DataCommand get: syntax error in recursion level setting')
                response.message = f'syntax error in recursion level setting'
    result_set = TripletSet()
    for arg in argument_list:
        result_set.update(data_client.get(arg, recursion_level=recursion_level, permitted=permitted))    
    response.output=result_set
    response.message += "success"
    response.success=True
    return response


@SessionManager.register("set")
def set_function(**kwargs):
    argument = kwargs["argument"]
    user = kwargs["user"]
    data_client :DataClient = kwargs["data_client"]
    token = kwargs["token"]
    session:SessionManager = kwargs["session"]

    response = CommandResponse(command = "set " + argument)

    permitted = data_client.simple_get([user],['write'],['*']).format('value')

    argument = session.nested_replace(argument, token)
    triplet_list=TripletSet([Triplet(x.strip()) for x in argument.split(';')])
        
    addednodes= 0
    for name,property,value in triplet_list:
        if property=='password' and data_client.in_module(name, 'users'):
            data_client.delete(f'{name}:password', permitted=permitted)
            addednodes += data_client.set(f'{name}:password:{session.pwd_context.hash(value)}')
        else:
            addednodes += data_client.set((name, property, value), permitted=permitted)
    response.message = f"added {addednodes} entries"
    response.success=True
    return response

@SessionManager.register("delete", "del")
def delete_function(**kwargs):
    argument = kwargs["argument"]
    user = kwargs["user"]
    data_client:DataClient = kwargs["data_client"]
    token = kwargs["token"]
    session = kwargs["session"]

    response = CommandResponse(command = "delete " + argument)

    permitted = data_client.simple_get([user],['write'],['*']).format('value')

    argument = session.nested_replace(argument, token)
    triplet_list=TripletSet([Triplet(x.strip()) for x in argument.split(';')])

    deleted_nodes = 0

    for triplet in triplet_list:
        deleted_nodes += data_client.delete(triplet, permitted=permitted)

    response.message = f'{deleted_nodes} entries are deleted'
    response.success = True
    return response


@SessionManager.register("undo")
def undo_function(**kwargs):
    argument = kwargs["argument"]
    session:SessionManager = kwargs["session"]

    response = CommandResponse(command = "undo")
    if argument:
        response.message = 'syntax error'
        return response
    undo_commands = session.system_data_client.server.undo()
    response.message = f'undid {undo_commands} elementary operations'
    response.success = True
    return response

@SessionManager.register("redo")
def redo_function(**kwargs):
    argument = kwargs["argument"]
    session:SessionManager = kwargs["session"]

    response = CommandResponse(command = "redo")
    if argument:
        response.message = 'syntax error'
        return response
    redo_commands = session.system_data_client.server.redo()
    response.message = f'redid {redo_commands} elementary operations'
    response.success = True
    return response
