# sound_processing.py
# module for handling all sound related code.
###### IMPORT ######

import numpy as np
import pygame
from soundfile import write as sfwrite
import pretty_midi
from os import environ, path
from math import *

###### INTERNAL MODULES ######

import values as v
from console_controls.console import *

###### METHODS ######

def notesToFreq(notes):
    '''Converts a set of notes (as ints from C2) to frequencies'''
    freqs = []
    C1 = 65.41 / 2
    ratio = 1.05946309436
    for note in notes:
        noteFreq = C1 * (ratio ** (note - 1))
        freqs.append(noteFreq)
    return freqs

def toSound(array_1d: np.ndarray, returnType='Sound'):# -> pygame.mixer.Sound:
    '''Convert a 1-D int16 numpy array into a 2-D array matching mixer channels, then wrap into a Sound.'''
    freq, fmt, nchan = pygame.mixer.get_init()
    if nchan == 1:
        arr2d = array_1d.reshape(-1, 1)
    else:
        # duplicate mono into both LR for stereo
        arr2d = np.column_stack([array_1d] * nchan)
    return pygame.sndarray.make_sound(arr2d) if returnType == 'Sound' else arr2d

def exportToWav(arr2d: np.ndarray, filename: str, sample_rate: int = 44100): # filename is actually the filepath
    '''Take a 2-D array and write it to a WAV file using soundfile library. If file exists, appends an incrementing number to the filename.'''
    base, ext = path.splitext(filename)
    candidate = filename
    counter = 1
    while path.exists(candidate):
        candidate = f"{base} ({counter}){ext}"
        counter += 1
    sfwrite(candidate, arr2d, sample_rate, subtype='PCM_16')

def playNotes(notes, duration=1, waves=0, volume=0.2, sample_rate=v.SAMPLE_RATE):
    '''Single set of notes playback, does not keep track of phase.'''
    try:
        freqs = notesToFreq(notes)
        counts = {}
        for f in freqs:
            counts[f] = counts.get(f, 0) + 1

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = np.zeros_like(t)

        for freq, mag in counts.items():
            if waves == 0:
                part = np.sign(np.sin(2 * np.pi * freq * t)) * mag
            elif waves == 1:
                part = (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * freq * t)) * mag
            else:
                part = 2 * (t * freq - np.floor(0.5 + t * freq)) * mag
            wave += part

        # normalize + volume
        wave = wave/np.max(np.abs(wave)) - (0.6*wave/(np.max(np.abs(wave))**2))
        wave *= volume * v.globalVolume

        audio = (wave * 32767).astype(np.int16)
        sound = toSound(audio)
        v.play_obj = sound.play()
    except Exception as e:
        console.error(f"NoteError: {e}")

def assembleNotes(notes, phases, duration=1, volume=0.2, sample_rate=v.SAMPLE_RATE):
    '''Compound notes playback, tracks phase to keep continuous notes'''
    freqs = notesToFreq([n[0] for n in notes])
    inColors = [n[2] for n in notes]

    counts = {}
    for idx, f in enumerate(freqs):
        typ = v.waveMap[inColors[idx]]
        counts[(f, typ)] = counts.get((f, typ), 0) + 1

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    newPhases = {}
    wave = np.zeros_like(t)
    #seen = set()

    phasesOfFreqs = {}

    for idx, freq in enumerate(freqs):
        typ = v.waveMap[inColors[idx]]
        phase = phases.get(freq, 0.0)
        if notes[idx][1]:
            phase += pi
        if freq in phasesOfFreqs:
            phase = phasesOfFreqs[freq]
        else:
            phasesOfFreqs[freq] = phase
        #if (freq, typ) in seen:
            #continue

        if typ == 0: # square wave
            part = np.sign(np.sin(2 * np.pi * freq * t + phase)) * counts[(freq, typ)]
        elif typ == 1: # triangle wave
            part = (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * freq * t + phase)) * counts[(freq, typ)]
        else: # sawtooth wave
            part = 2 * (t * freq + (phase / (2 * pi)) - np.floor(0.5 + t * freq + (phase / (2 * pi)))) * counts[(freq, typ)]

        wave += part
        #seen.add((freq, typ))
        newPhases[freq] = (phase + 2 * np.pi * freq * duration) % (2 * np.pi) # increments phase to keep it continuous

    # normalize + volume
    wave = wave / np.max(np.abs(wave)) - (0.6 * wave / (np.max(np.abs(wave)) ** 2))
    wave *= volume * v.globalVolume

    audio = (wave * 32767).astype(np.int16)
    return audio, newPhases

def createMidiFromNotes(noteData, outputFolderPath, instrumentName="Acoustic Grand Piano"):
    global tpm
    baseName = path.splitext(path.basename(v.workingFile))[0]
    ext = ".mid"
    candidate = path.join(outputFolderPath, baseName + ext)
    # Resolve name conflicts
    counter = 1
    while path.exists(candidate):
        candidate = path.join(outputFolderPath, f"{baseName} ({counter}){ext}")
        counter += 1
    
    midi = pretty_midi.PrettyMIDI()
    instrument = pretty_midi.Instrument(program=pretty_midi.instrument_name_to_program(instrumentName))

    for note in noteData:
        pitch = note["pitch"]
        start = note["startTime"]
        end = start + note["duration"]
        velocity = note.get("velocity", 127)

        midiNote = pretty_midi.Note(velocity=velocity, pitch=pitch, start=start, end=end)
        instrument.notes.append(midiNote)

    midi.instruments.append(instrument)
    midi.write(candidate)