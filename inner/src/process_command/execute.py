# process_command/execute.py
# handles the execution of end-point process commands, such as retrieve, instantiate, export, and convert.
###### IMPORT ######

from os import path
import dill as pkl
from math import floor

###### INTERNAL MODULES ######

from console_controls.console import *
import utils.state_loading as sl
import utils.file_io as fio
import sound.sound_processing as sp
import utils.converting as converting
import utils.exporting as exporting

###### FUNCTIONS ######

def processCommandResponse(pcFile: dict, payload=None):
    '''
    fields:
        pcFile (dict) - process command payload
        payload (dict | None) - response payload
    outputs: dict

    Builds a successful process command response.
    '''
    return {
        "status": "success",
        "id": pcFile['id'],
        "message": "",
        "payload": payload or {}
    }


def retrieve(pcFile: dict):
    '''
    fields:
        pcFile (dict) - the process command payload.
    outputs: dict

    Retrieves the project data and returns it as a process command response.
    '''
    args = pcFile['args']

    projectFilePath = path.join(args['project_folder_path'], args['project_file_name']) + '.symphony'
    with open(projectFilePath, "rb") as pf:
        ps = sl.toProgramState(pkl.load(pf))

    maxNoteEndTime = 0
    for color, colorChannel in ps["noteMap"].items():
        for note in colorChannel:
            maxNoteEndTime = max(maxNoteEndTime, note.time + note.duration)

    tpm = ps["tpm"]
    tiles = maxNoteEndTime
    payload = {
        'fileInfo' : {
            'Description' : ps['meta']['file_data']['description'],
            'Composer' : ps['meta']['file_data']['composer'],
            'Collaborators' : ps['meta']['file_data']['collaborators'],
            'Key' : ps["key"],
            'Mode' : ps["mode"],
            'Tempo (tpm)' : ps["tpm"],
            'Beats Per Measure' : ps["beatsPerMeasure"],
            # 'Empty?' : (ps["noteMap"] == {}),
            'Length (tiles)' : tiles,
            'Duration' : ("0" if len(str(floor(tiles / tpm))) == 1 else '') + str(floor(tiles / tpm)) + ':' + ("0" if len(str(round(((tiles / tpm) % 1) * 60))) == 1 else '') + str(round(((tiles / tpm) % 1) * 60))
        }
    }
    return processCommandResponse(pcFile, payload)


def instantiate(pcFile: dict):
    '''
    fields:
        pcFile (dict) - the process command payload.
    outputs: dict

    Creates a new project file and returns success.
    '''
    args = pcFile['args']

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

    ps = sl.newProgramState("Eb", "Lydian", 360, NOTE_MAP_EMPTY, WAVE_MAP_EMPTY, 4, 4)
    projectFilePath = path.join(args['project_folder_path'], args['project_file_name']) + '.symphony'

    fio.simpleDump(projectFilePath, ps)
    return processCommandResponse(pcFile, { "project_file_path": projectFilePath })


def export(pcFile: dict):
    '''
    fields:
        pcFile (dict) - the process command payload.
    outputs: dict

    Exports the project into a specified audio format. (mp3 or wav)
    '''
    args = pcFile['args']

    projectFileName = args['project_file_name']
    projectFolderPath = args['project_folder_path']
    outputFileType = args['file_type']
    destFolderPath = args['dest_folder_path']

    projectFilePath = path.join(projectFolderPath, projectFileName) + '.symphony'
    with open(projectFilePath, "rb") as pf:
        ps = sl.toProgramState(pkl.load(pf))

    finalWave = sp.createFullSound(ps['noteMap'], ps['waveMap'], tpm=ps['tpm'])
    arr2d = sp.toSound(finalWave, returnType='2DArray')

    if outputFileType == 'wav':
        outputFilePath = exporting.exportToWav(arr2d, path.join(destFolderPath, projectFileName) + '.wav', sample_rate=44100)
    elif outputFileType == 'flac':
        outputFilePath = exporting.exportToFlac(arr2d, path.join(destFolderPath, projectFileName) + '.flac', sample_rate=44100)
    elif outputFileType == 'mp3':
        outputFilePath = exporting.exportToMp3(arr2d, path.join(destFolderPath, projectFileName) + '.mp3', sample_rate=44100)

    return processCommandResponse(pcFile, { "output_file_path": outputFilePath })


def convert(pcFile: dict):
    '''
    fields:
        pcFile (dict) - the process command payload.
    outputs: dict

    Converts the project into a specified musical notation format. (mid or mscz)
    '''
    args = pcFile['args']

    projectFileName = args['project_file_name']
    projectFolderPath = args['project_folder_path']
    outputFileType = args['file_type']
    destFolderPath = args['dest_folder_path']

    projectFilePath = path.join(projectFolderPath, projectFileName) + '.symphony'
    with open(projectFilePath, "rb") as pf:
        ps = sl.toProgramState(pkl.load(pf))

    if outputFileType == 'midi':
        outputFilePath = converting.createMidiFromNotes(ps['noteMap'], path.join(destFolderPath, projectFileName) + '.mid')
    if outputFileType == 'musicxml':
        if args['time_sig_denominator'] == 'auto': timeSigDenominator = 4
        else: timeSigDenominator = args['time_sig_denominator']

        if args['tempo_bpm'] == 'auto': bpm = (ps['tpm'] / ps['beatLength']) * (4 / timeSigDenominator)
        else: bpm = args['tempo_bpm']
        
        if args['time_sig_numerator'] == 'auto': timeSigNumerator = ps['beatsPerMeasure']
        else: timeSigNumerator = args['time_sig_numerator']

        outputFilePath = converting.createMusicXMLFromNotes(ps['noteMap'],
                                   path.join(destFolderPath, projectFileName) + '.musicxml',
                                   bpm,
                                   timeSigNumerator,
                                   timeSigDenominator,
                                   ps['beatLength'],
                                   ps['key'],
                                   ps['mode'],
                                   args['color_clef_map'] if (args['color_clef_map'] != {}) else None)
        
    return processCommandResponse(pcFile, { "output_file_path": outputFilePath })


def updateMetadata(pcFile: dict):
    '''
    fields:
        pcFile (dict) - the process command payload.
    outputs: dict

    Updates the metadata of the project.
    '''
    args = pcFile['args']

    projectFileName = args['project_file_name']
    projectFolderPath = args['project_folder_path']
    metadata = args['metadata']

    projectFilePath = path.join(projectFolderPath, projectFileName) + '.symphony'
    with open(projectFilePath, "rb") as pf:
        ps = sl.toProgramState(pkl.load(pf))

    defaultFileData = sl.DEFAULT_META_FIELD["file_data"]
    hasRequiredMetadataFields = (
        isinstance(metadata, dict)
        and all(field in metadata for field in defaultFileData.keys())
    )
    savedMetadata = metadata if hasRequiredMetadataFields else dict(defaultFileData)
    ps['meta']['file_data'] = savedMetadata

    with open(projectFilePath, "wb") as pf:
        pkl.dump(ps, pf)

    return processCommandResponse(pcFile, { "metadata": savedMetadata })