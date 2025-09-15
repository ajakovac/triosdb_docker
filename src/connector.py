from __future__ import annotations

from collections import deque
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from database.server import DatabaseServer

from configs.logging_config import setup_logger
logger = setup_logger(__file__)

class UndoBuffer:
    def __init__(self, maxlen):
        self.maxlen = maxlen
        self.buffer = []
        self.pos = 0  # shared read/write position: read from self.pos-1, write to self.pos

    def extend(self, values):
        for v in values:
            self.write(v)

    def write(self, value):
        if self.pos == len(self.buffer):
            self.buffer.append(value)
            self.buffer = self.buffer[-self.maxlen:]
            self.pos = len(self.buffer)
        else:
            self.buffer[self.pos] = value
            self.pos += 1
            self.buffer = self.buffer[:self.pos]
    
    def peek(self):
        if self.pos == 0:
            return None
        return self.buffer[self.pos-1]

    def undo(self):
        if self.pos == 0:
            return None
        self.pos -= 1
        return self.buffer[self.pos]

    def redo(self):
        if self.pos == len(self.buffer):
            return None
        self.pos += 1
        return self.buffer[self.pos-1]

    def reset(self):
        self.pos = len(self.buffer)

    def __repr__(self):
        return f"Buffer: {self.buffer}, Position: {self.pos}"


class DatabaseConnector:
    def __init__(self):
        self.server = DatabaseServer()
        try:
            self.client = self.server.get_client()
        except:
            self.server.start()
            self.client = self.server.get_client()
        self.undo_buffer = UndoBuffer(maxlen=self.server.config_system['undo_list_length'])
    
    def path(self):
        return self.server.mounted_path()

    def get(self, key) ->list:
        res = self.client.get(key)
        if res is None:
            return []
        else:
            return res.split(',')

    def set(self, key, value, position=None, unique=True, register=True):
        if self.exists(key):
            entry = self.get(key)
            if unique and value in entry:
                return 0
            if position is None:
                position = len(entry)
            entry.insert(position, str(value))
        else:
            entry = [value]
        if register:
            self.undo_buffer.write(['set', key, value, position])
        return self.client.set(key, ",".join(entry))
    
    def delete(self, key, value=None, register=True):
        if value is None:
            deleted_entries=0
            for value in self.get(key):
                deleted_entries += self._delete(key, value, register)
            return deleted_entries
        return self._delete(key, value, register)

    def _delete(self, key, value, register=True):
        try:
            entry = self.get(key)
            index = entry.index(value)
            del entry[index]
            if register:
                self.undo_buffer.write(['delete', key, value, index])
            if entry:
                self.client.set(key, ",".join(entry))
            else:
                self.client.delete(key)
            return 1
        except ValueError:
            return 0            

    def start_command(self, message='command'):
        if self.undo_buffer.peek() is not None and self.undo_buffer.peek()[0] != 'start':
            self.undo_buffer.write(['start', message])

    def undo(self, until_start=True):
        number_of_undo_operations=0
        while True:
            undo_entry = self.undo_buffer.undo()
            if undo_entry is None or undo_entry[0] == 'start':
                return number_of_undo_operations
            command, key, value, position = undo_entry
            if command == 'set':
                number_of_undo_operations += self.delete(key, value, register=False)
            if command == 'delete':
                number_of_undo_operations += self.set(key, value, position, register=False)
            if not until_start:
                break
        return number_of_undo_operations

    def redo(self, until_start=True):
        number_of_redo_operations=0
        while True:
            redo_entry = self.undo_buffer.redo()
            if redo_entry is None or redo_entry[0] == 'start':
                return number_of_redo_operations
            command, key, value, position = redo_entry
            if command == 'set':
                number_of_redo_operations += self.set(key, value, position, register=False)
            if command == 'delete':
                number_of_redo_operations += self.delete(key, value, register=False)
            if not until_start:
                break
        return number_of_redo_operations

    def exists(self, key):
        return self.client.exists(key)
    
    def keys(self, pattern='*'):
        return self.client.keys(pattern)
    
    def check(self):
        try:
            self.client.ping()
            return True
        except:
            return False
    
    def delete_all(self):
        return self.client.flushdb()
    
    def raw(self, pattern='*'):
        return { x:self.client.get(x) for x in self.client.keys(pattern) }
