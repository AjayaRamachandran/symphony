##### test-launchnew.py ######

# test module that starts the python program, initializes a workingfile, then tells the
# python program to open the workingfile in a GUI window.

###### IMPORT ######

import subprocess
import time
import os
import json
import uuid
import sys
import urllib.request

####### INITIALIZE ######

test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(test_dir, ".."))
symphony_data_folder = os.path.join(test_dir, "test_symphony_data")
working_file_folder = os.path.join(test_dir, "test_projects")
working_file_name = "testfile"

PROCESS_COMMAND_URL = "http://127.0.0.1:7279/process-command"

###### METHODS ######

def send_command(command):
    body = json.dumps(command).encode('utf-8')
    request = urllib.request.Request(
        PROCESS_COMMAND_URL,
        data=body,
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode('utf-8'))

###### TESTS ######

# send "kill" command
kill_command = {
    "command": "kill",
    "id": str(uuid.uuid4()),
    "args": {
        "project_file_name": working_file_name,
        "project_folder_path": working_file_folder,
        "symphony_data_path": symphony_data_folder
    }
}

try: send_command(kill_command)
except Exception: None

time.sleep(2)

try: os.remove(os.path.join(working_file_folder, working_file_name) + '.symphony')
except: None

# launch main.py in non-blocking mode but keep console output
subprocess.Popen(
    [sys.executable, os.path.join(project_root, "main.py"), project_root],
    stdout=None,  # inherit console output
    stderr=None,
    stdin=None,
    close_fds=True
)

time.sleep(2)

# send "instantiate" command
instantiate_command = {
    "command": "instantiate",
    "id": str(uuid.uuid4()),
    "args": {
        "project_file_name": working_file_name,
        "project_folder_path": working_file_folder,
        "symphony_data_path": symphony_data_folder
    }
}

send_command(instantiate_command)

time.sleep(1)

# send "open" command
open_command = {
    "command": "open",
    "id": str(uuid.uuid4()),
    "args": {
        "project_file_name": working_file_name,
        "project_folder_path": working_file_folder,
        "symphony_data_path": symphony_data_folder
    }
}

send_command(open_command)

#time.sleep(10)

# send "kill" command
kill_command = {
    "command": "kill",
    "id": str(uuid.uuid4()),
    "args": {
        "project_file_name": working_file_name,
        "project_folder_path": working_file_folder,
        "symphony_data_path": symphony_data_folder
    }
}

#send_command(kill_command)