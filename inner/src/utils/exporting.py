# utils/exporting.py
# module for handling the exporting to various file formats.
###### IMPORT ######

import numpy as np
import soundfile as sf
from os import path

###### INTERNAL MODULES ######

from console_controls.console import *

###### METHODS / CLASSES ######

def exportToWav(arr2d: np.ndarray, filename: str, sample_rate: int = 44100): # filename is actually the filepath
    '''
    fields:
        arr2d (np.ndarray) - sound data\n
        filename (str) - the output file name\n
        sample_rate (number) - the sample rate of the audio\n
    outputs: nothing
    
    Take a 2-D array and write it to a WAV file using soundfile library. If file exists, appends an incrementing number to the filename.
    '''
    base, ext = path.splitext(filename)
    candidate = filename
    counter = 1
    while path.exists(candidate):
        candidate = f"{base} ({counter}){ext}"
        counter += 1
    sf.write(candidate, arr2d, sample_rate, subtype='PCM_16')
    console.log('Completed WAV Export.')


def exportToFlac(arr2d: np.ndarray, filename: str, sample_rate: int = 44100):
    '''
    fields:
        arr2d (np.ndarray) - sound data\n
        filename (str) - output filepath\n
        sample_rate (number) - sample rate\n
    outputs: nothing

    Take a 2-D array and write it to a FLAC file.
    If file exists, appends an incrementing number to the filename.
    '''
    base, ext = path.splitext(filename)
    if ext.lower() != ".flac":
        ext = ".flac"

    candidate = base + ext
    counter = 1
    while path.exists(candidate):
        candidate = f"{base} ({counter}){ext}"
        counter += 1

    sf.write(candidate, arr2d, sample_rate, format="FLAC")
    console.log('Completed FLAC Export.')


def exportToMp3(arr2d: np.ndarray, filename: str, sample_rate: int = 44100, quality: float = 0.6):
    '''
    fields:
        arr2d (np.ndarray) - sound data\n
        filename (str) - output filepath\n
        sample_rate (number) - sample rate\n
        quality (float) - mp3 quality (0 to 1.0)\n
    outputs: nothing

    Take a 2-D array and write it to an Ogg Vorbis file.
    If file exists, appends an incrementing number to the filename.
    '''
    base, ext = path.splitext(filename)
    if ext.lower() != ".mp3":
        ext = ".mp3"

    candidate = base + ext
    counter = 1
    while path.exists(candidate):
        candidate = f"{base} ({counter}){ext}"
        counter += 1

    # Ensure correct type and range
    arr2d = np.asarray(arr2d, dtype=np.float32)
    arr2d = arr2d / np.maximum(np.max(np.abs(arr2d)), 1.0)
    arr2d = np.clip(arr2d, -1.0, 1.0)

    # Ensure shape (frames, channels)
    if arr2d.ndim != 2:
        raise ValueError("Audio must be 2D: (frames, channels)")

    sf.write(
        candidate,
        arr2d,
        sample_rate,
        format="MP3",
        subtype="MPEG_LAYER_III",
        compression_level=(1-quality)
    )
    console.log('Completed MP3 Export.')