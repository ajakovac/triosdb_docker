from __future__ import annotations

import time
import subprocess
import psutil
import redis
import re
import socket
import json

import shutil
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from configs.logging_config import setup_logger
logger = setup_logger(__file__)

def get_redis_rdb_path(host, port, password=None):
    try:
        r = redis.Redis(host=host, port=port, password=password)
        dir_config = r.config_get('dir')
        file_config = r.config_get('dbfilename')
        
        redis_dir = dir_config.get('dir')
        db_file = file_config.get('dbfilename')
        
        if redis_dir and db_file:
            return redis_dir, db_file
        else:
            logger.error("Could not retrieve dir/dbfilename from config.")
            return None
    except redis.exceptions.ConnectionError:
        logger.error(f"Could not connect to Redis at {host}:{port}")
        return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

def find_free_port(start=6380, end=65535, host='127.0.0.1'):
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free ports found in range.")

class DatabaseServer:
    def __init__(self):
        systemdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        config_file = os.path.join( systemdir, "src/configs", "system_config.json")
        with open(config_file) as f:
            config_text = f.read()
        self.config_system = json.loads(config_text.replace('SYSTEM_DIR', systemdir))

    def mounted_path(self):
        path = self.config_system["data_path"]
        if not os.path.exists(path) or not os.path.isdir(path):
            raise FileNotFoundError(f'DataServer config_file: database is not mounted')
        return path

    def get_connection(self):
        path = self.mounted_path()
        if not os.path.exists(os.path.join(path,"status.json")):
            logger.warning(f'DataServer get_connection: database was not mounted properly, reseting')
            self.save_status()
            return None, None
        with open(os.path.join(path,"status.json")) as f:
            DBstatus = json.load(f)
        host,port = None,None
        if DBstatus["connection"] is not None:
            host, port = DBstatus["connection"]
            try:
                self.get_client(host, port)
            except:
                logger.warning(f'DataServer get_connection: database was not closed properly, reseting')
                self.save_status()
                host,port = None,None
        return host,port

    def get_client(self, host=None, port=None):
        if host is None or port is None:
            host, port = self.get_connection()
        r = redis.StrictRedis(host=host, port=port, decode_responses=True)
        r.ping()
        return r

    def redis_config_data(self, keys=None):
        if keys is None:
            keys = sorted([
                'daemonize',
                'bind',
                'port',
                'dir',
                'dbfilename',
                'appendfilename',
                'logfile',
                'appendonly',
                'appendfsync',
                'maxmemory',
                'maxclients',
                'loglevel',
                'save'
            ])
        redis_client = self.get_client()
        return { x : redis_client.config_get(x) for x in keys}

    def save_status(self, connection=None, pid=None):
        path = self.mounted_path()
        DBstatus = {
            "connection" : connection,
            "pid" : pid
        }
        with open(os.path.join(path,"status.json"),"w") as f:
            print(json.dumps(DBstatus, indent=4), file=f)
        return True

    def start(self):
        path = self.mounted_path()
        host, port = self.get_connection()
        if host is not None:
            logger.info(f'DataServer start: server is already running and sound!')
            return host, port
        else:
            redis_server_path = self.config_system["redis_server_path"]
            redis_config_file = self.config_system["redis_config_file"]
            host              = self.config_system["default_host"]
            port = find_free_port(host=host)
            self.process = subprocess.Popen([redis_server_path,
                                    redis_config_file,
                                    '--daemonize', 'yes',
                                    '--bind', host,
                                    '--port', str(port),
                                    '--dir',  path,
                                    '--dbfilename', 'db_data.rdb',
                                    '--appendfilename', 'db_append.aof',
                                    '--logfile', 'db_logfile.log'
                                    ], 
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info(f"waiting for Redis server to start...")
            time.sleep(self.config_system['redis_wait_time'])
            pid = self.process.pid
            self.save_status((host,port), pid)
            # check connection
            self.get_client()
            return host, port

    def stop(self):
        host, port = self.get_connection()
        if host is None:
            logger.info(f'DataServer stop: server is not running')
            return True        
        try:
            r = self.get_client()
            logger.info(f"waiting for Redis server to stop...")
            r.shutdown()
            self.save_status()
            time.sleep(self.config_system['redis_wait_time'])
            logger.info(f"Stopped Redis server at {host}:{port}")
            return True
        except:
            return False

    def check_redis_processes(self):
        databases = []

        # explore localhost for running redis servers
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            nameOK = proc.info['name'] == 'redis-server' or (proc.info['cmdline'] is not None and 'redis-server' in proc.info['cmdline'])
            if not nameOK:
                continue
            PID = proc.info['pid']
            # Get all inet (IPv4 + IPv6) connections
            connections = proc.net_connections(kind='inet')

            connected_clients=[]
            full_path=None
            for conn in connections:
                local_ip, local_port = conn.laddr
                if conn.raddr:
                    connected_clients.append(conn.raddr)
                else:
                    #this is the server side
                    full_path = get_redis_rdb_path(host=local_ip, port=local_port)
            
            cmdline = [x for x in proc.info['cmdline'] if x]
            databases.append({
                "pid" : PID,
                "cmdline" : cmdline,
                "proc_name" : proc.info['name'],
                "proc_status" : proc.status(),
                "IP address" : local_ip,
                "port" : local_port,
                "connected clients" : connected_clients,
                "database_file" : os.path.join(*full_path),
                "path" : full_path[0],
                "dbfilename" : full_path[1]
            })
            return databases


if __name__ == "__main__":
    try:
        server = DatabaseServer()
        myname = sys.argv.pop(0)
        command = sys.argv.pop(0)
        
        if command == 'show':
            databases = server.check_redis_processes()
            if not databases:
                logger.info("No databases are running")
            else:
                logger.info(json.dumps(databases, indent=4))
            exit(0)

        name = sys.argv.pop(0) if sys.argv else None
        data_dir = sys.argv.pop(0) if sys.argv else None

        if command == 'start':
            server.start(name, data_dir)
        elif command == 'stop':
            server.stop(name, data_dir)
        elif command == 'check':
            host, port = server.get_connection(name, data_dir)
            if host is not None:
                logger.info(f"Server runs at {host}:{port}")
            else:
                logger.info(f"Server is not running")
        else:
            print("Unknown command")
            exit(-1)
    except Exception as e:
        print("Usage:")
        print(f">>  {myname} show|start|stop|check")
        #print(e)
        exit(-1)
