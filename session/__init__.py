import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from session.manager import SessionManager
import session.commands.basic_commands
import session.commands.archive_commands
import session.commands.filter_commands