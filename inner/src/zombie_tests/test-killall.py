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

####### INITIALIZE ######

test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(test_dir, ".."))
symphony_data_folder = os.path.join(test_dir, "test_symphony_data")
process_command_path = os.path.join(test_dir, "test_symphony_data", "process-command.json")
temp_command_path = os.path.join(test_dir, "test_symphony_data", "temp.json")
working_file_folder = os.path.join(test_dir, "test_projects")
working_file_name = "testfile"

###### METHODS ######

def file_dump(command):
    global temp_command_path, process_command_path
    with open(temp_command_path, 'w') as pc_file:
        json.dump(command, pc_file)
    os.replace(temp_command_path, process_command_path)

###### TESTS ######

# write "kill" command
kill_command = {
    "command": "kill",
    "id": str(uuid.uuid4()),
    "pc_file_path": process_command_path,
    "args": {
        "project_file_name": working_file_name,
        "project_folder_path": working_file_folder,
        "symphony_data_path": symphony_data_folder
    }
}

file_dump(kill_command)