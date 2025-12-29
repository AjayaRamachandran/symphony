# utils/sound_processing.py
# module for handling all sound related code.
###### IMPORT ######

import numpy as np
import pygame
from soundfile import write as sfwrite
import pretty_midi
from os import path
from math import exp
from music21 import stream, note, tempo, meter, instrument, clef

###### INTERNAL MODULES ######

from console_controls.console import *

###### INITIALIZE ######

SAMPLE_RATE = 44100

###### METHODS ######

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


def playNotes(notes=[], waves=0, duration=1, volume=0.2, sample_rate=SAMPLE_RATE):
    '''
    fields:
        notes (list) - list of notes to play\n
        waves (number) - wave type for the notes\n
        duration (number) - duration of the sound, in seconds\n
        volume (number) - volume of the sound\n
        sample_rate (number) - the sample rate of the audio\n
    outputs: nothing
    
    Single set of notes playback, does not keep track of phase. Doesn't return, just plays the sound.
    '''
    try:
        freqs = notesToFreq(notes)
        counts = {}
        for index, f in enumerate(freqs):
            counts[(notes[index], f)] = counts.get((notes[index], f), 0) + 1

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = np.zeros_like(t)

        for freqt, mag in counts.items():
            note, freq = freqt
            if waves == 0:
                part = np.sign(np.sin(2 * np.pi * freq * t)) * mag
            elif waves == 1:
                part = (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * freq * t)) * mag * 3
            else:
                part = 2 * (t * freq - np.floor(0.5 + t * freq)) * mag
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
        sound = toSound(audio)

        play_obj = sound.play()
        return play_obj
    
    except Exception as e:
        console.error(f"NoteError: {e}")
        return None

def playFull(noteMap, waveMap, playhead=0, tpm=120, volume=0.2, sample_rate=SAMPLE_RATE, channel='all'):
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

    try:
        audio = createFullSound(noteMap, waveMap, playhead, tpm, volume, sample_rate)
        sound = toSound(audio)

        play_obj = sound.play()
        return play_obj

    except Exception as e:
        console.error(f"playFull Error: {e}")
        return None

def createFullSound(noteMap, waveMap, playhead=0, tpm=120, volume=0.2, sample_rate=SAMPLE_RATE, channel='all'):
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
        freq = notesToFreq([note.pitch])[0]
        wave_type = waveMap[color]

        start_sec = note.time * seconds_per_tile
        dur_sec = note.duration * seconds_per_tile

        start_idx = int(start_sec * sample_rate)
        end_idx = int((start_sec + dur_sec) * sample_rate)

        if start_idx >= total_samples:
            continue

        t = np.linspace(0, dur_sec, end_idx - start_idx, False)

        if wave_type == 0:  # square
            part = np.sign(np.sin(2 * np.pi * freq * t))
        elif wave_type == 1:  # triangle
            part = (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * freq * t))

            # --- small fade-out to avoid pop ---
            fade_time = 0.005  # 5 ms
            fade_len = int(sample_rate * fade_time)
            if fade_len > 0 and fade_len < len(part):
                fade = np.linspace(1, 0, fade_len)
                part[-fade_len:] *= fade
            # ----------------------------------
        else:  # sawtooth
            part = 2 * (t * freq - np.floor(0.5 + t * freq))

        part *= noteToMagnitude(note.pitch, wave_type)

        wave[start_idx:end_idx] += part[:max(0, total_samples - start_idx)]

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
    sfwrite(candidate, arr2d, sample_rate, subtype='PCM_16')


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

    sfwrite(candidate, arr2d, sample_rate, format="FLAC")


def exportToOggVorbis(arr2d: np.ndarray, filename: str, sample_rate: int = 44100, quality: float = 0.5):
    '''
    fields:
        arr2d (np.ndarray) - sound data\n
        filename (str) - output filepath\n
        sample_rate (number) - sample rate\n
        quality (float) - Vorbis quality (-1.0 to 1.0, typical 0.3-0.6)\n
    outputs: nothing

    Take a 2-D array and write it to an Ogg Vorbis file.
    If file exists, appends an incrementing number to the filename.
    '''
    base, ext = path.splitext(filename)
    if ext.lower() not in (".ogg", ".oga"):
        ext = ".ogg"

    candidate = base + ext
    counter = 1
    while path.exists(candidate):
        candidate = f"{base} ({counter}){ext}"
        counter += 1

    sfwrite(
        candidate,
        arr2d,
        sample_rate,
        format="OGG",
        subtype="VORBIS",
        compression=quality
    )

