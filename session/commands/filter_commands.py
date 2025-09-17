
import re
from asteval import Interpreter
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

@SessionManager.register("yield")
def yield_function(**kwargs):
    argument = kwargs["argument"]
    data_client:DataClient = kwargs["data_client"]
    token = kwargs["token"]
    session:SessionManager = kwargs["session"]

    response = CommandResponse(command = "yield " + argument)

    argument_list=argument.split(';')
    command = argument_list.pop(0).strip()
    argument = session.nested_replace('(' + ';'.join(argument_list) +')', token)
    argument_list= TripletSet(argument)

    try:
        response.output = data_client.transform(argument_list, command)
        response.message += "success"
        response.success=True
        return response
    except Exception as e:  
        logger.error(f"Error in yield: {e}")
        response.message += f"Error: {str(e)}"
        response.success=False
        return response

@SessionManager.register("filter")
def filter_function(**kwargs):
    argument = kwargs["argument"]
    data_client:DataClient = kwargs["data_client"]
    token = kwargs["token"]
    session:SessionManager = kwargs["session"]

    response = CommandResponse(command = "filter " + argument)

    argument_list=argument.split(';')
    command = argument_list.pop(0).strip()
    argument = session.nested_replace('(' + ';'.join(argument_list) +')', token)
    argument_list= TripletSet(argument)

    try:
        response.output = data_client.filter(argument_list, command)
        response.message += "success"
        response.success=True
        return response
    except Exception as e:  
        logger.error(f"Error in transform_function: {e}")
        response.output = TripletSet()
        response.message += f"Error: {str(e)}"
        response.success=False
        return response

@SessionManager.register("choose")
def choose_function(**kwargs):
    argument = kwargs["argument"]
    token = kwargs["token"]
    session:SessionManager = kwargs["session"]

    response = CommandResponse(command = "choose " + argument)

    argument_list=argument.split(';')
    format = argument_list.pop(0)
    choose = ['name' in format, 'property' in format, 'value' in format]
    argument = session.nested_replace('(' + ';'.join(argument_list) +')', token)
    res = {}
    for u in TripletSet(argument):
        res.update(dict.fromkeys(np.array(u.data)[choose]))
    response.output= list(res.keys())
    response.message += "success"
    response.success=True
    return response
