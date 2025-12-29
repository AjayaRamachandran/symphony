# process_commands.py
# module for working with the process command file, reading and writing.
###### IMPORT ######

import json
import copy
import sys

###### INTERNAL MODULES ######

from console_controls.console import *
import process_command.execute as pce

###### STATE ######

gui_is_open = False

###### FUNCTIONS ######

def operateProcessCommand(file_path):
    '''
    fields:
        file_path (str) - absolute file path to read process command from
    outputs: dict | None

    Reads the process command file, writes a success or error message back into it, then runs the necessary execution method.
    If the command is to open the GUI, returns command data (in all other cases, return nothing) to tell main to open GUI.
    '''
    global gui_is_open

    try:
        with open(file_path, 'r') as pc_file:
            pc = json.load(pc_file)
    except Exception:
        return

    if pc.get('command') is None:
        return

    if pc['command'] == 'kill':
        sys.exit()
    
    if pc['command'] == 'open':
        if gui_is_open:
            with open(file_path, 'w') as dump_file:
                json.dump({
                    "status" : "error",
                    "id" : pc['id'],
                    "message" : "GuiAlreadyRunningError",
                    "payload" : { }
                }, dump_file)
            return
        else:
            gui_is_open = True
            new_pc = copy.deepcopy(pc)
            with open(file_path, 'w') as dump_file:
                json.dump({
                    "status": "success",
                    "id": pc['id'],
                    "message": "",
                    "payload": {}
                }, dump_file)
            return new_pc
    elif pc['command'] in ['retrieve', 'instantiate', 'export', 'convert']:
        command = pc['command']
        new_pc = copy.deepcopy(pc)
        console.log(command + '...')
        try:
            if command == 'retrieve':
                pce.retrieve(pc)
            elif command == 'instantiate':
                pce.instantiate(pc)
            elif command == 'export':
                pce.export(pc)
            elif command == 'convert':
                pce.convert(pc)
        except Exception as e:
            with open(file_path, 'w') as dump_file:
                json.dump({
                    "status": "error",
                    "id": pc['id'],
                    "message": "UnknownError",
                    "payload": {"error_message": str(e)}
                }, dump_file)
            return

