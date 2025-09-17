import jwt
import secrets
from passlib.context import CryptContext
from datetime import datetime
import time

import re
from configs.response_model import CommandResponse

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.utilities import *
from utils.triplets import *
from session.client import DataClient

from configs.logging_config import setup_logger
logger = setup_logger(__file__)

class SessionManager:
    dispatch_table = {}

    @classmethod
    def register(cls, *names):
        def decorator(func):
            actual_names = names or [func.__name__]
            for key in actual_names:
                cls.dispatch_table[key] = func
            return func
        return decorator

    def __init__(self):
        self.system_data_client= DataClient()
        self.login_data = {"system": self.system_data_client}

        # check the necessary header of the database; create if not present
        if not '_system' in self.system_data_client:
            logger.info('install: creating _system module')
            self.system_data_client.new(name='_system', module='_system')
            #'world' is the defaul name
            self.system_data_client.set('_system:name:world')
        
        # setting up the user system
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.system_data_client.new(name='users', module='_system')
        if not self.system_data_client.in_module('user-su','users'):
            password = RandomName().generate(length=10)
            self.system_data_client.new(name='user-su', module='users')
            self.system_data_client.set(f'user-su:password:{self.pwd_context.hash(password)}')
            self.system_data_client.set(f'user-su:read:_all')
            self.system_data_client.set(f'user-su:write:_all')
            self.system_data_client.set(f'user-su:description:Superuser account')
            self.user_expiration_dt('user-su')
            logger.info(f'install: created "su" user with random password {password}; please change it!')
        skey = self.system_data_client.simple_get(['_system'],['SECRET_KEY'],['*']).format('value')
        if skey:
            self.SECRET_KEY = skey[0]
        else:
            logger.debug("No valid SECRET_KEY -- generating")
            self.SECRET_KEY= secrets.token_urlsafe(64)
            self.system_data_client.set(f'_system:SECRET_KEY:{self.SECRET_KEY}')
        self.ALGORITHM = "HS256"
        self.default_expiration_time_delta = 15*60   #15 minutes

    def start(self):
        self.system_data_client.new(name='system_info', module='_system')
        self.system_data_client.new(name='built_in_functions', module='system_info')
        for k,v in SessionManager.dispatch_table.items():
            value = v.__doc__ if v.__doc__ else "No documentation available"
            self.system_data_client.set(f"built_in_functions:{k}:{value}")
        logger.info("Starting SessionManager")
    
    def stop(self):
        logger.info("Stopping SessionManager")
    
    def decode_access_token(self, token: str):
        try:
            return jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
        except jwt.ExpiredSignatureError:
            logger.error("Token has expired")
            return None
        except jwt.InvalidTokenError:
            logger.error("Invalid token")
            return None

    def user_expiration_dt(self, username, dt=None):
        if not self.system_data_client.in_module(username, 'users'):
            logger.error(f'user {username} is not registered')
            return None
        expiration = self.system_data_client.simple_get([username],['expires'],['*']).format('value')
        if '_infinity' in expiration:
            return 1
        if dt is None:
            try:
                return float(expiration[0])-datetime.now().timestamp()
            except:
                return 0
        self.system_data_client.delete(f'{username}:expires')
        newtime = datetime.now().timestamp()+dt
        self.system_data_client.set(f'{username}:expires:{str(newtime)}')   
        return newtime     

    def login(self, username: str, password: str, edit_mode: bool = False):
        """
        Login method to authenticate a user and return an access token.
        """
        if not self.system_data_client.in_module(username, 'users'):
            logger.error(f"Session login: user {username} is not registered")
            return None
        hashed_password = self.system_data_client.simple_get([username],['password'],['*']).format('value')[0]
        authorized = self.pwd_context.verify(password, hashed_password)
        if not authorized:
            return None
        self.user_expiration_dt(username, self.default_expiration_time_delta)
        logger.info(f"SessionManager login: user {username} logged in")
        self.login_data[username] = DataClient()
        access_data = {
            "sub": username
        }
        access_token = jwt.encode(access_data, self.SECRET_KEY, algorithm=self.ALGORITHM)
        if access_token is None:
            return None
        return {"access_token": access_token, "token_type": "Bearer"}

    def get_user_by_token(self, token: str):
        payload = self.decode_access_token(token)
        if payload is None:
            return None
        username = payload.get("sub")
        if not self.system_data_client.in_module(username,'users'):
            logger.error(f"get_user_by_token: unknown user")
            return None
        if self.user_expiration_dt(username) <=0:
            logger.warning(f'get_user_by_token: token expired for user "{username}", please log in again')
            return None
        return username

    def logout(self, token: str):
        """
        Logout method to invalidate the user's session.
        """
        username = self.get_user_by_token(token)
        if username is None:
            logger.info(f"SessionManager logout: user {username} is not logged in")
            return {"message": f'{username} is not logged in'}
        self.user_expiration_dt(username, dt=0)  # Set expiration time to 0 to invalidate the session
        logger.info(f"SessionManager logout: user {username} logged out")
        del self.login_data[username]  # Remove user session data
        return {"message": f'{username} logged out'}

    def nested_replace(self, text, token, start_delim = r'\(', end_delim = r'\)', item_separator=';', entry_separator=':'):
        x = [m.start() for m in re.finditer(start_delim, text)]
        y = [m.start() for m in re.finditer(end_delim, text)]
        if len(x) != len(y):
            logger.error("Mismatched parentheses")
            return None
        if not x:
            return text
        pairs = [[x[0]]]
        for ni in range(len(x)-1):
            if x[ni+1] > y[ni]:
                pairs[-1].append(y[ni])
                pairs.append([x[ni+1]])
        if y[-1] > x[-1]:
            pairs[-1].append(y[-1])
        else:
            logger.error("Mismatched parentheses")
            return None
        start = 0
        newtext = ""
        for i,pr in enumerate(pairs):
            newtext += text[start:pr[0]]
            sub_result = self.command(text[pr[0]+1:pr[1]], token=token).output
            if isinstance(sub_result, TripletSet):
                sub_result = item_separator.join([entry_separator.join(u) for u in sub_result])
            elif isinstance(sub_result, list):
                sub_result = ','.join(sub_result)
            newtext += sub_result
            start = pr[1]+1
        newtext += text[start:]
        return newtext

    def command(self, text, token:str) -> CommandResponse:
        """
            Communication with the data server should be through commands.
            Commands are simple texts with the format "command arguments"

            The (...) construct in commands means sub-commands that are executed as commands,
            and the result is put back in text level for further processing.

            The output is a TripletSet.
        """
        t0 = time.time()
        user = self.get_user_by_token(token)
        if user is None:
            logger.error("DataCommand command: invalid token")
            return CommandResponse(
                command=text,
                message="invalid token"
            )
        data_client = self.login_data.get(user)
        if data_client is None:
            logger.error(f"DataCommand command: no data client for user {user}")
            return CommandResponse(
                command=text,
                message="invalid token"
            )
        
        self.user_expiration_dt(user, self.default_expiration_time_delta)
        text = text.strip()
        m = re.match(r'^(\w+)\s*(.*)', text)
        if m:
            keyword, argument = m.groups()
        else:
            keyword, argument = '',text

        if keyword not in SessionManager.dispatch_table:
            argument = f'{keyword} {argument}'
            keyword = "get"
        response = SessionManager.dispatch_table[keyword](
            argument = argument,
            user = user,
            data_client = data_client,
            token = token,
            session = self)
        dt = time.time() - t0
        response.message += f' -- elapsed time: {dt:.2f} seconds'
        return response

    
