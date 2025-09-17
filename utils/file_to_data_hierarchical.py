import re
import numpy as np

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from session.client import DataClient
from utils.utilities import RandomName

from configs.logging_config import setup_logger
logger = setup_logger(__file__)

def make_unique_name(data_client:DataClient, name=None, default_extension_length=5, maxtrials=3, separator='.'):
    if name is None:
        name = default_extension_length * '*'
        separator = ''
    m = re.match(r'^(.*?)(\**)$',name)
    if not m:
        logger.debug(f'make_unique_name: Bad name {name}')
        name = default_extension_length * '*'
        separator = ''
    basename = m.group(1)
    extension_length = len(m.group(2))
    if extension_length==0:
        return name
    if extension_length==1:
        extension_length = default_extension_length
    randomname = f'{basename}{separator}{RandomName().generate(length=extension_length)}'
    trials = 0
    while data_client.server.exists(randomname):
        randomname = f'{basename}{separator}{RandomName().generate(length=extension_length)}'
        trials +=1
        if trials==maxtrials:
            extension_length+=1
            trials=0
    return randomname

def process_hierarchy_text(
        data_client:DataClient,
        datamodule:str,
        textlist:list[str],
        parent_name:str|None = None,
        child_name:str|None = None):
    addednodes=0
    create_node_dict = {}
    for q in textlist:
        m = re.match(r'(-*)\s*(.*)$', q)
        if not m:
            logger.warning(f'process_hierarchy_text: invalid entry: {q}')
            continue
        level = len(m.group(1))
        entrylist = [x.strip() for x in m.group(2).split(',')]
        name = entrylist.pop(0)
        if name:
            create_node_dict[name] = [level, entrylist]
    
    for name in create_node_dict:
        addednodes += data_client.new(name, datamodule)
    
    for name in create_node_dict:
        level, entrylist = create_node_dict[name]
        for element in entrylist:
            property, *value = element.split(':')
            if not value:
                value = property.strip()
                property = "_property"
            else:
                property = property.strip()
                value = value[0].strip()
            data_client.set((name, property, value))

    pnodes = []
    for name in create_node_dict:
        level, entrylist = create_node_dict[name]
        while pnodes and level <= pnodes[-1][0]:
            pnodes.pop()
        if pnodes:
            parent = pnodes[-1][1]
            if parent_name: data_client.set((name, parent_name, parent))
            if child_name: data_client.set((parent, child_name, name))
        pnodes.append([level,name])
    return addednodes

def next_line_and_header(textlines:list[str], header={}):
    if not textlines:
        return True, header
    line = textlines.pop(0).strip()
    if not line:
        return next_line_and_header(textlines, header)
    m = re.match(r'^#([^:]+):([^:]+)\s*$', line)
    if not m:
        return False, line
    header[m.group(1).strip()] = m.group(2).strip()
    return True, next_line_and_header(textlines, header)[1]

def list_to_data_hierarchical(data_client, module, textlines:list[str]):
    header={}
    to_process = []
    while textlines:
        found_new_header, line = next_line_and_header(textlines, header)
        if found_new_header and to_process:
            try:
                process_hierarchy_text(
                    data_client=data_client,
                    datamodule = module,
                    textlist=to_process,
                    parent_name = header.get("parent"),
                    child_name = header.get("child")
                )
                logger.info(f'processed {len(to_process)} lines')
                to_process.clear()
            except:
                print(f'please specify module in the text file as #module:NAME')
                exit(-1)
        else:
            to_process.append(line)


def file_to_data_hierarchical(data_client, module, filename: str):
    with open(filename) as f:
        list_to_data_hierarchical(data_client, module, textlines = f.readlines())

if __name__ == "__main__":
    app_name = sys.argv.pop(0)
    delete = False
    databasename=None
    module = None
    filename = None

    while sys.argv:
        command = sys.argv.pop(0)
        if command == '-help':
            print(\
    f"""
    This utility function is for adding a hierarchy format data to a database.
    Usage:
        {app_name} <flags> module hierarchy_data

    The following flags and parameters are allowed:
    '-database' or '-db' : sets the database name; default is None

    At the end the module informes the data server about the change in the user module.
    """)
            continue
        if command == '-database' or command == '-db':
            databasename = sys.argv.pop(0)
            continue
        if command == '-delete':
            delete = True
            continue
        if module is None:
            module = command
            continue
        filename = command

    client = DataClient()

    file_to_data_hierarchical(client, module, filename)