def createMidiFromNotes(noteMap: dict, filename: str, instrumentName="Acoustic Grand Piano"):
    '''
    fields:
        noteMap (dict) - noteMap data\n
        filename (string) - path of output folder\n
        instrumentName (string) - instrument type to use\n
    outputs: nothing

    Generates a MIDI file from a 1.1 noteMap and saves it to a file.
    '''

    base, ext = path.splitext(filename)
    # Resolve name conflicts
    candidate = base + ext
    counter = 1
    while path.exists(candidate):
        candidate = f"{base} ({counter}){ext}"
        counter += 1
    
    midi = pretty_midi.PrettyMIDI()
    instrument = pretty_midi.Instrument(program=pretty_midi.instrument_name_to_program(instrumentName))

    for color, channel in noteMap.items():
        for note in noteMap:
            pitch = note.pitch + 23
            start = note.time
            end = start + note.duration
            velocity = 64

            midiNote = pretty_midi.Note(velocity=velocity, pitch=pitch, start=start, end=end)
            instrument.notes.append(midiNote)

    midi.instruments.append(instrument)
    midi.write(candidate)

def createMusicXMLFromNotes(
    noteMap: dict,
    filename: str,
    tempoBPM: int,
    timeSigNumerator: int,
    timeSigDenominator: int,
    beatLength: int,
    key: str,
    mode: str,
    colorStaffMap: dict | None = None
):
    '''
    fields:
        noteMap (dict) - {color: iterable of notes}\n
        filename (str) - output filepath (.musicxml)\n
        tempoBPM (int) - tempo in BPM\n
        timeSigNumerator (int) - beats per measure\n
        timeSigDenominator (int) - note value that gets the beat\n
        beatLength (int) - number of tiles per beat\n
        key (str) - tonic (e.g. "C#", "Db")\n
        mode (str) - musical mode\n
        colorStaffMap (dict) - color → clef name (ex. "Treble", "Tenor (8vb)")\n
    outputs: nothing

    Generates a MuseScore-compatible MusicXML notation file.
    '''

    base, ext = path.splitext(filename)
    if ext.lower() not in (".xml", ".musicxml"):
        ext = ".musicxml"

    candidate = base + ext
    counter = 1
    while path.exists(candidate):
        candidate = f"{base} ({counter}){ext}"
        counter += 1

    score = stream.Score()

    # Tempo
    score.insert(0, tempo.MetronomeMark(number=tempoBPM))

    # Time signature
    score.insert(0, meter.TimeSignature(f"{timeSigNumerator}/{timeSigDenominator}"))

    # Key signature
    modeMap = {
        "Ionian (maj.)": "major",
        "Aeolian (min.)": "minor",
        "Dorian": "dorian",
        "Phrygian": "phrygian",
        "Lydian": "lydian",
        "Mixolydian": "mixolydian",
        "Locrian": "locrian",
    }
    score.insert(0, key.Key(key, modeMap[mode]))

    # One tile expressed in quarterLength units
    tileQuarterLength = (4 / timeSigDenominator) / beatLength

    # Clef mapping
    clefMap = {
        "Treble": clef.TrebleClef,
        "Treble (8va)": clef.Treble8vaClef,
        "Treble (8vb)": clef.Treble8vbClef,

        "Soprano": clef.SopranoClef,
        "Mezzo-soprano": clef.MezzoSopranoClef,
        "Alto": clef.AltoClef,
        "Tenor": clef.TenorClef,

        "Bass": clef.BassClef,
        "Bass (8vb)": clef.Bass8vbClef,
    }

    for color, notes in noteMap.items():
        part = stream.Part()

        # Clef assignment
        clefName = colorStaffMap.get(color) if colorStaffMap else None
        if clefName and clefName in clefMap:
            part.insert(0, clefMap[clefName]())    
        else:
            part.insert(0, clef.TrebleClef()) # default is treble clef

        for n in notes:
            pitch = n.pitch + 23
            startQL = n.time * tileQuarterLength
            durQL = n.duration * tileQuarterLength

            m21note = note.Note(pitch)
            m21note.duration.quarterLength = durQL
            part.insert(startQL, m21note)

        score.append(part)

    score.write("musicxml", candidate)
