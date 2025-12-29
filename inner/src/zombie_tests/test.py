##### TEST1.PY ######

# test module that starts the python program, initializes a workingfile, then tells the
# python program to open the workingfile in a GUI window.

import subprocess
import time
import os
import json
import uuid
import sys

test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(test_dir, ".."))
symphony_data_folder = os.path.join(test_dir, "test_symphony_data")
process_command_path = os.path.join(test_dir, "test_symphony_data", "process-command.json")
working_file_folder = os.path.join(test_dir, "test_projects")
working_file_name = "testfile"

# initialize empty process command file
with open(process_command_path, 'w') as pc_file:
    pc_file.write('')

try: os.remove(os.path.join(working_file_folder, working_file_name) + '.symphony')
except: None

# launch main.py in non-blocking mode but keep console output
subprocess.Popen(
    [sys.executable, os.path.join(project_root, "main.py"), project_root, process_command_path],
    stdout=None,  # inherit console output
    stderr=None,
    stdin=None,
    close_fds=True
)

time.sleep(3)

# write "instantiate" command
instantiate_command = {
    "command": "instantiate",
    "id": str(uuid.uuid4()),
    "pc_file_path": process_command_path,
    "args": {
        "project_file_name": working_file_name,
        "project_folder_path": working_file_folder,
        "symphony_data_path": symphony_data_folder
    }
}
with open(process_command_path, 'w') as pc_file:
    json.dump(instantiate_command, pc_file)


time.sleep(2)

# write "open" command
open_command = {
    "command": "open",
    "id": str(uuid.uuid4()),
    "pc_file_path": process_command_path,
    "args": {
        "project_file_name": working_file_name,
        "project_folder_path": working_file_folder,
        "symphony_data_path": symphony_data_folder
    }
}
with open(process_command_path, 'w') as pc_file:
    json.dump(open_command, pc_file)

time.sleep(2)

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
with open(process_command_path, 'w') as pc_file:
    json.dump(kill_command, pc_file)
