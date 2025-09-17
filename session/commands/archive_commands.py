
import re
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from session.manager import SessionManager
from configs.response_model import CommandResponse

from utils.utilities import *
from utils.triplets import *
from session.client import DataClient

from configs.logging_config import setup_logger
logger = setup_logger(__file__)

@SessionManager.register("save")
def save_function(**kwargs):
    kwargs["delete"] = False
    kwargs["response"] = CommandResponse(command = 'save ' + kwargs['argument'])
    return save_or_archive(**kwargs)

@SessionManager.register("archive")
def save_function(**kwargs):
    kwargs["delete"] = False
    kwargs["response"] = CommandResponse(command = 'archive ' + kwargs['argument'])
    return save_or_archive(**kwargs)

def save_or_archive(**kwargs):
    argument = kwargs["argument"]
    user = kwargs["user"]
    data_client:DataClient = kwargs["data_client"]
    token = kwargs["token"]
    session = kwargs["session"]
    todelete = kwargs["delete"]
    response:CommandResponse = kwargs["response"]

    permitted = data_client.simple_get([user],['write'],['*']).format('value')
    saved_items = 0
    for x in argument.split(';'):
        module = x.strip()
        triplets = data_client.get(module, permitted=permitted)
        saved_items += data_client.save(triplets, module, delete=todelete, permitted=permitted)
    if todelete:
        response.message += f'archived {saved_items} entries'
    else:
        response.message += f'saved {saved_items} entries'
    response.success = True
    return response

@SessionManager.register("load")
def load_function(**kwargs):
    argument = kwargs["argument"]
    user = kwargs["user"]
    data_client:DataClient = kwargs["data_client"]
    token = kwargs["token"]
    session = kwargs["session"]

    response = CommandResponse(command = 'load ' + argument)

    permitted = data_client.simple_get([user],['write'],['*']).format('value')
    argument_list = argument.split(';')
    main_module = argument_list.pop(0).strip()
    if '_all' not in permitted and main_module not in permitted:
        response.message = f'You are not allowed to load into module "{main_module}"'
        response.success = False
        return response
    loaded_items = 0
    for x in argument_list:
        module = x.strip()
        loaded_items += data_client.load(module, main_module, permitted=permitted)
        logger.info(f'{module} is loaded into {main_module}')
    response.message = f'loaded {loaded_items} entries'
    response.success = True
    return response

