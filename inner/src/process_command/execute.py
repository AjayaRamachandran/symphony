# process_command/execute.py
# handles the execution of end-point process commands, such as retrieve, instantiate, export, and convert.
###### IMPORT ######

import json
from os import path
import dill as pkl
from math import floor

###### INTERNAL MODULES ######

from console_controls.console import *
import utils.state_loading as sl
import utils.file_io as fio
import utils.sound_processing as sp

###### FUNCTIONS ######

def retrieve(pc_file: dict):
    '''
    fields:
        pc_file (dict) - the data contained within the process command file.
    outputs: nothing

    Retrieves and writes the project data into the process command file.
    '''
    args = pc_file['args']

    project_file_path = path.join(args['project_folder_path'], args['project_file_name']) + '.symphony'
    response_file_path = args['pc_file_path']
    ps = sl.toProgramState(pkl.load(open(project_file_path, "rb")))

    with open(response_file_path, 'w') as f:

        tpm = round(3600 / ps["ticksPerTile"], 2)
        tiles = int((max(ps["noteMap"].items(), key=lambda x : x[0][1]))[0][1]) if (len(ps["noteMap"].items()) > 0) else 0
        payload = {
            'fileInfo' : {
                'Key' : ps["key"],
                'Mode' : ps["mode"],
                'Tempo (tpm)' : tpm,
                # 'Empty?' : (ps["noteMap"] == {}),
                'Length (tiles)' : tiles,
                'Duration' : ("0" if len(str(floor(tiles / tpm))) == 1 else '') + str(floor(tiles / tpm)) + ':' + ("0" if len(str(round(((tiles / tpm) % 1) * 60))) == 1 else '') + str(round(((tiles / tpm) % 1) * 60))
                }
        }
        json.dump({
            "status" : "success",
            "id" : pc_file['id'],
            "message" : "",
            "payload" : payload
        }, f)
        
        f.close()


def instantiate(pc_file: dict):
    '''
    fields:
        pc_file (dict) - the data contained within the process command file.
    outputs: nothing

    Creates a new project file and returns success to the pc file.
    '''
    args = pc_file['args']

    NOTE_MAP_EMPTY = {}
    WAVE_MAP_EMPTY = {
        "orange" : 0,
        "purple" : 0,
        "cyan" : 0,
        "lime" : 0,
        "blue" : 0,
        "pink" : 0,
        "all" : 0
    }

    ps = sl.newProgramState("Eb", "Lydian", 10, NOTE_MAP_EMPTY, WAVE_MAP_EMPTY)
    project_file_path = path.join(args['project_folder_path'], args['project_file_name']) + '.symphony'
    response_file_path = args['pc_file_path']

    fio.simpleDump(project_file_path, ps)
    with open(response_file_path, 'w') as f:
        json.dump({
            "status" : "success",
            "id" : pc_file['id'],
            "message" : "",
            "payload" : { }
        }, f)
        
        f.close()


def export(pc_file: dict):
    '''
    fields:
        pc_file (dict) - the data contained within the process command file.
    outputs: nothing

    Exports the project into a specified audio format. (mp3 or wav)
    '''
    args = pc_file['args']

    project_file_name = args['project_file_name']
    project_folder_path = args['project_folder_path']
    output_file_type = args['file_type']

    project_file_path = path.join(project_folder_path, project_file_name) + '.symphony'
    response_file_path = args['pc_file_path']
    ps = sl.toProgramState(pkl.load(open(project_file_path, "rb")))

    finalWave = sp.createFullSound(ps['noteMap'], ps['waveMap'], tpm=ps['tpm'])
    arr2d = sp.toSound(finalWave, returnType='2DArray')

    if output_file_type == 'wav':
        sp.exportToWav(arr2d, path.join(project_folder_path, project_file_name) + '.wav', sample_rate=44100)
    elif output_file_type == 'flac':
        sp.exportToFlac(arr2d, path.join(project_folder_path, project_file_name) + '.flac', sample_rate=44100)
    elif output_file_type == 'ogg':
        sp.exportToOggVorbis(arr2d, path.join(project_folder_path, project_file_name) + '.ogg', sample_rate=44100)

    with open(response_file_path, 'w') as f:
        json.dump({
            "status" : "success",
            "id" : pc_file['id'],
            "message" : "",
            "payload" : { }
        }, f)
        
        f.close()


def convert(pc_file: dict):
    '''
    fields:
        pc_file (dict) - the data contained within the process command file.
    outputs: nothing

    Converts the project into a specified musical notation format. (mid or mscz)
    '''
    args = pc_file['args']

    project_file_name = args['project_file_name']
    project_folder_path = args['project_folder_path']
    output_file_type = args['file_type']

    if args['tempo'] == 'auto':
        

    project_file_path = path.join(project_folder_path, project_file_name) + '.symphony'
    response_file_path = args['pc_file_path']
    ps = sl.toProgramState(pkl.load(open(project_file_path, "rb")))

    if output_file_type == 'mid':
        sp.createMidiFromNotes(sl.convertNoteMapToStrikeList(ps['noteMap']),
                               path.join(project_folder_path, project_file_name) + '.mid')
    if output_file_type == 'musicxml':
        sp.createMusicXMLFromNotes(ps['noteMap'],
                                   path.join(project_folder_path, project_file_name) + '.musicxml',
                                   ps['tpm'],
                                   args['quarter_notes_per_tile'],
                                   args)