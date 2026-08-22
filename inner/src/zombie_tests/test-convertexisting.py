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

dest_folder = os.path.join(test_dir, "test_symphony_data", "exports")

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

#try: os.remove(os.path.join(working_file_folder, working_file_name) + '.symphony')
#except: None

# launch main.py in non-blocking mode but keep console output
subprocess.Popen(
    [sys.executable, "-u", os.path.join(project_root, "main.py"), project_root],
    stdout=None,  # inherit console output
    stderr=None,
    stdin=None,
    close_fds=True,
    env={**os.environ, "PYTHONUNBUFFERED": "1"}
)

time.sleep(3)

# send "convert" command
convert_command = {
    "command": "convert",
    "id": str(uuid.uuid4()),
    "args": {
        "project_file_name": working_file_name,
        "project_folder_path": working_file_folder,
        "symphony_data_path": symphony_data_folder,
        "dest_folder_path": dest_folder,
        "file_type": "mid"
    }
}

# send_command(convert_command)

time.sleep(2)

# send "convert" command
convert_command = {
    "command": "convert",
    "id": str(uuid.uuid4()),
    "args": {
        "project_file_name": working_file_name,
        "project_folder_path": working_file_folder,
        "symphony_data_path": symphony_data_folder,
        "dest_folder_path": dest_folder,
        "file_type": "musicxml",
        "time_sig_numerator" : "auto",
        "time_sig_denominator" : 4,
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

send_command(convert_command)