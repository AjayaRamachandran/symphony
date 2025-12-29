# process_commands.py
# module for working with the process command file, reading and writing.
###### IMPORT ######

import json
import copy

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
    '''
    global gui_is_open

    pc_file = open(file_path)
    pc = json.load(pc_file)
    
    if pc['command'] == 'open':
        if gui_is_open:
            json.dump({
                "status" : "error",
                "id" : pc['id'],
                "message" : "GuiAlreadyRunningError",
                "payload" : { }
            }, pc_file)
            return
        else:
            new_pc = copy.deepcopy(pc)
            json.dump({
                "status" : "success",
                "id" : pc['id'],
                "message" : "",
                "payload" : { }
            }, pc_file)
            return new_pc
    elif pc['command'] in ['retrieve', 'instantiate', 'export', 'convert']:
        with pc['command'] as command:
            new_pc = copy.deepcopy(pc)
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
                json.dump({
                    "status" : "error",
                    "id" : pc['id'],
                    "message" : "UnknownError",
                    "payload" : {
                        "error_message" : e
                    }
                }, pc_file)

