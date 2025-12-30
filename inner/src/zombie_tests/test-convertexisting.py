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

dest_folder = os.path.join(test_dir, "test_symphony_data", "exports")

###### METHODS ######

def file_dump(command):
    global temp_command_path, process_command_path
    with open(temp_command_path, 'w') as pc_file:
        json.dump(command, pc_file)
    os.replace(temp_command_path, process_command_path)

###### TESTS ######

# initialize empty process command file
with open(process_command_path, 'w') as pc_file:
    pc_file.write('')

#try: os.remove(os.path.join(working_file_folder, working_file_name) + '.symphony')
#except: None

# launch main.py in non-blocking mode but keep console output
subprocess.Popen(
    [sys.executable, os.path.join(project_root, "main.py"), project_root, process_command_path],
    stdout=None,  # inherit console output
    stderr=None,
    stdin=None,
    close_fds=True
)

time.sleep(3)

# write "convert" command
convert_command = {
    "command": "convert",
    "id": str(uuid.uuid4()),
    "pc_file_path": process_command_path,
    "args": {
        "project_file_name": working_file_name,
        "project_folder_path": working_file_folder,
        "symphony_data_path": symphony_data_folder,
        "dest_folder_path": dest_folder,
        "file_type": "mid"
    }
}

file_dump(convert_command)

time.sleep(2)

# write "convert" command
convert_command = {
    "command": "convert",
    "id": str(uuid.uuid4()),
    "pc_file_path": process_command_path,
    "args": {
        "project_file_name": working_file_name,
        "project_folder_path": working_file_folder,
        "symphony_data_path": symphony_data_folder,
        "dest_folder_path": dest_folder,
        "file_type": "musicxml",
        "time_sig_numerator" : "auto",
        "time_sig_denominator" : 8,
        "tempo_bpm" : "auto",
        "color_clef_map" : {
            "orange" : "Bass",
            "lime" : "Treble (8vb)",
            "purple" : "Treble",
            "cyan" : "Treble",
            "pink" : "Treble",
            "blue" : "Treble"
        }
    }
}

file_dump(convert_command)