# sound/sound_processing.py
# module for handling all sound related code.
###### IMPORT ######

import numpy as np
import pygame
from math import exp

###### INTERNAL MODULES ######

from console_controls.console import *
import sound.instruments as ins

###### INITIALIZE ######

SAMPLE_RATE = 44100

###### METHODS / CLASSES ######

def notesToFreq(notes):
    '''
    fields:
        notes (list) - notes to convert
    outputs: list

    Converts a set of notes (as ints from C2) to frequencies
    '''
    freqs = []
    C2 = 65.41
    ratio = 1.05946309436
    for note in notes:
        noteFreq = C2 * (ratio ** (note - 1))
        freqs.append(noteFreq)
    return freqs

def noteToMagnitude(note, waves):
    '''
    fields:
        note (number) - input note pitch\n
        waves (number) - wave type\n
    outputs: number

    Gets a relative magnitude based on an input note and type, to keep perceived volume the same
    '''
    if waves != 1:
        mag = (1.8 - 1.4 * (note / 72))
    else:
        mag = 6 * exp(-(1/20) * (note + 5))
    return mag

def toSound(array_1d: np.ndarray, returnType='Sound'):# -> pygame.mixer.Sound:
    '''
    fields:
        array_1d (np.ndarray) - 1-dimensional int16 array of waves\n
        returnType (string) - what to return the sound as\n
    outputs: pygame sound
    
    Convert a 1-D int16 numpy array into a 2-D array matching mixer channels, then wrap into a Sound.
    '''
    freq, fmt, nchan = pygame.mixer.get_init()
    if nchan == 1:
        arr2d = array_1d.reshape(-1, 1)
    else:
        # duplicate mono into both LR for stereo
        arr2d = np.column_stack([array_1d] * nchan)
    return pygame.sndarray.make_sound(arr2d) if returnType == 'Sound' else arr2d

def createNoteBuffer(note, waves=0, duration=1, volume=0.2, sample_rate=SAMPLE_RATE):
    '''
    fields:
        notes (list) - list of notes to play\n
        waves (number) - wave type for the notes\n
        duration (number) - duration of the sound, in seconds\n
        volume (number) - volume of the sound\n
        sample_rate (number) - the sample rate of the audio\n
    outputs: np.ndarray | None
    
    Creates and returns a note's sound buffer based on provided information about the note.
    '''
    notes = [note]
    try:
        freqs = notesToFreq(notes)
        counts = {}
        for index, f in enumerate(freqs):
            counts[(notes[index], f)] = counts.get((notes[index], f), 0) + 1

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = np.zeros_like(t)
        instrument_fn = ins.get_instrument(waves)

        for freqt, mag in counts.items():
            note, freq = freqt
            part = instrument_fn(t, freq, mag)
            wave += part * noteToMagnitude(note, waves)

        # --- small fade-out for triangle wave to avoid pop ---
        if waves == 1:
            fade_time = 0.005  # 5 ms
            fade_len = int(sample_rate * fade_time)
            if fade_len > 0:
                fade = np.linspace(1, 0, fade_len)
                wave[-fade_len:] *= fade
        # ----------------------------------------------------

        # normalize + volume
        wave *= volume * 0.3

        audio = (wave * 32767).astype(np.int16)
        return audio
    
    except Exception as e:
        console.error(f"Note Generation Error: {e}")
        return None

def playNote(note, waves=0, duration=1, volume=0.2, sample_rate=SAMPLE_RATE):
    '''
    fields:
        note (number) - note to play\n
        waves (number) - wave type for the notes\n
        duration (number) - duration of the sound, in seconds\n
        volume (number) - volume of the sound\n
        sample_rate (number) - the sample rate of the audio\n
    outputs: nothing
    
    Single note playback. Doesn't return anything, just plays the sound.
    '''
    try:
        audio = createNoteBuffer(note, waves, duration, volume, sample_rate)
        if audio is None:
            return None

        sound = toSound(audio)

        play_obj = sound.play()
        return play_obj
    
    except Exception as e:
        console.error(f"Note Playback Error: {e}")
        return None

def createFullSound(noteMap, waveMap, playhead=0, tpm=360, volume=0.2, sample_rate=SAMPLE_RATE, channel='all'):
    '''
    fields:
        noteMap (dict) - noteMap in stanard format\n
        waveMap (dict) - waveMap in standard format\n
        playhead (int) - tile offset\n
        tpm (int) - tiles per minute\n
        volume (float) - output volume\n
        sample_rate (int) - audio sample rate\n
        channel (str | int) - which channel to play\n
    outputs: np.ndarray

    Creates the full sound of the song as a buffer, stored in an ndarray.
    '''

    seconds_per_tile = 60.0 / tpm

    # Flatten notes and find total length
    all_notes = []
    last_tile = 0

    for cchIdx, cch in enumerate(noteMap.items()):
        color, notes = cch
        if channel == 'all' or channel == cchIdx:
            for note in notes:
                all_notes.append((color, note))
                end_tile = note.time + note.duration
                last_tile = max(last_tile, end_tile)

    total_duration = last_tile * seconds_per_tile
    total_samples = int(total_duration * sample_rate)

    wave = np.zeros(total_samples, dtype=np.float32)

    # Generate each note into the buffer
    for color, note in all_notes:
        wave_type = waveMap[color]

        start_sec = note.time * seconds_per_tile
        dur_sec = note.duration * seconds_per_tile

        start_idx = int(start_sec * sample_rate)
        if start_idx >= total_samples:
            continue

        note_audio = createNoteBuffer(note.pitch, wave_type, dur_sec, 1.0, sample_rate)
        if note_audio is None or len(note_audio) == 0:
            continue

        part = note_audio.astype(np.float32) / 32767.0
        write_len = min(len(part), total_samples - start_idx)
        if write_len <= 0:
            continue

        wave[start_idx:start_idx + write_len] += part[:write_len]

    # Normalize
    max_val = np.max(np.abs(wave))
    if max_val > 0:
        wave /= max_val

    wave *= volume * 0.3

    # Apply playhead offset
    playhead_samples = int(playhead * seconds_per_tile * sample_rate)
    if playhead_samples < len(wave):
        wave = wave[playhead_samples:]
    else:
        wave = np.zeros(1, dtype=np.float32)

    audio = (wave * 32767).astype(np.int16)

    return audio

def playFull(noteMap, waveMap, playhead=0, tpm=360, volume=0.2, sample_rate=SAMPLE_RATE, channel='all'):
    '''
    fields:
        noteMap (dict) - noteMap in standard format\n
        waveMap (dict) - waveMap in standard format\n
        playhead (int) - tile offset\n
        tpm (int) - tiles per minute\n
        volume (float) - output volume\n
        sample_rate (int) - audio sample rate\n
        channel (str | int) - which channel to play\n
    outputs: nothing (plays sound)

    Creates the full sound as a buffer then plays it.
    '''
    notesToPlay = noteMap if channel == 'all' else {list(noteMap.items())[channel][0] : list(noteMap.items())[channel][1]}

    try:
        audio = createFullSound(notesToPlay, waveMap, playhead, tpm, volume, sample_rate)
        sound = toSound(audio)

        play_obj = sound.play()
        return play_obj

    except Exception as e:
        console.error(f"playFull Error: {e}")
        return None
